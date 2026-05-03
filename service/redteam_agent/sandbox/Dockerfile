# =============================================================================
# AI-RedTeam Agent Container
# =============================================================================
# Full agent service image — runs the complete RedTeam agent (LangGraph loop,
# tools, LLM access) inside an isolated Docker container.  Each agent run
# gets its own container with restricted networking via iptables.
#
# The Backend creates and manages these containers via Docker API.
#
# Build:
#   docker build -t redteam-agent:latest -f service/redteam_agent/sandbox/Dockerfile .
# =============================================================================

FROM kalilinux/kali-rolling:latest

LABEL maintainer="AI-RedTeam"
LABEL description="Full AI agent service with penetration-testing tools in an isolated container"

# ── Avoid interactive prompts during package install ─────────────────────────
ENV DEBIAN_FRONTEND=noninteractive

# ── Install tools + Python runtime ──────────────────────────────────────────
# Only packages the agent actually needs at runtime.  Metasploit MUST run
# inside the container so all exploitation traffic is subject to iptables
# network restrictions — msfrpcd is started by entrypoint.sh.
#
# To add more tools later, append them here and rebuild the image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # ── Scanning (used by execute_nmap_scan tool) ──
    nmap \
    # ── Exploitation framework (msfrpcd runs inside container) ──
    metasploit-framework \
    # ── Python (agent service runtime) ──
    python3 \
    python3-pip \
    python3-venv \
    # ── Network lockdown (used by entrypoint.sh) ──
    iptables \
    iproute2 \
    # ── Minimal debug / connectivity helpers ──
    iputils-ping \
    curl \
    dnsutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Create working directory ─────────────────────────────────────────────────
WORKDIR /opt/redteam

# ── Install Python dependencies first (layer caching) ───────────────────────
COPY service/requirements.txt /opt/redteam/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed \
        -r /opt/redteam/requirements.txt \
    && pip3 install --no-cache-dir --break-system-packages --ignore-installed \
        fastapi uvicorn

# ── Copy the agent service code ─────────────────────────────────────────────
COPY service/redteam_agent/ /opt/redteam/redteam_agent/

# ── Copy documentation used by the RAG system ───────────────────────────────
COPY doc/ /opt/redteam/doc/

# ── Create output directory for scan artifacts ───────────────────────────────
RUN mkdir -p /opt/redteam/output && chmod 777 /opt/redteam/output

# ── Network-restriction entrypoint ──────────────────────────────────────────
# The entrypoint script sets iptables rules that only allow traffic to the
# designated TARGET_IP and ALLOWED_HOSTS.  All other outbound traffic is dropped.
COPY service/redteam_agent/sandbox/entrypoint.sh /opt/redteam/entrypoint.sh
RUN chmod +x /opt/redteam/entrypoint.sh

# ── Expose the agent API port ───────────────────────────────────────────────
EXPOSE 8100

ENTRYPOINT ["/opt/redteam/entrypoint.sh"]
CMD ["python3", "-m", "redteam_agent.api"]
