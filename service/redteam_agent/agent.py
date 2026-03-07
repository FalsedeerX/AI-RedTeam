import operator
import re
from typing import Literal, TypedDict, Annotated, List, Dict
from langchain_ollama import ChatOllama
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
from .config import config
from .critic import CriticPipeline
from .tools import retrieve_context, execute_nmap_scan, execute_msf_module, search_msf_modules

VALID_PHASES = ("recon", "enumeration", "exploitation", "complete")
PHASE_ORDER = {phase: i for i, phase in enumerate(VALID_PHASES)}

# Define state
class MessagesState(TypedDict):
    # --- LLM context ---
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
    # --- Structured fields for backend / frontend consumers ---
    current_phase: str
    directive: str
    findings: Annotated[list[dict], operator.add]
    last_tool_results: list[dict]
    phase_history: Annotated[list[str], operator.add]

class RedTeamAgent:
    """
    Encapsulates the Red Team Agent graph logic, models, and tools.

    Graph flow:
        START -> planner -> tactician -> critic_node -> risk_gate_node -> tool_node -> analyst_node -> planner
    The Planner decides *what* to do (phase + directive).
    The Tactician decides *how* to do it (tool calls).
    The Critic validates proposed commands (schema, scope, LLM review).
    The Risk Gate assesses danger level and requests operator approval for HIGH-risk actions.
    The Analyst interprets tool results to severity/risk levels.
    """
    def __init__(self):
        self._init_tools()
        self._init_models()
        self.critic = CriticPipeline(self.critic_model)
        self.app = self._build_graph()

    def _init_tools(self):
        self.tools = [retrieve_context, execute_nmap_scan, execute_msf_module, search_msf_modules]
        self.tools_by_name = {tool.name: tool for tool in self.tools}

    def _init_models(self):
        base_model = ChatOllama(**config.LLM_CONFIG)
        self.tactician_model = base_model.bind_tools(self.tools)
        self.planner_model = ChatOllama(**config.LLM_CONFIG)
        self.critic_model = ChatOllama(**config.LLM_CONFIG)
        self.analyst_model = ChatOllama(**config.LLM_CONFIG)

    # --- Nodes ---

    def planner_node(self, state: MessagesState):
        """Planner: decides the current engagement phase and issues a directive.

        Analyses the full message history (tool outputs, findings, etc.) and
        returns a structured PHASE + DIRECTIVE that the Tactician will execute.
        """
        phase_match, directive_match = None, None
        for _ in range(config.PLANNER_MAX_RETRIES):
            raw_response = self.planner_model.invoke(
                [SystemMessage(content=config.PLANNER_SYSTEM_PROMPT)]
                + state["messages"]
            )
            response = self._sanitize_response(raw_response).content
            
            # Parse PHASE and DIRECTIVE from response
            phase_match = re.search(r"PHASE:\s*(recon|enumeration|exploitation|complete)", response, re.IGNORECASE)
            directive_match = re.search(r"DIRECTIVE:\s*(.+)", response, re.DOTALL)
            if not phase_match or not directive_match:
                continue  # Retry
            phase = phase_match.group(1).lower()
            directive = directive_match.group(1).strip()

            # Prevent skipping phases
            prev_phase = state.get("current_phase", "recon")
            prev_idx = PHASE_ORDER.get(prev_phase, 0)
            new_idx = PHASE_ORDER.get(phase, 0)
            if new_idx > prev_idx + 1:
                phase = VALID_PHASES[prev_idx + 1]
                directive = f"(Auto-corrected from skipped phase) {directive}"

            return {
                "messages": [HumanMessage(content=f"[PLANNER — phase: {phase}]\n{directive}")],
                "current_phase": phase,
                "directive": directive,
                "phase_history": [phase],
            }
        # After exceeding MAX_PLANNER_RETRIES:
        # Raise an error with details on what was missing for debugging
        missing = []
        if not phase_match:
            missing.append("PHASE")
        if not directive_match:
            missing.append("DIRECTIVE")
        raise ValueError(f"LLM response does not contain required format after {config.PLANNER_MAX_RETRIES} attempts. Missing: {', '.join(missing)}. Expected format: \nPHASE: <phase>\nDIRECTIVE: <directive>")

    def tactician_node(self, state: MessagesState):
        """Tactician: generates specific tool calls based on the Planner's directive.

        Reads the Planner's objective directly from message history and independently
        decides HOW to accomplish it — strategy is left to the Planner.
        """
        response = self.tactician_model.invoke(
            [SystemMessage(content=config.TACTICIAN_SYSTEM_PROMPT)]
            + state["messages"]
        )
        response = self._sanitize_response(response)

        return {
            "messages": [response],
            "llm_calls": state.get('llm_calls', 0) + 1
        }

    def tool_node(self, state: MessagesState):
        """Performs the tool call"""
        result = []
        last_message = state["messages"][-1]
        
        if not hasattr(last_message, 'tool_calls'):
            return {"messages": []}

        for tool_call in last_message.tool_calls:
            tool = self.tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            
            # Handle potential artifact return (content, artifact)
            if isinstance(observation, tuple):
                observation = observation[0]
            
            result.append(ToolMessage(
                content=str(observation), 
                tool_call_id=tool_call["id"], 
                name=tool_call["name"]
            ))
        return {
            "messages": result,
            "last_tool_results": [
                {"tool": msg.name, "output": msg.content}
                for msg in result
            ],
        }

    def critic_node(self, state: MessagesState):
        """Critic: validates proposed tool calls (schema -> scope -> LLM review).

        Performs Stage 1-3 validation only.  Risk-level gating (HIGH actions)
        is handled by the downstream ``risk_gate_node``.
        """
        if not hasattr(state["messages"][-1], "tool_calls") or not state["messages"][-1].tool_calls:
            return {"messages": []}

        action_calls = [tc for tc in state["messages"][-1].tool_calls if tc["name"] != "retrieve_context"]
        if not action_calls:
            return {"messages": []}

        # --- Stage 1: Schema validation ---
        issues = []
        for tc in action_calls:
            if tc["name"] == "execute_nmap_scan":
                issue = self.critic.validate_nmap_schema(tc["args"])
            elif tc["name"] == "execute_msf_module":
                issue = self.critic.validate_msf_schema(tc["args"])
            else:
                issue = None
            if issue:
                issues.append((tc, issue))
        if issues:
            return {"messages": [HumanMessage(content=(
                "CRITICISM DETECTED (schema validation):\n"
                + "\n\n".join(
                    f"  [{tc['name']}] args={tc.get('args', {})}:\n    {issue}"
                    for tc, issue in issues
                )
                + "\n\nPlease correct the command(s) and try again."
            ))]}

        # --- Stage 2: BLOCKED scope check ---
        blocked = []
        for tc in action_calls:
            name = tc["name"]
            args = tc.get("args", {})
            if name == "execute_nmap_scan":
                blocked_targets = self.critic.assess_nmap_blocked(args)
            elif name == "execute_msf_module":
                blocked_targets = self.critic.assess_msf_blocked(args)
            else:
                blocked_targets = []
            if blocked_targets:
                blocked.append((tc, f"Target(s) {blocked_targets} are outside allowed scope"))
        if blocked:
            return {"messages": [HumanMessage(content=(
                "CRITICISM DETECTED (scope violation):\n"
                + "\n".join(f"  [{tc['name']}] {reason}" for tc, reason in blocked)
                + "\n\nThese targets are outside the authorized engagement scope. "
                "Please choose targets within the allowed range."
            ))]}

        # --- Stage 3: LLM review ---
        issues = []
        for tc in action_calls:
            result = self.critic.stage_llm_review([tc], state["messages"])
            if result["messages"]:
                issues.append((tc, result["messages"][0].content))
        if issues:
            return {"messages": [HumanMessage(content=(
                "CRITICISM DETECTED (LLM review):\n"
                + "\n".join(f"  [{tc['name']}] {issue}" for tc, issue in issues)
                + "\nPlease correct the command(s) and try again."
            ))]}

        return {"messages": []}

    def risk_gate_node(self, state: MessagesState):
        """Risk gate: assesses danger level and requests operator approval.

        Runs pure-Python risk heuristics.  When a HIGH-risk action is
        detected, triggers a human-in-the-loop ``interrupt``.  On resume
        only this node is re-executed — the expensive LLM review in
        ``critic_node`` is NOT repeated.
        """
        if not hasattr(state["messages"][-1], "tool_calls") or not state["messages"][-1].tool_calls:
            return {"messages": []}


        _SAFE_TOOLS = {"retrieve_context", "search_msf_modules"}
        action_calls = [tc for tc in state["messages"][-1].tool_calls if tc["name"] not in _SAFE_TOOLS]

        high_calls = []
        for tc in action_calls:
            name = tc["name"]
            args = tc.get("args", {})
            if name == "execute_nmap_scan":
                level, reason = self.critic.assess_nmap_risk(args)
            elif name == "execute_msf_module":
                level, reason = self.critic.assess_msf_risk(args)
            else:
                level, reason = ("HIGH", f"Unknown tool: {name}, args: {args}")
            if level == "HIGH":
                high_calls.append((tc, reason))

        if high_calls:
            approval = interrupt({
                "risk_level": "HIGH",
                "proposed_actions": high_calls,
                "prompt": "Approve these high-risk actions? (yes/no)",
            })
            if not approval:
                return {"messages": [HumanMessage(content=(
                    "CRITICISM DETECTED (operator denied):\n"
                    + "\n".join(f"  [{tc['name']}] args={tc.get('args', {})}:\n    {reason}" for tc, reason in high_calls)
                    + "\n\nPlease propose a less aggressive alternative."
                ))]}

        return {"messages": []}

    def analyst_node(self, state: MessagesState):
        """Analyst: interprets tool results and maps findings to severity/risk levels."""    
        messages = state["messages"]

        tool_messages = []
        for m in reversed(messages):
            if isinstance(m, ToolMessage):
                tool_messages.append(m)
            elif tool_messages:
                break

        if not tool_messages:
            return {"messages": [], "findings": []}
        
        tool_summary = "\n\n".join(f"[{tm.name}]:\n{tm.content}" for tm in tool_messages)

        analyst_response = self.analyst_model.invoke([
            SystemMessage(content=config.ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=f"TOOL OUTPUTS:\n{tool_summary}\n\n")
        ])
        analyst_response = self._sanitize_response(analyst_response)

        clean_content = analyst_response.content
        findings = []
        for line in clean_content.split("\n"):
            if line.startswith("FINDING:"):
                # Extract severity and description
                parts = line[len("FINDING:"):].strip().split(" ", 1)
                if len(parts) == 2:
                    severity, description = parts
                    findings.append({
                        "severity": severity.strip("[]"),
                        "description": description.strip(),
                    })
        analyst_message = HumanMessage(content=f"Tool Call Analysis:\n{clean_content}")

        return {"messages": [analyst_message], "findings": findings}
    
    # --- Helpers ---
    
    @staticmethod
    def _strip_think_tags(text: str) -> str:
        """Remove qwen3 ``<think>`` artifacts from a string.

        Handles paired ``<think>…</think>`` blocks, unpaired opening/closing
        tags, and bare ``/think`` remnants.  Collapses leftover whitespace
        gaps so downstream parsers never see phantom empty tokens.
        """
        # Paired blocks
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        # Unpaired tags: <think>, </think>, <think, </think …
        text = re.sub(r"</?think>?", "", text)
        # Bare /think
        text = re.sub(r"/think\b", "", text)
        # Collapse whitespace gaps left by removals
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    @classmethod
    def _sanitize_response(cls, response):
        """Strip qwen3 ``<think>`` artifacts from an LLM response.

        Cleans **both** ``.content`` (free text) **and** every string
        value inside ``.tool_calls[*].args``, then returns a new
        message object via ``model_copy``.
        """
        updates: dict = {}

        # Clean .content
        if response.content:
            updates["content"] = cls._strip_think_tags(response.content)

        # Clean .tool_calls args
        if hasattr(response, "tool_calls") and response.tool_calls:
            updates["tool_calls"] = [
                {
                    **tc,
                    "args": {
                        k: cls._strip_think_tags(v) if isinstance(v, str) else v
                        for k, v in tc["args"].items()
                    },
                }
                for tc in response.tool_calls
            ]

        return response.model_copy(update=updates) if updates else response

    # --- Conditional Edges ---

    def route_after_planner(self, state: MessagesState) -> Literal["tactician", "__end__"]:
        """After the Planner runs, decide whether to continue or finish."""
        phase = state.get("current_phase", "recon")
        if phase == "complete":
            return END
        return "tactician"

    def route_after_tactician(self, state: MessagesState) -> Literal["critic_node", "planner"]:
        """After the Tactician runs, route based on whether tool calls were produced.

        - Has tool_calls → send to Critic for validation.
        - No tool_calls (LLM returned text instead of actions) → loop back to
          Planner so it can re-evaluate the situation or advance the phase.
        """
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "critic_node"
        return "planner"

    def route_after_critic(self, state: MessagesState) -> Literal["tactician", "risk_gate_node"]:
        """After the Critic runs, either loop back to fix or proceed to risk gate."""
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage) and "CRITICISM DETECTED" in last_message.content:
            return "tactician"
        return "risk_gate_node"

    def route_after_risk_gate(self, state: MessagesState) -> Literal["tactician", "tool_node"]:
        """After the Risk Gate runs, either loop back (operator denied) or proceed to execute."""
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage) and "CRITICISM DETECTED" in last_message.content:
            return "tactician"
        return "tool_node"

    # --- Utilities ---

    def save_graph_image(self, file_path="graph.png"):
        """Generate and save the graph structure as an image."""
        try:
            graph_png = self.app.get_graph(xray=True).draw_mermaid_png()
            with open(file_path, "wb") as f:
                f.write(graph_png)
            print(f"Graph image saved to '{file_path}'")
        except Exception as e:
            print(f"Could not save graph image: {e}")

    # --- Graph Construction ---

    def _build_graph(self):
        """Build the StateGraph:
        START → planner → tactician → critic_node → risk_gate_node → tool_node → analyst_node → planner
        """
        agent_builder = StateGraph(MessagesState)

        # Add nodes
        agent_builder.add_node("planner", self.planner_node)
        agent_builder.add_node("tactician", self.tactician_node)
        agent_builder.add_node("critic_node", self.critic_node)
        agent_builder.add_node("risk_gate_node", self.risk_gate_node)
        agent_builder.add_node("tool_node", self.tool_node)
        agent_builder.add_node("analyst_node", self.analyst_node)

        # Add edges
        
        # Entry point
        agent_builder.add_edge(START, "planner")
        # Planner -> Tactician / END
        agent_builder.add_conditional_edges(
            "planner",
            self.route_after_planner,
            {"tactician": "tactician", END: END},
        )
        # Tactician -> Critic / Planner (no tool calls = let Planner re-evaluate)
        agent_builder.add_conditional_edges(
            "tactician",
            self.route_after_tactician,
            {"critic_node": "critic_node", "planner": "planner"},
        )
        # Critic -> Risk Gate (passed) / Tactician (rejected)
        agent_builder.add_conditional_edges(
            "critic_node",
            self.route_after_critic,
            {"risk_gate_node": "risk_gate_node", "tactician": "tactician"},
        )
        # Risk Gate -> tool_node (approved) / Tactician (denied)
        agent_builder.add_conditional_edges(
            "risk_gate_node",
            self.route_after_risk_gate,
            {"tool_node": "tool_node", "tactician": "tactician"},
        )
        # tool_node -> analyst_node -> planner
        agent_builder.add_edge("tool_node", "analyst_node")
        agent_builder.add_edge("analyst_node", "planner")

        return agent_builder.compile(checkpointer=InMemorySaver())

def get_agent():
    """
    Factory function to get the agent with compiled graph.
    """
    return RedTeamAgent()
