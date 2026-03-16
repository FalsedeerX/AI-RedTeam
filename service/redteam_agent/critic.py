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


def _strip_think_tags(text: str) -> str:
    """Remove qwen3 ``<think>`` artifacts from *text*."""
    # 1. Paired blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # 2. Remaining unpaired tags: <think>, </think>, <think, </think
    text = re.sub(r"</?think>?", "", text)
    # 3. Bare /think
    text = re.sub(r"/think\b", "", text)
    # 4. Collapse whitespace gaps
    text = re.sub(r" {2,}", " ", text)
    return text.strip()

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

    # --- Stage 1: Schema validation ---

    @staticmethod
    def _extract_targets_from_nmap(command: str) -> list[str]:
        """Extract target arguments from an nmap command string."""
        parts = command.strip().split()
        targets: list[str] = []
        i = 0
        while i < len(parts):
            if not parts[i].startswith("-"):
                targets.append(parts[i])
            i += 2 if parts[i] in _NMAP_FLAGS_WITH_ARGS else 1
        return targets

    @classmethod
    def validate_nmap_schema(cls, args: dict) -> str | None:
        """Minimal format checks for nmap commands."""
        command = args.get("command", "")
        # Ensure command is a non-empty string
        if not command or not command.strip():
            return (
                f"'execute_nmap_scan' requires a 'command' argument. "
                f"Provided args: {args}."
            )
        # Ensure command starts with 'nmap' (case-insensitive)
        parts = command.strip().split()
        if not parts or parts[0].lower() != "nmap":
            return "Command must start with 'nmap'."
        # Ensure at least one target is specified (non-flag argument)
        targets = cls._extract_targets_from_nmap(command)
        if not targets:
            return "No target host specified in the nmap command."
        for t in targets:
            try:
                ipaddress.ip_network(t, strict=False)
            except ValueError:
                if re.match(r"^\d[\d,./-]*$", t):
                    return (
                        f"'{t}' is not a valid IP address or CIDR and appears "
                        f"to be a misplaced port specification. Use: -p {t}"
                    )
        return None

    @staticmethod
    def validate_msf_schema(args: dict) -> str | None:
        """Minimal format checks for MSF module parameters."""
        # Ensure module_type is valid
        module_type = args.get("module_type", "")
        if module_type not in VALID_MSF_MODULE_TYPES:
            return (
                f"Invalid module_type '{module_type}'. "
                f"Must be one of: {', '.join(VALID_MSF_MODULE_TYPES)}."
            )
        # Ensure rport (if present) is a valid integer port number
        rport = args.get("options", {}).get("RPORT") or args.get("options", {}).get("rport")
        if rport is not None:
            try:
                port_int = int(rport)
                if not (1 <= port_int <= 65535):
                    return f"RPORT {rport} out of range (1~65535)."
            except (ValueError, TypeError):
                return f"RPORT '{rport}' is not a valid integer."
        return None

    # --- Stage 2: Danger-level assessment ---

    @staticmethod
    def _find_blocked_targets(targets: list[str], allowed: list[str]) -> list[str]:
        """Return targets that fall outside all allowed networks.

        Hostnames and unparseable values are skipped (deferred to LLM review).
        Returns an empty list when *allowed* is empty (no restriction configured).
        """
        if not allowed or not targets:
            return []
        allowed_nets = []
        blocked = []
        for entry in allowed:
            try:
                allowed_nets.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                continue
        for target in targets:
            try:
                target_net = ipaddress.ip_network(target, strict=False)
            except ValueError:
                continue  # hostname or unparseable — let LLM critic handle
            if not any(target_net.subnet_of(net) for net in allowed_nets):
                blocked.append(target)
        return blocked
    
    def assess_nmap_blocked(self, args: dict) -> list[str]:
        """Return nmap targets that fall outside the allowed scope."""
        targets = self._extract_targets_from_nmap(args.get("command", ""))
        return self._find_blocked_targets(targets, config.ALLOWED_TARGETS)

    def assess_nmap_risk(self, args: dict) -> tuple[str, str]:
        """Assess nmap command for HIGH-risk patterns.

        Returns (level, reason) where level is ``HIGH`` or ``MEDIUM``.
        """
        command = args.get("command", "")
        if re.search(r"--script[= ]?(exploit|vuln|brute|dos)", command, re.IGNORECASE):
            return ("HIGH", f"Dangerous nmap script category detected in: {command}")
        if "-T5" in command:
            return ("HIGH", f"Aggressive timing (-T5) in: {command}")
        # Full-port UDP scan is extremely slow (can take 30+ min) and will
        # almost certainly exceed the subprocess timeout.
        has_udp = bool(re.search(r"-sU", command))
        has_large_port_range = bool(
            re.search(r"-p\s*\d*-65535|1-65535|-p-", command)
        )
        if has_udp and has_large_port_range:
            return ("HIGH", f"Full-port UDP scan detected — extremely slow, likely to timeout: {command}")
        large_scan = []
        for t in self._extract_targets_from_nmap(command):
            cidr_match = re.search(r"/(\d+)$", t)
            if cidr_match and int(cidr_match.group(1)) <= 16:
                large_scan.append((cidr_match.group(1), t))
        if large_scan:
            details = "; ".join(f"{t} (/{mask})" for mask, t in large_scan)
            return ("HIGH", f"Large network scan detected in target(s): {details}")
        return ("MEDIUM", "Standard nmap scan operation.")

    def assess_msf_blocked(self, args: dict) -> list[str]:
        """Return MSF targets that fall outside the allowed scope."""
        options = args.get("options", {})
        rhosts = options.get("RHOSTS") or options.get("rhosts", "")
        return self._find_blocked_targets(str(rhosts).split(), config.ALLOWED_TARGETS)

    def assess_msf_risk(self, args: dict) -> tuple[str, str]:
        """Assess Metasploit module for HIGH-risk patterns.

        Returns (level, reason) where level is ``HIGH`` or ``MEDIUM``.
        """
        module_type = args.get("module_type", "")
        module_name = args.get("module_name", "")
        options = args.get("options", {})
        # Normalize display: strip redundant module_type/ prefix that the LLM
        # sometimes includes in module_name (e.g. 'exploit/windows/smb/...')
        display_name = module_name
        if display_name.startswith(f"{module_type}/"):
            display_name = display_name[len(module_type) + 1:]
        if module_type == "exploit":
            return ("HIGH", f"Exploit module requested: {module_type}/{display_name} with options: {options}")
        return ("MEDIUM", "Standard Metasploit operation.")
    
    # --- Stage 3: LLM review ---

    def stage_llm_review(self, tool_calls: list[dict], messages: list) -> dict:
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
        # Look for both legacy ToolMessage (retrieve_context) and new RAG node results.
        rag_context = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and m.name == "retrieve_context":
                rag_context = m.content
                break
            if isinstance(m, HumanMessage) and "[RAG SEARCH RESULT" in m.content:
                rag_context = m.content
                break

        critic_response = self.critic_model.invoke([
            SystemMessage(content=config.CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"DOCUMENTATION CONTEXT:\n{rag_context}\n\n"
                f"PROPOSED ACTIONS:\n{proposed_summary}"
            ))
        ])

        critic_text = _strip_think_tags(str(critic_response.content))
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
