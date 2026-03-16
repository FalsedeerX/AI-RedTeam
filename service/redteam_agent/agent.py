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
from .rag_node import RAGNode
from .tools import execute_nmap_scan, execute_msf_module, search_msf_modules

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
    # --- RAG inter-node communication ---
    rag_query: str
    rag_reason: str
    rag_caller: str

class RedTeamAgent:
    """
    Encapsulates the Red Team Agent graph logic, models, and tools.

    Graph flow:
        START -> planner -> tactician -> critic_node -> risk_gate_node -> tool_node -> analyst_node -> planner
        Any thinking node (planner, tactician, critic, analyst) can request a RAG
        search via rag_node, which routes results back to the calling node.
    The Planner decides *what* to do (phase + directive).
    The Tactician decides *how* to do it (tool calls).
    The Critic validates proposed commands (schema, scope, LLM review).
    The Risk Gate assesses danger level and requests operator approval for HIGH-risk actions.
    The Analyst interprets tool results to severity/risk levels.
    The RAG Node retrieves knowledge from the vector store on behalf of thinking nodes.
    """
    def __init__(self):
        self._init_tools()
        self._init_models()
        self.critic = CriticPipeline(self.critic_model)
        self.rag = RAGNode(self.rag_model)
        self.app = self._build_graph()

    def _init_tools(self):
        self.tools = [execute_nmap_scan, execute_msf_module, search_msf_modules]
        self.tools_by_name = {tool.name: tool for tool in self.tools}

    def _init_models(self):
        base_model = ChatOllama(**config.LLM_CONFIG)
        self.tactician_model = base_model.bind_tools(self.tools)
        self.planner_model = ChatOllama(**config.LLM_CONFIG)
        self.critic_model = ChatOllama(**config.LLM_CONFIG)
        self.analyst_model = ChatOllama(**config.LLM_CONFIG)
        self.rag_model = ChatOllama(**config.LLM_CONFIG)

    # --- Nodes ---

    def planner_node(self, state: MessagesState):
        """Planner: decides the current engagement phase and issues a directive.

        Analyses the full message history (tool outputs, findings, etc.) and
        returns a structured PHASE + DIRECTIVE that the Tactician will execute.
        May request a RAG search first by outputting RAG_SEARCH + RAG_REASON.
        """
        phase_match, directive_match = None, None
        for _ in range(config.PLANNER_MAX_RETRIES):
            raw_response = self.planner_model.invoke(
                [SystemMessage(content=config.PLANNER_SYSTEM_PROMPT)]
                + state["messages"]
            )
            response = self._sanitize_response(raw_response).content

            # Check for RAG search request
            rag_request = self._parse_rag_request(response)
            if rag_request and self._recent_rag_count(state["messages"]) < config.MAX_RAG_PER_NODE:
                return {
                    "messages": [HumanMessage(content=f"[PLANNER \u2192 RAG] Searching: {rag_request[0]}")],
                    "rag_query": rag_request[0],
                    "rag_reason": rag_request[1],
                    "rag_caller": "planner",
                }

            # Parse PHASE and DIRECTIVE from response
            phase_match = re.search(r"PHASE:\s*(recon|enumeration|exploitation|complete)", response, re.IGNORECASE)
            directive_match = re.search(r"DIRECTIVE:\s*(.+)", response, re.DOTALL)

            # Graceful fallback: if PHASE is "complete" but DIRECTIVE is missing,
            # synthesize a reasonable completion directive instead of retrying.
            if phase_match and phase_match.group(1).lower() == "complete" and not directive_match:
                phase = "complete"
                directive = "Engagement concluded — all viable exploitation approaches have been attempted."
                return {
                    "messages": [HumanMessage(content=f"[PLANNER — phase: {phase}]\n{directive}")],
                    "current_phase": phase,
                    "directive": directive,
                    "phase_history": [phase],
                }

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
        # Graceful fallback — mark engagement as complete instead of crashing.
        # This typically happens when the context is very long and the LLM
        # struggles to follow the strict format.
        return {
            "messages": [HumanMessage(
                content="[PLANNER — phase: complete]\n"
                        "Engagement concluded — planner could not produce a structured directive "
                        "after maximum retries (likely due to extended context)."
            )],
            "current_phase": "complete",
            "directive": "Engagement concluded (planner format fallback).",
            "phase_history": ["complete"],
        }

    def tactician_node(self, state: MessagesState):
        """Tactician: generates specific tool calls based on the Planner's directive.

        Reads the Planner's objective directly from message history and independently
        decides HOW to accomplish it — strategy is left to the Planner.
        May request a RAG search first by outputting RAG_SEARCH + RAG_REASON.
        """
        response = self.tactician_model.invoke(
            [SystemMessage(content=config.TACTICIAN_SYSTEM_PROMPT)]
            + state["messages"]
        )
        response = self._sanitize_response(response)

        # Check for RAG search request in text content
        if response.content:
            rag_request = self._parse_rag_request(response.content)
            if rag_request and self._recent_rag_count(state["messages"]) < config.MAX_RAG_PER_NODE:
                return {
                    "messages": [HumanMessage(content=f"[TACTICIAN \u2192 RAG] Searching: {rag_request[0]}")],
                    "rag_query": rag_request[0],
                    "rag_reason": rag_request[1],
                    "rag_caller": "tactician",
                    "llm_calls": state.get('llm_calls', 0) + 1,
                }

        return {
            "messages": [response],
            "llm_calls": state.get('llm_calls', 0) + 1
        }

    def tool_node(self, state: MessagesState):
        """Performs the tool call.

        Uses ``_find_pending_action_msg`` to locate the most recent AI
        message with unexecuted tool_calls, so that intermediate messages
        (e.g. RAG search results) do not break the lookup.
        """
        result = []
        tc_message = self._find_pending_action_msg(state["messages"])

        if not tc_message:
            return {"messages": []}

        for tool_call in tc_message.tool_calls:
            tool = self.tools_by_name.get(tool_call["name"])
            if not tool:
                continue  # skip unknown tools (e.g. leftover retrieve_context)
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

        Before running the 3 stages, automatically requests a RAG search for
        the proposed commands so that Stage 3 (LLM review) has documentation
        context.  If RAG results already exist after the current tool-call
        message, the RAG step is skipped.
        """
        tc_message = self._find_pending_action_msg(state["messages"])
        if not tc_message:
            return {"messages": []}

        action_calls = [tc for tc in tc_message.tool_calls if tc["name"] != "retrieve_context"]
        if not action_calls:
            return {"messages": []}

        # --- Auto-RAG: ensure we have documentation context ---
        tc_idx = next(
            i for i, m in enumerate(state["messages"]) if m is tc_message
        )
        has_rag = any(
            isinstance(m, HumanMessage) and "[RAG SEARCH RESULT" in m.content
            for m in state["messages"][tc_idx:]
        )
        if not has_rag:
            query_parts = []
            for tc in action_calls:
                if tc["name"] == "execute_nmap_scan":
                    cmd = tc["args"].get("command", "")
                    flags = " ".join(p for p in cmd.split() if p.startswith("-"))
                    query_parts.append(f"nmap {flags} usage and compatibility")
                elif tc["name"] == "execute_msf_module":
                    module = tc["args"].get("module_name", "")
                    query_parts.append(f"metasploit module {module} usage and options")
            if query_parts:
                query = "; ".join(query_parts)
                return {
                    "messages": [HumanMessage(content=f"[CRITIC \u2192 RAG] Verifying: {query}")],
                    "rag_query": query,
                    "rag_reason": "Need documentation to validate proposed security tool commands for correctness and safety",
                    "rag_caller": "critic_node",
                }

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
        tc_message = self._find_pending_action_msg(state["messages"])
        if not tc_message:
            return {"messages": []}

        _SAFE_TOOLS = {"search_msf_modules"}
        action_calls = [tc for tc in tc_message.tool_calls if tc["name"] not in _SAFE_TOOLS]

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
        """Analyst: interprets tool results and maps findings to severity/risk levels.

        May request a RAG search first to better understand tool outputs.
        When re-entered after a RAG round-trip, the RAG results are included
        in the prompt so the LLM knows what was already searched.
        """    
        messages = state["messages"]

        # Collect consecutive tool messages (most recent batch)
        tool_messages = []
        for m in reversed(messages):
            if isinstance(m, ToolMessage):
                tool_messages.append(m)
            elif tool_messages:
                break

        if not tool_messages:
            return {"messages": [], "findings": []}
        
        tool_summary = "\n\n".join(f"[{tm.name}]:\n{tm.content}" for tm in tool_messages)

        # Collect any prior RAG results from this analyst invocation so the
        # LLM knows what has already been searched and won't repeat the same
        # RAG query.  We scan backwards from the tail of messages, collecting
        # RAG SEARCH RESULT messages until we hit a non-RAG message.
        prior_rag = []
        for m in reversed(messages):
            if isinstance(m, HumanMessage) and "[RAG SEARCH RESULT" in m.content:
                prior_rag.append(m.content)
            elif isinstance(m, HumanMessage) and "\u2192 RAG]" in m.content:
                continue  # skip the RAG request message itself
            else:
                break
        prior_rag.reverse()

        prompt_parts = [f"TOOL OUTPUTS:\n{tool_summary}"]
        if prior_rag:
            prompt_parts.append(
                "PRIOR RAG SEARCH RESULTS (already searched — do NOT repeat these queries, "
                "use the information or proceed without it):\n"
                + "\n---\n".join(prior_rag)
            )

        analyst_response = self.analyst_model.invoke([
            SystemMessage(content=config.ANALYST_SYSTEM_PROMPT),
            HumanMessage(content="\n\n".join(prompt_parts))
        ])
        analyst_response = self._sanitize_response(analyst_response)
        clean_content = analyst_response.content

        # Check for RAG search request — but only if we haven't already exhausted retries
        rag_request = self._parse_rag_request(clean_content)
        if rag_request and not prior_rag and self._recent_rag_count(messages) < config.MAX_RAG_PER_NODE:
            # First RAG attempt for this analyst invocation — allow it
            return {
                "messages": [HumanMessage(content=f"[ANALYST \u2192 RAG] Searching: {rag_request[0]}")],
                "rag_query": rag_request[0],
                "rag_reason": rag_request[1],
                "rag_caller": "analyst_node",
                "findings": [],
            }

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
    def _find_pending_action_msg(messages: list):
        """Return the most recent AI message whose tool_calls have not been executed.

        Scans backward through *messages*.  Returns ``None`` if a
        ``ToolMessage`` is encountered before an AI message with
        ``tool_calls`` — that means the calls were already executed.
        This allows nodes (critic, risk_gate, tool_node) to locate the
        correct tool-call message even when RAG messages have been
        inserted between the tactician output and the consuming node.
        """
        for m in reversed(messages):
            if hasattr(m, "tool_calls") and m.tool_calls:
                return m
            if isinstance(m, ToolMessage):
                return None  # tool_calls already executed
        return None

    @staticmethod
    def _parse_rag_request(text: str):
        """Parse ``RAG_SEARCH`` and ``RAG_REASON`` markers from LLM output.

        Returns ``(query, reason)`` if found, ``None`` otherwise.
        """
        search_match = re.search(r"RAG_SEARCH:\s*(.+?)(?:\n|$)", text)
        if not search_match:
            return None
        reason_match = re.search(r"RAG_REASON:\s*(.+?)(?:\n|$)", text)
        query = search_match.group(1).strip()
        reason = reason_match.group(1).strip() if reason_match else ""
        return (query, reason)

    @staticmethod
    def _recent_rag_count(messages: list) -> int:
        """Count consecutive RAG round-trips at the tail of *messages*.

        Used to enforce ``MAX_RAG_PER_NODE`` and prevent infinite
        RAG-search loops.
        """
        count = 0
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                if "[RAG SEARCH RESULT" in m.content:
                    count += 1
                elif "\u2192 RAG]" in m.content:
                    continue  # part of a RAG round-trip request
                else:
                    break
            else:
                break
        return count
    
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

        # Clean .tool_calls args (strip think tags from values AND
        # whitespace from keys — qwen3 sometimes emits ' SMBPIPE' etc.)
        if hasattr(response, "tool_calls") and response.tool_calls:
            updates["tool_calls"] = [
                {
                    **tc,
                    "args": {
                        k.strip(): cls._strip_think_tags(v) if isinstance(v, str) else v
                        for k, v in tc["args"].items()
                    },
                }
                for tc in response.tool_calls
            ]

        return response.model_copy(update=updates) if updates else response

    # --- Conditional Edges ---

    def route_after_planner(self, state: MessagesState) -> Literal["tactician", "rag_node", "__end__"]:
        """After the Planner runs, decide whether to continue, RAG, or finish."""
        if state.get("rag_query"):
            return "rag_node"
        phase = state.get("current_phase", "recon")
        if phase == "complete":
            return END
        return "tactician"

    def route_after_tactician(self, state: MessagesState) -> Literal["critic_node", "planner", "rag_node"]:
        """After the Tactician runs, route based on output.

        - RAG search requested → rag_node.
        - Has tool_calls → send to Critic for validation.
        - No tool_calls (text only) → loop back to Planner.
        """
        if state.get("rag_query"):
            return "rag_node"
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "critic_node"
        return "planner"

    def route_after_critic(self, state: MessagesState) -> Literal["tactician", "risk_gate_node", "rag_node"]:
        """After the Critic runs, route to RAG, loop back to fix, or proceed."""
        if state.get("rag_query"):
            return "rag_node"
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

    def route_after_analyst(self, state: MessagesState) -> Literal["planner", "rag_node"]:
        """After the Analyst runs, route to RAG or back to Planner."""
        if state.get("rag_query"):
            return "rag_node"
        return "planner"

    def route_after_rag(self, state: MessagesState) -> Literal["planner", "tactician", "critic_node", "analyst_node"]:
        """After the RAG node, route back to whichever node requested the search."""
        caller = state.get("rag_caller", "planner")
        return caller

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
        """Build the StateGraph with RAG support.

        Main flow:
            START → planner → tactician → critic_node → risk_gate_node → tool_node → analyst_node → planner

        Any thinking node can detour to rag_node for knowledge retrieval:
            planner     ↔ rag_node
            tactician   ↔ rag_node
            critic_node ↔ rag_node
            analyst_node↔ rag_node
        """
        agent_builder = StateGraph(MessagesState)

        # Add nodes
        agent_builder.add_node("planner", self.planner_node)
        agent_builder.add_node("tactician", self.tactician_node)
        agent_builder.add_node("critic_node", self.critic_node)
        agent_builder.add_node("risk_gate_node", self.risk_gate_node)
        agent_builder.add_node("tool_node", self.tool_node)
        agent_builder.add_node("analyst_node", self.analyst_node)
        agent_builder.add_node("rag_node", self.rag)

        # ---- Edges ----

        # Entry point
        agent_builder.add_edge(START, "planner")

        # Planner → Tactician / RAG / END
        agent_builder.add_conditional_edges(
            "planner",
            self.route_after_planner,
            {"tactician": "tactician", "rag_node": "rag_node", END: END},
        )
        # Tactician → Critic / Planner / RAG
        agent_builder.add_conditional_edges(
            "tactician",
            self.route_after_tactician,
            {"critic_node": "critic_node", "planner": "planner", "rag_node": "rag_node"},
        )
        # Critic → Risk Gate / Tactician / RAG
        agent_builder.add_conditional_edges(
            "critic_node",
            self.route_after_critic,
            {"risk_gate_node": "risk_gate_node", "tactician": "tactician", "rag_node": "rag_node"},
        )
        # Risk Gate → tool_node / Tactician  (unchanged, no RAG)
        agent_builder.add_conditional_edges(
            "risk_gate_node",
            self.route_after_risk_gate,
            {"tool_node": "tool_node", "tactician": "tactician"},
        )
        # tool_node → analyst_node
        agent_builder.add_edge("tool_node", "analyst_node")

        # Analyst → Planner / RAG
        agent_builder.add_conditional_edges(
            "analyst_node",
            self.route_after_analyst,
            {"planner": "planner", "rag_node": "rag_node"},
        )
        # RAG → back to calling node
        agent_builder.add_conditional_edges(
            "rag_node",
            self.route_after_rag,
            {
                "planner": "planner",
                "tactician": "tactician",
                "critic_node": "critic_node",
                "analyst_node": "analyst_node",
            },
        )

        return agent_builder.compile(checkpointer=InMemorySaver())

def get_agent():
    """
    Factory function to get the agent with compiled graph.
    """
    return RedTeamAgent()
