"""Unit tests for the CriticPipeline — schema validation, scope enforcement,
and risk assessment.

These tests exercise the deterministic (non-LLM) stages of the Critic:
  Stage 1 — Schema validation (nmap command format, MSF module parameters)
  Stage 2 — Scope checking (allowed target CIDRs) and risk-level classification

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
    """Create a CriticPipeline with a mock model (Stage 3 not exercised)."""
    return CriticPipeline(critic_model=MagicMock())


# ═══════════════════════════════════════════════════════════
# Stage 1: Nmap Schema Validation
# ═══════════════════════════════════════════════════════════

class TestNmapSchemaValidation:
    """Tests for CriticPipeline.validate_nmap_schema."""

    def test_valid_basic_scan(self):
        """A standard nmap SYN scan passes schema validation."""
        result = CriticPipeline.validate_nmap_schema(
            {"command": "nmap -sS -T4 192.168.1.1"}
        )
        assert result is None

    def test_valid_version_detection(self):
        """Version detection scan with port specification passes."""
        result = CriticPipeline.validate_nmap_schema(
            {"command": "nmap -sV -T4 -p 80,443,8080 10.0.0.1"}
        )
        assert result is None

    def test_valid_top_ports(self):
        """Top-ports scan passes schema validation."""
        result = CriticPipeline.validate_nmap_schema(
            {"command": "nmap -sS -T4 --top-ports 1000 127.0.0.1"}
        )
        assert result is None

    def test_valid_cidr_target(self):
        """CIDR notation target passes validation."""
        result = CriticPipeline.validate_nmap_schema(
            {"command": "nmap -sS 192.168.1.0/24"}
        )
        assert result is None

    def test_empty_command_rejected(self):
        """Empty command string is rejected."""
        result = CriticPipeline.validate_nmap_schema({"command": ""})
        assert result is not None
        assert "requires a 'command' argument" in result

    def test_missing_command_key_rejected(self):
        """Missing 'command' key is rejected."""
        result = CriticPipeline.validate_nmap_schema({})
        assert result is not None

    def test_non_nmap_command_rejected(self):
        """Command that doesn't start with 'nmap' is rejected."""
        result = CriticPipeline.validate_nmap_schema(
            {"command": "ping 127.0.0.1"}
        )
        assert result is not None
        assert "must start with 'nmap'" in result.lower()

    def test_whitespace_only_command_rejected(self):
        """Whitespace-only command string is rejected."""
        result = CriticPipeline.validate_nmap_schema(
            {"command": "   "}
        )
        assert result is not None

    def test_misplaced_port_spec_rejected(self):
        """Numeric-only non-flag token is flagged as misplaced port spec."""
        result = CriticPipeline.validate_nmap_schema(
            {"command": "nmap -sS 80"}
        )
        assert result is not None
        assert "misplaced port specification" in result.lower()


# ═══════════════════════════════════════════════════════════
# Stage 1: MSF Schema Validation
# ═══════════════════════════════════════════════════════════

class TestMsfSchemaValidation:
    """Tests for CriticPipeline.validate_msf_schema."""

    def test_valid_auxiliary_module(self):
        """Valid auxiliary module passes."""
        result = CriticPipeline.validate_msf_schema({
            "module_type": "auxiliary",
            "module_name": "scanner/smb/smb_ms17_010",
            "options": {"RHOSTS": "192.168.1.1"},
        })
        assert result is None

    def test_valid_exploit_module(self):
        """Valid exploit module passes."""
        result = CriticPipeline.validate_msf_schema({
            "module_type": "exploit",
            "module_name": "windows/smb/ms17_010_eternalblue",
            "options": {"RHOSTS": "192.168.1.1", "RPORT": 445},
        })
        assert result is None

    def test_invalid_module_type_rejected(self):
        """Invalid module_type is rejected."""
        result = CriticPipeline.validate_msf_schema({
            "module_type": "scanner",
            "module_name": "test/module",
        })
        assert result is not None
        assert "invalid module_type" in result.lower()

    def test_rport_out_of_range_rejected(self):
        """RPORT outside 1-65535 is rejected."""
        result = CriticPipeline.validate_msf_schema({
            "module_type": "auxiliary",
            "module_name": "scanner/http/http_version",
            "options": {"RPORT": 99999},
        })
        assert result is not None
        assert "out of range" in result.lower()

    def test_rport_negative_rejected(self):
        """Negative RPORT is rejected."""
        result = CriticPipeline.validate_msf_schema({
            "module_type": "auxiliary",
            "options": {"RPORT": -1},
        })
        assert result is not None

    def test_rport_non_integer_rejected(self):
        """Non-integer RPORT is rejected."""
        result = CriticPipeline.validate_msf_schema({
            "module_type": "auxiliary",
            "options": {"RPORT": "abc"},
        })
        assert result is not None
        assert "not a valid integer" in result.lower()

    def test_valid_rport_as_string(self):
        """String-encoded valid port passes."""
        result = CriticPipeline.validate_msf_schema({
            "module_type": "auxiliary",
            "options": {"RPORT": "8080"},
        })
        assert result is None


# ═══════════════════════════════════════════════════════════
# Stage 2: Risk Assessment
# ═══════════════════════════════════════════════════════════

class TestRiskAssessment:
    """Tests for risk-level classification (nmap and MSF)."""

    def test_nmap_exploit_script_high(self, critic):
        """Nmap exploit script category triggers HIGH risk."""
        level, _ = critic.assess_nmap_risk(
            {"command": "nmap --script exploit 192.168.1.1"}
        )
        assert level == "HIGH"

    def test_nmap_vuln_script_high(self, critic):
        """Nmap vuln script category triggers HIGH risk."""
        level, _ = critic.assess_nmap_risk(
            {"command": "nmap --script vuln 192.168.1.1"}
        )
        assert level == "HIGH"

    def test_nmap_aggressive_timing_high(self, critic):
        """Aggressive timing -T5 triggers HIGH risk."""
        level, _ = critic.assess_nmap_risk(
            {"command": "nmap -T5 192.168.1.1"}
        )
        assert level == "HIGH"

    def test_nmap_full_udp_scan_high(self, critic):
        """Full-port UDP scan triggers HIGH risk."""
        level, _ = critic.assess_nmap_risk(
            {"command": "nmap -sU -p 1-65535 192.168.1.1"}
        )
        assert level == "HIGH"

    def test_nmap_large_cidr_high(self, critic):
        """Large CIDR (/16 or below) triggers HIGH risk."""
        level, _ = critic.assess_nmap_risk(
            {"command": "nmap -sS 10.0.0.0/8"}
        )
        assert level == "HIGH"

    def test_nmap_standard_scan_medium(self, critic):
        """Standard SYN scan is MEDIUM risk."""
        level, _ = critic.assess_nmap_risk(
            {"command": "nmap -sS -T4 192.168.1.1"}
        )
        assert level == "MEDIUM"

    def test_msf_exploit_module_high(self, critic):
        """Exploit modules are always HIGH risk."""
        level, _ = critic.assess_msf_risk({
            "module_type": "exploit",
            "module_name": "windows/smb/ms17_010_eternalblue",
            "options": {"RHOSTS": "192.168.1.1"},
        })
        assert level == "HIGH"

    def test_msf_auxiliary_module_medium(self, critic):
        """Auxiliary scanner modules are MEDIUM risk."""
        level, _ = critic.assess_msf_risk({
            "module_type": "auxiliary",
            "module_name": "scanner/smb/smb_version",
            "options": {"RHOSTS": "192.168.1.1"},
        })
        assert level == "MEDIUM"


# ═══════════════════════════════════════════════════════════
# Stage 2: Scope Enforcement
# ═══════════════════════════════════════════════════════════

class TestScopeEnforcement:
    """Tests for target scope blocking."""

    def test_target_within_scope_allowed(self):
        """Target inside allowed CIDR is not blocked."""
        blocked = CriticPipeline._find_blocked_targets(
            ["192.168.1.10"], ["192.168.1.0/24"]
        )
        assert blocked == []

    def test_target_outside_scope_blocked(self):
        """Target outside allowed CIDR is blocked."""
        blocked = CriticPipeline._find_blocked_targets(
            ["10.0.0.1"], ["192.168.1.0/24"]
        )
        assert blocked == ["10.0.0.1"]

    def test_no_allowed_targets_means_unrestricted(self):
        """Empty allowed list means no restriction (all targets allowed)."""
        blocked = CriticPipeline._find_blocked_targets(
            ["10.0.0.1"], []
        )
        assert blocked == []

    def test_multiple_targets_mixed(self):
        """Mix of in-scope and out-of-scope targets."""
        blocked = CriticPipeline._find_blocked_targets(
            ["192.168.1.10", "10.0.0.1", "192.168.1.20"],
            ["192.168.1.0/24"],
        )
        assert blocked == ["10.0.0.1"]

    def test_nmap_blocked_extracts_targets(self, critic):
        """Nmap scope check correctly extracts targets from the command."""
        import redteam_agent.critic as critic_module
        original = critic_module.config.ALLOWED_TARGETS
        critic_module.config.ALLOWED_TARGETS = ["127.0.0.0/8"]
        try:
            blocked = critic.assess_nmap_blocked(
                {"command": "nmap -sS 10.0.0.1"}
            )
            assert blocked == ["10.0.0.1"]
        finally:
            critic_module.config.ALLOWED_TARGETS = original

    def test_nmap_localhost_within_scope(self, critic):
        """Localhost target within 127.0.0.0/8 is allowed."""
        import redteam_agent.critic as critic_module
        original = critic_module.config.ALLOWED_TARGETS
        critic_module.config.ALLOWED_TARGETS = ["127.0.0.0/8"]
        try:
            blocked = critic.assess_nmap_blocked(
                {"command": "nmap -sS -T4 127.0.0.1"}
            )
            assert blocked == []
        finally:
            critic_module.config.ALLOWED_TARGETS = original


# ═══════════════════════════════════════════════════════════
# Helper: Target Extraction
# ═══════════════════════════════════════════════════════════

class TestTargetExtraction:
    """Tests for _extract_targets_from_nmap helper."""

    def test_single_ip(self):
        """Extracts the IP target (note: 'nmap' itself is also a non-flag token)."""
        targets = CriticPipeline._extract_targets_from_nmap(
            "nmap -sS 192.168.1.1"
        )
        assert "192.168.1.1" in targets

    def test_multiple_targets(self):
        """Both IP targets are extracted."""
        targets = CriticPipeline._extract_targets_from_nmap(
            "nmap -sS 192.168.1.1 10.0.0.1"
        )
        assert "192.168.1.1" in targets
        assert "10.0.0.1" in targets

    def test_port_flag_not_counted(self):
        """Port flag -p value should not appear as a target."""
        targets = CriticPipeline._extract_targets_from_nmap(
            "nmap -sS -p 80,443 192.168.1.1"
        )
        assert "192.168.1.1" in targets
        assert "80,443" not in targets

    def test_top_ports_value_not_counted(self):
        """--top-ports value should not appear as a target."""
        targets = CriticPipeline._extract_targets_from_nmap(
            "nmap -sS --top-ports 1000 127.0.0.1"
        )
        assert "127.0.0.1" in targets
        assert "1000" not in targets
