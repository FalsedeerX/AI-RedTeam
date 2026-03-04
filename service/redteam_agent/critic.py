"""Critic pipeline — 3-stage validation for proposed tool calls.

Stage 1: Schema validation (deterministic format checks).
Stage 2: Danger-level assessment (BLOCKED rejects, HIGH triggers human-in-the-loop).
Stage 3: LLM review (action commands checked against RAG documentation).
"""

import ipaddress
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.types import interrupt

from .config import config

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_MSF_MODULE_TYPES = ("auxiliary", "exploit", "post", "payload", "encoder", "nop")

# Nmap flags that consume the next token as their value (for target extraction)
_NMAP_FLAGS_WITH_ARGS = frozenset({
    "-p", "-oN", "-oX", "-oG", "-oA", "-e", "-S", "-D",
    "-g", "--source-port", "--top-ports", "-iL", "-sI",
    "--script", "--exclude", "--excludefile", "--max-rate",
    "--min-rate", "--max-retries", "--host-timeout",
    "--scan-delay", "--max-scan-delay",
})


class CriticPipeline:
    """Three-stage validation pipeline for proposed tool calls.

    Parameters
    ----------
    critic_model : Any
        A LangChain-compatible chat model used for Stage 3 (LLM review).
    """

    def __init__(self, critic_model: Any) -> None:
        self.critic_model = critic_model

    # ── public entry point (called by agent.critic_node) ──────────────

    def evaluate(self, state: dict) -> dict:
        """Run the 3-stage pipeline and return a state update dict.

        Returns ``{"messages": []}`` when all checks pass, or
        ``{"messages": [HumanMessage(...)]}`` with feedback on failure.
        """
        messages = state["messages"]
        last_ai_message = messages[-1]

        if not hasattr(last_ai_message, "tool_calls") or not last_ai_message.tool_calls:
            return {"messages": []}

        tool_calls = last_ai_message.tool_calls

        # Stage 1 ─ Schema validation
        result = self._stage_schema_validation(tool_calls)
        if result is not None:
            return result

        # Stage 2 ─ Danger-level assessment
        result = self._stage_danger_assessment(tool_calls)
        if result is not None:
            return result

        # Stage 3 ─ LLM review
        return self._stage_llm_review(tool_calls, messages)

    # ── Stage 1: Schema validation ────────────────────────────────────

    @staticmethod
    def validate_nmap_schema(command: str) -> list[str]:
        """Minimal format checks for nmap commands."""
        issues: list[str] = []
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
    def validate_msf_schema(tool_call: dict) -> list[str]:
        """Minimal format checks for MSF module parameters."""
        issues: list[str] = []
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
                    issues.append(f"RPORT {rport} out of range (1\u201365535).")
            except (ValueError, TypeError):
                issues.append(f"RPORT '{rport}' is not a valid integer.")
        return issues

    def _stage_schema_validation(self, tool_calls: list[dict]) -> dict | None:
        """Return feedback dict if schema issues found, else ``None``."""
        all_issues: list[str] = []
        for tc in tool_calls:
            if tc["name"] == "execute_nmap_scan":
                cmd = tc["args"].get("command", "")
                if not cmd:
                    all_issues.append(
                        f"'execute_nmap_scan' requires a 'command' argument. "
                        f"Provided args: {tc['args']}."
                    )
                else:
                    all_issues.extend(self.validate_nmap_schema(cmd))
            elif tc["name"] == "execute_msf_module":
                all_issues.extend(self.validate_msf_schema(tc))

        if all_issues:
            return {"messages": [HumanMessage(content=(
                "CRITICISM DETECTED (schema validation):\n"
                + "\n".join(f"  \u2022 {issue}" for issue in all_issues)
                + "\n\nPlease correct the command(s) and try again."
            ))]}
        return None

    # ── Stage 2: Danger-level assessment ──────────────────────────────

    @staticmethod
    def extract_targets_from_nmap(command: str) -> list[str]:
        """Extract target arguments from an nmap command string."""
        parts = command.strip().split()
        targets: list[str] = []
        skip_next = False
        for arg in parts[1:]:  # skip 'nmap'
            if skip_next:
                skip_next = False
                continue
            if arg in _NMAP_FLAGS_WITH_ARGS:
                skip_next = True
                continue
            if arg.startswith("-"):
                continue
            targets.append(arg)
        return targets

    @staticmethod
    def is_target_allowed(target: str, allowed: list[str]) -> bool:
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

    def assess_danger_level(self, tool_calls: list[dict]) -> tuple[str, str]:
        """Classify the danger level of proposed tool calls.

        Returns
        -------
        (level, reason) where level is ``LOW | MEDIUM | HIGH | BLOCKED``.
        """
        allowed_targets = config.ALLOWED_TARGETS

        for tc in tool_calls:
            name = tc["name"]
            args = tc.get("args", {})

            if name == "retrieve_context":
                continue

            # BLOCKED: target outside allowed scope
            if name == "execute_nmap_scan" and allowed_targets:
                for t in self.extract_targets_from_nmap(args.get("command", "")):
                    if not self.is_target_allowed(t, allowed_targets):
                        return ("BLOCKED", f"Target '{t}' is outside allowed scope: {allowed_targets}")

            if name == "execute_msf_module" and allowed_targets:
                rhosts = args.get("options", {}).get("RHOSTS") or args.get("options", {}).get("rhosts", "")
                for t in str(rhosts).split():
                    if not self.is_target_allowed(t, allowed_targets):
                        return ("BLOCKED", f"Target '{t}' is outside allowed scope: {allowed_targets}")

            # HIGH: exploit modules
            if name == "execute_msf_module" and args.get("module_type") == "exploit":
                return ("HIGH", f"Exploit module requested: {args.get('module_name', '?')}")

            # HIGH: dangerous nmap patterns
            if name == "execute_nmap_scan":
                cmd = args.get("command", "")
                if re.search(r"--script[= ]?(exploit|vuln|brute|dos)", cmd, re.IGNORECASE):
                    return ("HIGH", f"Dangerous nmap script category detected in: {cmd}")
                if "-T5" in cmd:
                    return ("HIGH", f"Aggressive timing (-T5) in: {cmd}")
                for t in self.extract_targets_from_nmap(cmd):
                    cidr_match = re.search(r"/(\d+)$", t)
                    if cidr_match and int(cidr_match.group(1)) <= 16:
                        return ("HIGH", f"Large network scan (/{cidr_match.group(1)}) in target: {t}")

        # Any action tool present → MEDIUM
        for tc in tool_calls:
            if tc["name"] in ("execute_nmap_scan", "execute_msf_module"):
                return ("MEDIUM", "Standard scan/auxiliary operation.")

        return ("LOW", "Information retrieval only.")

    def _stage_danger_assessment(self, tool_calls: list[dict]) -> dict | None:
        """Return feedback dict if blocked/denied, else ``None``."""
        level, reason = self.assess_danger_level(tool_calls)

        if level == "BLOCKED":
            return {"messages": [HumanMessage(content=(
                f"CRITICISM DETECTED (scope violation):\n  \u2022 {reason}\n\n"
                "This target is outside the authorized engagement scope. "
                "Please choose a target within the allowed range."
            ))]}

        if level == "HIGH":
            tool_summary = "\n".join(
                f"  \u2022 {tc['name']}({tc.get('args', {})})" for tc in tool_calls
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
                    f"  \u2022 High-risk action rejected by operator: {reason}\n\n"
                    "Please propose a less aggressive alternative."
                ))]}

        return None  # MEDIUM / LOW — pass through

    # ── Stage 3: LLM review ──────────────────────────────────────────

    def _stage_llm_review(self, tool_calls: list[dict], messages: list) -> dict:
        """LLM-based review of action tool calls against RAG documentation."""
        action_calls = [
            tc for tc in tool_calls
            if tc["name"] in ("execute_nmap_scan", "execute_msf_module")
        ]
        if not action_calls:
            return {"messages": []}  # Only retrieve_context — nothing to review

        # Build a summary of all proposed actions
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

        critic_response = self.critic_model.invoke([
            SystemMessage(content=config.CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"DOCUMENTATION CONTEXT:\n{rag_context}\n\n"
                f"PROPOSED ACTIONS:\n{proposed_summary}"
            ))
        ])

        critic_text = str(critic_response.content).strip()
        critic_upper = critic_text.upper()

        # Reject explicit INVALID (check before VALID since "INVALID" contains "VALID")
        if re.search(r"\bINVALID\b", critic_upper):
            return {"messages": [HumanMessage(content=(
                f"CRITICISM DETECTED:\n{critic_text}\n\n"
                "Please correct the command(s) and try again."
            ))]}

        # Accept explicit VALID
        first_line_upper = critic_upper.splitlines()[0] if critic_upper else ""
        if re.match(r"^\s*VALID\b", first_line_upper) or re.search(r"\bVALID\b", critic_upper):
            return {"messages": []}  # Pass

        # Fallback: unrecognized format → treat as rejection for safety
        return {"messages": [HumanMessage(content=(
            f"CRITICISM DETECTED:\n{critic_text}\n\n"
            "Please correct the command(s) and try again."
        ))]}
