#!/bin/bash
# =============================================================================
# entrypoint.sh — Container network-restriction bootstrap
# =============================================================================
# Applies iptables rules that restrict outbound traffic to ONLY the
# designated target IP and explicitly allowed hosts (Ollama, MSF RPC, etc.).
#
# Allowed traffic:
#   - loopback (127.0.0.0/8)
#   - DNS resolution to the Docker-internal DNS server (127.0.0.11)
#   - the explicit TARGET_IP
#   - ALLOWED_HOSTS (Ollama, MSF RPC, backend, etc.)
#   - DOCKER_GATEWAY_IP (host.docker.internal)
#   - established / related return traffic
#
# Everything else is DROPPED.
# =============================================================================

set -e

echo "[agent-container] Configuring network restrictions …"

# ── Resolve host.docker.internal to its IPv4 address ─────────────────────────
# Docker Desktop adds both IPv4 and IPv6 entries in /etc/hosts.  The container
# often has no IPv6 route, so Python HTTP clients fail with "Network is
# unreachable" when they try the IPv6 address first.
# Fix: resolve to a numeric IPv4 address and rewrite environment variables so
# Python never attempts IPv6.
HOST_IPV4=$(getent ahostsv4 host.docker.internal 2>/dev/null | awk 'NR==1{print $1}')
if [ -n "$HOST_IPV4" ]; then
    echo "[agent-container] Resolved host.docker.internal → $HOST_IPV4 (IPv4)"
    # Rewrite env vars that may reference host.docker.internal
    for var in LLM_BASE_URL; do
        val=$(eval echo "\$$var")
        if echo "$val" | grep -q 'host\.docker\.internal'; then
            new_val=$(echo "$val" | sed "s/host\.docker\.internal/$HOST_IPV4/g")
            export "$var=$new_val"
            echo "[agent-container] Rewrote $var → $new_val"
        fi
    done
fi

# Flush any pre-existing rules
iptables -F OUTPUT 2>/dev/null || true

# 1. Allow loopback
iptables -A OUTPUT -o lo -j ACCEPT

# 2. Allow Docker-internal DNS (needed for Docker DNS resolution)
iptables -A OUTPUT -d 127.0.0.11 -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -d 127.0.0.11 -p tcp --dport 53 -j ACCEPT

# 3. Allow return traffic for established connections
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 4. Allow traffic to the designated target(s)
if [ -n "$TARGET_IP" ]; then
    for ip in $(echo "$TARGET_IP" | tr ',' ' '); do
        echo "[agent-container] Allowing outbound to target: $ip"
        iptables -A OUTPUT -d "$ip" -j ACCEPT
    done
fi

# 5. Allow traffic to additional hosts (Ollama, MSF RPC, Backend, etc.)
#    Comma-separated list of IPs/CIDRs passed via ALLOWED_HOSTS env var.
if [ -n "$ALLOWED_HOSTS" ]; then
    for ip in $(echo "$ALLOWED_HOSTS" | tr ',' ' '); do
        echo "[agent-container] Allowing outbound to host: $ip"
        iptables -A OUTPUT -d "$ip" -j ACCEPT
    done
fi

# 6. Allow traffic to the Docker gateway (host.docker.internal)
#    On Docker Desktop the host-gateway IP (192.168.65.254) differs from the
#    bridge gateway (172.17.0.1).  Resolve it dynamically to be safe.
if [ -n "$DOCKER_GATEWAY_IP" ]; then
    echo "[agent-container] Allowing outbound to Docker gateway: $DOCKER_GATEWAY_IP"
    iptables -A OUTPUT -d "$DOCKER_GATEWAY_IP" -j ACCEPT
fi

# 6b. Allow traffic to host.docker.internal's resolved IPv4 address.
#     On Docker Desktop the host-gateway IP differs from the bridge gateway,
#     so we reuse $HOST_IPV4 that was resolved at the top of this script.
if [ -n "$HOST_IPV4" ]; then
    echo "[agent-container] Allowing outbound to host.docker.internal ($HOST_IPV4)"
    iptables -A OUTPUT -d "$HOST_IPV4" -j ACCEPT
fi

# 7. DROP everything else
iptables -A OUTPUT -j DROP

echo "[agent-container] Network restrictions applied.  Outbound traffic limited to target(s) and allowed hosts."

# =============================================================================
# Start Metasploit RPC daemon (msfrpcd) locally so all exploitation traffic
# originates from this container and is subject to the iptables rules above.
# =============================================================================
MSF_RPC_USER="${MSF_RPC_USER:-msf}"
MSF_RPC_PASS="${MSF_RPC_PASS:-msf123}"
MSF_RPC_PORT="${MSF_RPC_PORT:-55552}"
MSF_RPC_SSL="${MSF_RPC_SSL:-false}"

SSL_FLAG="-S"
if [ "$MSF_RPC_SSL" = "true" ]; then
    SSL_FLAG=""
fi

echo "[agent-container] Starting msfrpcd on 127.0.0.1:${MSF_RPC_PORT} …"
msfrpcd -U "$MSF_RPC_USER" -P "$MSF_RPC_PASS" \
        -a 127.0.0.1 -p "$MSF_RPC_PORT" $SSL_FLAG -f &
MSFRPCD_PID=$!

# Give msfrpcd a moment to bind
sleep 3
if kill -0 $MSFRPCD_PID 2>/dev/null; then
    echo "[agent-container] msfrpcd started (PID $MSFRPCD_PID)"
else
    echo "[agent-container] WARNING: msfrpcd failed to start — MSF tools will be unavailable"
fi

echo "[agent-container] Starting agent service: $@"
exec "$@"
