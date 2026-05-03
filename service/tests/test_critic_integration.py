"""Integration test — CriticPipeline multi-stage validation flow.

Tests the end-to-end validation pipeline (Stage 1 → Stage 2 → risk
classification) to ensure schema validation, scope enforcement, and risk
assessment work together correctly.

No external services (Ollama, Metasploit, Nmap) are required.
"""

import sys
import pytest
from unittest.mock import MagicMock
from pathlib import Path

# Add service directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from redteam_agent.critic import CriticPipeline


@pytest.fixture
def critic():
    """Create a CriticPipeline with a mock LLM model."""
    return CriticPipeline(critic_model=MagicMock())


class TestCriticPipelineIntegration:
    """End-to-end validation pipeline tests.

    Each test exercises the full Stage 1 → Stage 2 → risk flow,
    verifying that invalid inputs are caught at the earliest stage
    and valid inputs propagate through to correct risk classification.
    """

    def test_valid_nmap_passes_all_stages(self, critic):
        """A well-formed, in-scope nmap command passes schema + risk."""
        args = {"command": "nmap -sS -T4 --top-ports 1000 127.0.0.1"}

        # Stage 1: Schema validation
        schema_issue = CriticPipeline.validate_nmap_schema(args)
        assert schema_issue is None, f"Schema validation failed: {schema_issue}"

        # Stage 2: Risk classification
        level, reason = critic.assess_nmap_risk(args)
        assert level == "MEDIUM", (
            f"Expected MEDIUM risk for standard scan, got {level}: {reason}"
        )

    def test_malformed_nmap_rejected_at_schema(self, critic):
        """A non-nmap command is caught at Stage 1 before reaching risk."""
        args = {"command": "curl http://example.com"}

        schema_issue = CriticPipeline.validate_nmap_schema(args)
        assert schema_issue is not None
        # Pipeline should stop here — no risk assessment needed

    def test_out_of_scope_target_blocked(self, critic):
        """Valid schema but out-of-scope target is caught at Stage 2 scope."""
        import redteam_agent.critic as critic_module
        original = critic_module.config.ALLOWED_TARGETS
        critic_module.config.ALLOWED_TARGETS = ["192.168.1.0/24"]

        try:
            args = {"command": "nmap -sS 10.0.0.1"}

            # Stage 1: Schema passes
            schema_issue = CriticPipeline.validate_nmap_schema(args)
            assert schema_issue is None

            # Stage 2: Scope enforcement catches out-of-scope target
            blocked = critic.assess_nmap_blocked(args)
            assert "10.0.0.1" in blocked
        finally:
            critic_module.config.ALLOWED_TARGETS = original

    def test_msf_exploit_passes_schema_flagged_high(self, critic):
        """MSF exploit module passes schema but is flagged as HIGH risk."""
        args = {
            "module_type": "exploit",
            "module_name": "windows/smb/ms17_010_eternalblue",
            "options": {"RHOSTS": "192.168.1.1", "RPORT": 445},
        }

        # Stage 1: Schema validation
        schema_issue = CriticPipeline.validate_msf_schema(args)
        assert schema_issue is None

        # Stage 2: Risk classification
        level, reason = critic.assess_msf_risk(args)
        assert level == "HIGH"
        assert "exploit" in reason.lower()

    def test_msf_invalid_type_stops_at_schema(self, critic):
        """Invalid module_type is caught at schema, never reaches risk."""
        args = {
            "module_type": "scanner",  # not a valid module_type
            "module_name": "smb/smb_version",
            "options": {"RHOSTS": "192.168.1.1"},
        }

        schema_issue = CriticPipeline.validate_msf_schema(args)
        assert schema_issue is not None
        assert "invalid module_type" in schema_issue.lower()

    def test_all_dangerous_nmap_patterns_detected(self, critic):
        """Multiple dangerous nmap patterns are all identified as HIGH risk."""
        dangerous_commands = [
            "nmap --script exploit 192.168.1.1",
            "nmap --script vuln 192.168.1.1",
            "nmap -T5 192.168.1.1",
            "nmap -sU -p 1-65535 192.168.1.1",
            "nmap -sS 10.0.0.0/8",
        ]

        for cmd in dangerous_commands:
            args = {"command": cmd}
            # Stage 1: All are valid nmap commands
            schema_issue = CriticPipeline.validate_nmap_schema(args)
            assert schema_issue is None, (
                f"Schema rejected valid dangerous command: {cmd}"
            )
            # Stage 2: All should be HIGH risk
            level, reason = critic.assess_nmap_risk(args)
            assert level == "HIGH", (
                f"Expected HIGH for '{cmd}', got {level}: {reason}"
            )
