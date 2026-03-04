import ipaddress
import operator
import re
from typing import Literal, TypedDict, Annotated, List, Dict
from langchain_ollama import ChatOllama
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from .config import config
from .tools import retrieve_context, execute_nmap_scan, execute_msf_module

VALID_PHASES = ("recon", "enumeration", "exploitation", "complete")
VALID_MSF_MODULE_TYPES = ("auxiliary", "exploit", "post", "payload", "encoder", "nop")

# Nmap flags that consume the next token as their value (for target extraction)
_NMAP_FLAGS_WITH_ARGS = frozenset({
    "-p", "-oN", "-oX", "-oG", "-oA", "-e", "-S", "-D",
    "-g", "--source-port", "--top-ports", "-iL", "-sI",
    "--script", "--exclude", "--excludefile", "--max-rate",
    "--min-rate", "--max-retries", "--host-timeout",
    "--scan-delay", "--max-scan-delay",
})

# Define state
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
    current_phase: str
    plan: str
    findings: Annotated[list[dict], operator.add]

class RedTeamAgent:
    """
    Encapsulates the Red Team Agent graph logic, models, and tools.

    Graph flow:
        START -> planner -> tactician -> critic_node -> tool_node -> analyst_node -> planner
    The Planner decides *what* to do (phase + directive).
    The Tactician decides *how* to do it (tool calls).
    The Critic validates proposed commands before execution.
    The Analyst interprets tool results to severity/risk levels.
    """
    def __init__(self):
        self._init_tools()
        self._init_models()
        self.app = self._build_graph()

    def _init_tools(self):
        self.tools = [retrieve_context, execute_nmap_scan, execute_msf_module]
        self.tools_by_name = {tool.name: tool for tool in self.tools}

    def _init_models(self):
        base_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )
        self.tactician_model = base_model.bind_tools(self.tools)
        self.planner_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )
        self.critic_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )
        self.analyst_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )

    # --- Nodes ---

    def planner_node(self, state: MessagesState):
        """Planner: decides the current engagement phase and issues a directive.

        Analyses the full message history (tool outputs, findings, etc.) and
        returns a structured PHASE + DIRECTIVE that the Tactician will execute.
        """
        response = self.planner_model.invoke(
            [SystemMessage(content=config.PLANNER_SYSTEM_PROMPT)]
            + state["messages"]
        )
        text = response.content.strip()
        phase = state.get("current_phase", "recon")
        directive = text  # Fallback: treat the whole response as the directive

        phase_match = re.search(r"PHASE:\s*(recon|enumeration|exploitation|complete)", text, re.IGNORECASE)
        directive_match = re.search(r"DIRECTIVE:\s*(.+)", text, re.DOTALL)

        if phase_match:
            phase = phase_match.group(1).lower()
        if directive_match:
            directive = directive_match.group(1).strip()

        planner_message = HumanMessage(
            content=f"[PLANNER — phase: {phase}]\n{directive}"
        )

        return {
            "messages": [planner_message],
            "current_phase": phase,
            "plan": directive,
        }

    def tactician_node(self, state: MessagesState):
        """Tactician: generates specific tool calls based on the Planner's directive.

        Focuses *only* on execution — strategy is left to the Planner.
        """
        directive = state.get("plan", "")

        # Prepend the directive so the Tactician knows exactly what to do
        directive_preamble = (
            f"CURRENT PHASE: {state.get('current_phase', 'recon')}\n"
            f"PLANNER DIRECTIVE: {directive}\n\n"
            "Generate the appropriate tool call(s) to carry out the above directive."
        )
        return {
            "messages": [ self.tactician_model.invoke(
                [
                    SystemMessage(content=config.TACTICIAN_SYSTEM_PROMPT),
                    HumanMessage(content=directive_preamble)
                ]
                + state["messages"]
            )],
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
            content = observation
            if isinstance(observation, tuple):
                content = observation[0]
            
            result.append(ToolMessage(
                content=str(content), 
                tool_call_id=tool_call["id"], 
                name=tool_call["name"]
            ))
        return {"messages": result}

    # --- Schema Validation (minimal, deterministic) ---

    @staticmethod
    def _validate_nmap_schema(command: str) -> list[str]:
        """Minimal format checks for nmap commands."""
        issues = []
        parts = command.strip().split()
        if not parts or parts[0].lower() != "nmap":
            issues.append("Command must start with 'nmap'.")
            return issues
        # Ensure at least one non-flag argument (target host)
        skip_next = False
        has_target = False
        for arg in parts[1:]:
            if skip_next:
                skip_next = False
                continue
            if arg in _NMAP_FLAGS_WITH_ARGS:
                skip_next = True
                continue
            if not arg.startswith("-"):
                has_target = True
                break
        if not has_target:
            issues.append("No target host specified in the nmap command.")
        return issues

    @staticmethod
    def _validate_msf_schema(tool_call: dict) -> list[str]:
        """Minimal format checks for MSF module parameters."""
        issues = []
        args = tool_call.get("args", {})
        module_type = args.get("module_type", "")
        if module_type not in VALID_MSF_MODULE_TYPES:
            issues.append(
                f"Invalid module_type '{module_type}'. "
                f"Must be one of: {', '.join(VALID_MSF_MODULE_TYPES)}."
            )
        rport = args.get("options", {}).get("RPORT") or args.get("options", {}).get("rport")
        if rport is not None:
            try:
                port_int = int(rport)
                if not (1 <= port_int <= 65535):
                    issues.append(f"RPORT {rport} out of range (1~65535).")
            except (ValueError, TypeError):
                issues.append(f"RPORT '{rport}' is not a valid integer.")
        return issues

    # --- Danger Level Assessment ---

    @staticmethod
    def _extract_targets_from_nmap(command: str) -> list[str]:
        """Extract target arguments from an nmap command string."""
        parts = command.strip().split()
        targets = []
        skip_next = False
        for arg in parts[1:]:  # skip 'nmap'
            if skip_next:
                skip_next = False
                continue
            if arg in _NMAP_FLAGS_WITH_ARGS:
                skip_next = True
                continue
            if arg.startswith("-"):
                # handle --flag=value form
                continue
            targets.append(arg)
        return targets

    @staticmethod
    def _is_target_allowed(target: str, allowed: list[str]) -> bool:
        """Check if a target IP/CIDR falls within any allowed network."""
        if not allowed:
            return True  # no restriction configured
        try:
            target_net = ipaddress.ip_network(target, strict=False)
        except ValueError:
            # hostname or unparseable — let LLM critic handle semantic issues
            return True
        for allowed_entry in allowed:
            try:
                allowed_net = ipaddress.ip_network(allowed_entry, strict=False)
                if target_net.subnet_of(allowed_net):
                    return True
            except ValueError:
                continue
        return False

    def _assess_danger_level(self, tool_calls: list[dict]) -> tuple[str, str]:
        """Classify the danger level of proposed tool calls.

        Returns:
            (level, reason) where level is LOW | MEDIUM | HIGH | BLOCKED.
        """
        allowed_targets = config.ALLOWED_TARGETS

        for tc in tool_calls:
            name = tc["name"]
            args = tc.get("args", {})

            # retrieve_context is always safe
            if name == "retrieve_context":
                continue

            # ── BLOCKED: target outside allowed scope ──
            if name == "execute_nmap_scan" and allowed_targets:
                for t in self._extract_targets_from_nmap(args.get("command", "")):
                    if not self._is_target_allowed(t, allowed_targets):
                        return ("BLOCKED", f"Target '{t}' is outside allowed scope: {allowed_targets}")

            if name == "execute_msf_module" and allowed_targets:
                rhosts = args.get("options", {}).get("RHOSTS") or args.get("options", {}).get("rhosts", "")
                for t in str(rhosts).split():
                    if not self._is_target_allowed(t, allowed_targets):
                        return ("BLOCKED", f"Target '{t}' is outside allowed scope: {allowed_targets}")

            # ── HIGH: exploit modules ──
            if name == "execute_msf_module" and args.get("module_type") == "exploit":
                return ("HIGH", f"Exploit module requested: {args.get('module_name', '?')}")

            # ── HIGH: dangerous nmap patterns ──
            if name == "execute_nmap_scan":
                cmd = args.get("command", "")
                if re.search(r"--script[= ]?(exploit|vuln|brute|dos)", cmd, re.IGNORECASE):
                    return ("HIGH", f"Dangerous nmap script category detected in: {cmd}")
                if "-T5" in cmd:
                    return ("HIGH", f"Aggressive timing (-T5) in: {cmd}")
                # Large subnet scan
                for t in self._extract_targets_from_nmap(cmd):
                    cidr_match = re.search(r"/(\d+)$", t)
                    if cidr_match and int(cidr_match.group(1)) <= 16:
                        return ("HIGH", f"Large network scan (/{cidr_match.group(1)}) in target: {t}")

        # If any action tool is present, it's at least MEDIUM
        for tc in tool_calls:
            if tc["name"] in ("execute_nmap_scan", "execute_msf_module"):
                return ("MEDIUM", "Standard scan/auxiliary operation.")

        return ("LOW", "Information retrieval only.")

    # --- Critic Node (3-stage pipeline) ---

    def critic_node(self, state: MessagesState):
        """Critic: validates proposed tool calls via a 3-stage pipeline.

        Stage 1: Schema validation — deterministic format checks.
        Stage 2: Danger-level assessment — BLOCKED rejects, HIGH triggers
                 human-in-the-loop via interrupt().
        Stage 3: LLM review — nmap commands checked against RAG docs.
        """
        messages = state["messages"]
        last_ai_message = messages[-1]

        if not hasattr(last_ai_message, "tool_calls") or not last_ai_message.tool_calls:
            return {"messages": []}

        # ── Stage 1: Schema validation ──
        all_issues: list[str] = []
        for tc in last_ai_message.tool_calls:
            if tc["name"] == "execute_nmap_scan":
                cmd = tc["args"].get("command", "")
                if not cmd:
                    all_issues.append(
                        f"'execute_nmap_scan' requires a 'command' argument. "
                        f"Provided args: {tc['args']}."
                    )
                else:
                    all_issues.extend(self._validate_nmap_schema(cmd))
            elif tc["name"] == "execute_msf_module":
                all_issues.extend(self._validate_msf_schema(tc))

        if all_issues:
            return {"messages": [HumanMessage(content=(
                "CRITICISM DETECTED (schema validation):\n"
                + "\n".join(f"{issue}" for issue in all_issues)
                + "\n\nPlease correct the command(s) and try again."
            ))]}

        # ── Stage 2: Danger-level assessment ──
        level, reason = self._assess_danger_level(last_ai_message.tool_calls)

        if level == "BLOCKED":
            return {"messages": [HumanMessage(content=(
                f"CRITICISM DETECTED (scope violation):\n{reason}\n\n"
                "This target is outside the authorized engagement scope. "
                "Please choose a target within the allowed range."
            ))]}
        # if level == "HIGH":
        else:
            tool_summary = "\n".join(
                f"{tc['name']}({tc.get('args', {})})" for tc in last_ai_message.tool_calls
            )
            human_response = interrupt({
                "risk_level": "HIGH",
                "reason": reason,
                "proposed_actions": tool_summary,
                "prompt": "Approve these high-risk actions? (yes/no)",
            })
            if str(human_response).strip().lower() not in ("yes", "y", "approve"):
                return {"messages": [HumanMessage(content=(
                    "CRITICISM DETECTED (operator denied):\n"
                    f"High-risk action rejected by operator: {reason}\n\n"
                    "Please propose a less aggressive alternative."
                ))]}

        # ── Stage 3: LLM review for action tool calls against documentation ──
        action_calls = [
            tc for tc in last_ai_message.tool_calls
            if tc["name"] in ("execute_nmap_scan", "execute_msf_module")
        ]
        if not action_calls:
            return {"messages": []}  # Only retrieve_context — nothing to review

        # Build a summary of all proposed actions for the critic
        proposed_parts: list[str] = []
        for tc in action_calls:
            if tc["name"] == "execute_nmap_scan":
                proposed_parts.append(f"[Nmap] {tc['args'].get('command', '')}")
            elif tc["name"] == "execute_msf_module":
                args = tc.get("args", {})
                proposed_parts.append(
                    f"[Metasploit] module_type={args.get('module_type', '?')}, "
                    f"module_name={args.get('module_name', '?')}, "
                    f"options={args.get('options', {})}"
                )
        proposed_summary = "\n".join(proposed_parts)

        # Retrieve the latest RAG context from message history
        rag_context = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and m.name == "retrieve_context":
                rag_context = m.content
                break

        # Invoke LLM as the Critic
        critic_response = self.critic_model.invoke([
            SystemMessage(content=config.CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"DOCUMENTATION CONTEXT:\n{rag_context}\n\n"
                f"PROPOSED ACTIONS:\n{proposed_summary}"
            ))
        ])

        # Logic: robust VALID / INVALID parsing.
        critic_text = str(critic_response.content).strip()
        critic_upper = critic_text.upper()

        # Reject explicit INVALID (avoid misclassifying because "INVALID" contains "VALID").
        if re.search(r"\bINVALID\b", critic_upper):
            return {"messages": [HumanMessage(content=(
                f"CRITICISM DETECTED:\n{critic_text}\n\n"
                "Please correct the command(s) and try again."
            ))]}

        # Accept explicit VALID regardless of explanation length.
        # Support forms like "VALID" or "VALID: ..." on the first line.
        first_line_upper = critic_upper.splitlines()[0] if critic_upper else ""
        if re.match(r"^\s*VALID\b", first_line_upper) or re.search(r"\bVALID\b", critic_upper):
            return {"messages": []}  # Pass

        # Fallback: unrecognized critic format => treat as rejection for safety.
        return {"messages": [HumanMessage(content=(
            f"CRITICISM DETECTED:\n{critic_text}\n\n"
            "Please correct the command(s) and try again."
        ))]}

    def analyst_node(self, state: MessagesState):
        """Analyst: interprets tool results and maps findings to severity/risk levels."""
        def _parse_llm_findings(response: str) -> list[dict]:
            """Parse the LLM response into structured findings."""
            findings = []
            for line in response.split("\n"):
                if line.startswith("FINDING:"):
                    # Extract severity and description
                    parts = line[len("FINDING:"):].strip().split(" ", 1)
                    if len(parts) == 2:
                        severity, description = parts
                        findings.append({
                            "severity": severity.strip("[]"),
                            "description": description.strip(),
                        })
            return findings
    
        messages = state["messages"]

        tool_messages: list = []
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

        findings = _parse_llm_findings(analyst_response.content)
        analyst_message = HumanMessage(content=f"Tool Call Analysis:\n{analyst_response.content}")

        return {"messages": [analyst_message], "findings": findings}

    # --- Conditional Edges ---

    def route_after_planner(self, state: MessagesState) -> Literal["tactician", "__end__"]:
        """After the Planner runs, decide whether to continue or finish."""
        phase = state.get("current_phase", "recon")
        if phase == "complete":
            return END
        return "tactician"

    def route_after_tactician(self, state: MessagesState) -> Literal["critic_node", END]:
        """After the Tactician runs, check if there are tool calls to review."""
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "critic_node"
        return END

    def route_after_critic(self, state: MessagesState) -> Literal["tactician", "tool_node", END]:
        """After the Critic runs, either loop back to fix or proceed to execute."""
        last_message = state["messages"][-1]
        
        if isinstance(last_message, HumanMessage) and "CRITICISM DETECTED" in last_message.content:
            return "tactician"  # Loop back to fix
        
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
        """Build the StateGraph: START -> planner -> tactician -> critic -> tool_node -> analyst -> planner."""
        agent_builder = StateGraph(MessagesState)

        # Add nodes
        agent_builder.add_node("planner", self.planner_node)
        agent_builder.add_node("tactician", self.tactician_node)
        agent_builder.add_node("tool_node", self.tool_node)
        agent_builder.add_node("critic_node", self.critic_node)
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
        # Tactician -> Critic / END
        agent_builder.add_conditional_edges(
            "tactician",
            self.route_after_tactician,
            {"critic_node": "critic_node", END: END},
        )
        # Critic -> Tactician (fix) / tool_node (execute)
        agent_builder.add_conditional_edges(
            "critic_node",
            self.route_after_critic,
            {"tactician": "tactician", "tool_node": "tool_node", END: END},
        )
        # tool_node -> analyst_node -> planner
        agent_builder.add_edge("tool_node", "analyst_node")
        agent_builder.add_edge("analyst_node", "planner")

        return agent_builder.compile()

def get_agent():
    """
    Factory function to get the agent with compiled graph.
    """
    return RedTeamAgent()
