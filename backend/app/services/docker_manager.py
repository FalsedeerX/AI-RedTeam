"""
docker_manager.py — Backend-side Docker container lifecycle management.

The Backend uses this module to spin up / tear down full agent-service
containers.  Each scan job gets its own isolated container running the
complete RedTeam agent (LangGraph loop, tools, LLM calls) on port 8100.

Architecture
------------
Backend (host)  ──HTTP──>  agent-container (Docker, port 8100)
                             └── runs redteam_agent.api (FastAPI)
                             └── runs nmap, MSF modules natively
                             └── iptables restricts outbound to target only

Public API
----------
create_agent_container(project_id, target_ip)  → container_url
get_container_url(project_id)                  → url | None
destroy_agent_container(project_id)            → None
recover_containers()                           → dict[project_id, url]
cleanup_stale_containers()                     → int
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import time
from typing import Any, Optional

try:
    import docker
    from docker.errors import DockerException, NotFound, APIError
    _DOCKER_AVAILABLE = True
except ImportError:
    _DOCKER_AVAILABLE = False
    DockerException = Exception  # type: ignore[misc]
    NotFound = Exception         # type: ignore[misc]
    APIError = Exception         # type: ignore[misc]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — loaded from environment / backend settings
# ---------------------------------------------------------------------------

SANDBOX_IMAGE: str = os.getenv("DOCKER_SANDBOX_IMAGE", "redteam-agent:latest")
CONTAINER_PREFIX: str = "redteam-agent"
NETWORK_PREFIX: str = "redteam-net"
CONTAINER_MEM_LIMIT: str = os.getenv("DOCKER_MEM_LIMIT", "2g")
CONTAINER_CPU_QUOTA: int = int(os.getenv("DOCKER_CPU_QUOTA", "150000"))
CONTAINER_CPU_PERIOD: int = 100_000
AGENT_CONTAINER_PORT: int = 8100

# Whether Docker sandboxing is enabled at all.
# Force-disabled when the ``docker`` Python package is not installed.
DOCKER_ENABLED: bool = (
    _DOCKER_AVAILABLE
    and os.getenv("DOCKER_SANDBOX_ENABLED", "false").lower() == "true"
)


# ---------------------------------------------------------------------------
# Docker client singleton
# ---------------------------------------------------------------------------

_client: Any = None


def _get_client():
    """Return a lazily-initialised Docker client."""
    if not _DOCKER_AVAILABLE:
        raise RuntimeError(
            "The 'docker' Python package is not installed.\n"
            "Install it with: pip install docker>=7.0.0"
        )
    global _client
    if _client is None:
        try:
            _client = docker.from_env()
            _client.ping()
        except DockerException as exc:
            raise RuntimeError(
                "Cannot connect to Docker daemon.  Is Docker running?\n"
                f"Detail: {exc}"
            ) from exc
    return _client


# ---------------------------------------------------------------------------
# In-memory container URL registry
# ---------------------------------------------------------------------------

# Maps project_id → container URL (e.g. "http://localhost:32789")
_container_urls: dict[str, str] = {}

# Maps project_id → (container_id, network_id) for cleanup
_container_ids: dict[str, tuple[str, str]] = {}


# ---------------------------------------------------------------------------
# Helper: resolve gateway IP
# ---------------------------------------------------------------------------

def _get_gateway_ip() -> str:
    """Resolve the Docker gateway IP (used for host.docker.internal)."""
    try:
        client = _get_client()
        bridge_net = client.networks.get("bridge")
        bridge_config = bridge_net.attrs.get("IPAM", {}).get("Config", [])
        if bridge_config:
            return bridge_config[0].get("Gateway", "")
    except Exception:
        pass
    return ""


def _collect_allowed_hosts() -> str:
    """Build a comma-separated list of host IPs the container should be
    allowed to reach (Ollama, MSF RPC, etc.).

    Reads from environment variables and auto-detects where possible.
    """
    hosts: set[str] = set()

    # Ollama host (LLM inference)
    ollama_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    # If Ollama is on localhost, the container needs the Docker gateway IP
    if "localhost" in ollama_url or "127.0.0.1" in ollama_url:
        gateway = _get_gateway_ip()
        if gateway:
            hosts.add(gateway)

    # MSF RPC runs locally inside the container (msfrpcd in entrypoint.sh),
    # so no external MSF host needs to be allowed.

    # Explicit additional hosts from env
    extra = os.getenv("DOCKER_ALLOWED_HOSTS", "")
    for h in extra.split(","):
        h = h.strip()
        if h:
            hosts.add(h)

    return ",".join(hosts)


# ---------------------------------------------------------------------------
# Container environment builder
# ---------------------------------------------------------------------------

def _build_agent_env(target_ip: str) -> dict[str, str]:
    """Build environment variables to pass to the agent container.

    Passes through agent-service configuration (LLM, MSF, RAG settings)
    and adds Docker-specific networking vars.
    """
    gateway_ip = _get_gateway_ip()

    # Rewrite LLM_BASE_URL for in-container access
    # If Ollama is on the Docker host, use host.docker.internal or gateway IP
    llm_base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    if "localhost" in llm_base_url or "127.0.0.1" in llm_base_url:
        # Replace with host.docker.internal (works on Docker Desktop)
        llm_base_url = llm_base_url.replace("localhost", "host.docker.internal")
        llm_base_url = llm_base_url.replace("127.0.0.1", "host.docker.internal")

    # MSF RPC runs inside the container (msfrpcd started by entrypoint.sh),
    # so the agent always connects to localhost regardless of the host setting.
    msf_rpc_host = "127.0.0.1"

    env = {
        # ── Networking restriction (used by entrypoint.sh) ──
        "TARGET_IP": target_ip,
        "ALLOWED_HOSTS": _collect_allowed_hosts(),
        "DOCKER_GATEWAY_IP": gateway_ip,

        # ── Agent service configuration ──
        "AGENT_HOST": "0.0.0.0",
        "AGENT_PORT": str(AGENT_CONTAINER_PORT),

        # ── LLM configuration ──
        "LLM_BASE_URL": llm_base_url,
        "LLM_MODEL_NAME": os.getenv("LLM_MODEL_NAME", "qwen3:8b"),
        "EMBEDDING_MODEL_NAME": os.getenv("EMBEDDING_MODEL_NAME", "bge-m3"),

        # ── MSF RPC configuration ──
        # MSF RPC — msfrpcd runs locally inside the container
        "MSF_RPC_HOST": msf_rpc_host,
        "MSF_RPC_PORT": os.getenv("MSF_RPC_PORT", "55552"),
        "MSF_RPC_USER": os.getenv("MSF_RPC_USER", "msf"),
        "MSF_RPC_PASS": os.getenv("MSF_RPC_PASS", "msf123"),
        "MSF_RPC_SSL": os.getenv("MSF_RPC_SSL", "false"),
        # LHOST for reverse payloads — should be this container's IP
        # (or the target-facing IP); passed through from host env if set.
        "MSF_LHOST": os.getenv("MSF_LHOST", ""),
        # WSL mode is irrelevant inside the container
        "MSF_WSL_MODE": "false",

        # ── RAG configuration ──
        "CHROMA_PERSIST_DIRECTORY": os.getenv(
            "CHROMA_PERSIST_DIRECTORY", "/opt/redteam/redteam_agent/chroma_db"
        ),
        "DOCS_SOURCE_DIRECTORY": os.getenv(
            "DOCS_SOURCE_DIRECTORY", "/opt/redteam/redteam_agent/lib"
        ),
    }

    # Remove empty values to avoid overriding defaults in the container
    return {k: v for k, v in env.items() if v}


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def _create_network(project_id: str):
    """Create a Docker bridge network for one agent container."""
    client = _get_client()
    network_name = f"{NETWORK_PREFIX}-{project_id[:12]}"

    # Clean up stale network with the same name
    try:
        stale = client.networks.get(network_name)
        stale.remove()
        logger.warning("Removed stale network %s", network_name)
    except NotFound:
        pass

    network = client.networks.create(
        name=network_name,
        driver="bridge",
        internal=False,  # False so iptables in the container can reach the target
        labels={"managed-by": "redteam-agent", "project-id": project_id},
    )
    logger.info("Created Docker network %s (%s)", network_name, network.short_id)
    return network


def _remove_network(network_id: str) -> None:
    """Remove a Docker network by ID, swallowing NotFound."""
    client = _get_client()
    try:
        net = client.networks.get(network_id)
        net.remove()
        logger.info("Removed Docker network %s", network_id)
    except NotFound:
        pass
    except APIError as exc:
        logger.warning("Failed to remove network %s: %s", network_id, exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_agent_container(project_id: str, target_ip: str) -> str:
    """Spin up an isolated Docker container running the full agent service.

    Parameters
    ----------
    project_id : str
        Unique project identifier (used for naming).
    target_ip : str
        Comma-separated target IP(s) / CIDR(s) the container may reach.

    Returns
    -------
    str
        The HTTP base URL to reach the agent service inside the container,
        e.g. ``http://localhost:32789``.
    """
    if not DOCKER_ENABLED:
        raise RuntimeError("Docker sandboxing is not enabled (DOCKER_SANDBOX_ENABLED=false)")

    client = _get_client()

    # Validate target IP(s)
    for part in target_ip.split(","):
        part = part.strip()
        try:
            ipaddress.ip_network(part, strict=False)
        except ValueError:
            if not re.match(r"^[\w.\-]+$", part):
                raise ValueError(f"Invalid target specifier: {part!r}")
            logger.warning("Target %r is not an IP/CIDR — passing as hostname", part)

    # Destroy any existing container for this project
    try:
        destroy_agent_container(project_id)
    except Exception:
        pass

    # 1. Create dedicated network
    network = _create_network(project_id)

    # 2. Naming
    container_name = f"{CONTAINER_PREFIX}-{project_id[:12]}"

    # 3. Build environment
    env = _build_agent_env(target_ip)

    # 4. Run the container with a published port
    container = client.containers.run(
        image=SANDBOX_IMAGE,
        name=container_name,
        hostname=container_name,
        detach=True,
        network=network.name,
        # Publish the agent API port to a random host port
        ports={f"{AGENT_CONTAINER_PORT}/tcp": None},
        # Capabilities needed for iptables inside the container
        cap_add=["NET_ADMIN", "NET_RAW"],
        # Extra host entry so host.docker.internal works on Linux too
        extra_hosts={"host.docker.internal": "host-gateway"},
        # Resource limits
        mem_limit=CONTAINER_MEM_LIMIT,
        cpu_quota=CONTAINER_CPU_QUOTA,
        cpu_period=CONTAINER_CPU_PERIOD,
        # Environment
        environment=env,
        # Labels for easy cleanup
        labels={
            "managed-by": "redteam-agent",
            "project-id": project_id,
        },
    )

    logger.info(
        "Created agent container %s (%s) on network %s — target=%s",
        container_name, container.short_id, network.name, target_ip,
    )

    # 5. Wait for the container to be ready and resolve the published port
    container.reload()  # refresh attrs to get port bindings
    port_bindings = container.attrs["NetworkSettings"]["Ports"]
    host_port_info = port_bindings.get(f"{AGENT_CONTAINER_PORT}/tcp")

    if not host_port_info:
        raise RuntimeError(
            f"Container {container_name} has no published port for {AGENT_CONTAINER_PORT}/tcp"
        )

    host_port = host_port_info[0]["HostPort"]
    container_url = f"http://localhost:{host_port}"

    # 6. Store in registry
    _container_urls[project_id] = container_url
    _container_ids[project_id] = (container.id, network.id)

    logger.info("Agent container %s reachable at %s", container_name, container_url)

    # 7. Wait for the agent API to become responsive
    _wait_for_agent(container_url, timeout=60)

    return container_url


def _wait_for_agent(url: str, timeout: int = 60) -> None:
    """Poll the agent service until it responds or timeout is reached."""
    import httpx

    deadline = time.time() + timeout
    last_exc = None
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{url}/status", timeout=5.0)
            # 404 is fine — means no run started yet but service is up
            if resp.status_code in (200, 404):
                logger.info("Agent service at %s is ready", url)
                return
        except Exception as exc:
            last_exc = exc
        time.sleep(2)

    logger.warning(
        "Agent service at %s did not become ready within %ds. Last error: %s",
        url, timeout, last_exc,
    )


def get_container_url(project_id: str) -> Optional[str]:
    """Return the HTTP base URL for the agent container of a project.

    Returns ``None`` if no container is running for the project.
    """
    return _container_urls.get(project_id)


def destroy_agent_container(project_id: str) -> None:
    """Forcefully stop and remove the agent container for a project.

    Safe to call even if the container has already been removed.
    """
    client = _get_client()

    container_name = f"{CONTAINER_PREFIX}-{project_id[:12]}"
    ids = _container_ids.pop(project_id, None)
    _container_urls.pop(project_id, None)

    # Remove container
    try:
        container = client.containers.get(container_name)
        container.stop(timeout=5)
        container.remove(force=True)
        logger.info("Destroyed agent container %s", container_name)
    except NotFound:
        logger.debug("Container %s already removed", container_name)
    except APIError as exc:
        logger.warning("Error removing container %s: %s", container_name, exc)

    # Remove network
    if ids:
        _remove_network(ids[1])
    else:
        # Try to find and remove network by naming convention
        network_name = f"{NETWORK_PREFIX}-{project_id[:12]}"
        try:
            net = client.networks.get(network_name)
            net.remove()
        except (NotFound, APIError):
            pass


def recover_containers() -> dict[str, str]:
    """Scan Docker for running agent containers and rebuild URL registry.

    Useful on backend startup to re-discover containers that survived
    a backend restart.

    Returns a dict mapping project_id → container_url.
    """
    if not DOCKER_ENABLED:
        return {}

    try:
        client = _get_client()
    except RuntimeError:
        return {}

    recovered: dict[str, str] = {}

    for ctr in client.containers.list(
        filters={"label": "managed-by=redteam-agent", "status": "running"}
    ):
        project_id = ctr.labels.get("project-id", "")
        if not project_id:
            continue

        # Resolve published port
        ctr.reload()
        port_bindings = ctr.attrs["NetworkSettings"]["Ports"]
        host_port_info = port_bindings.get(f"{AGENT_CONTAINER_PORT}/tcp")
        if not host_port_info:
            continue

        host_port = host_port_info[0]["HostPort"]
        url = f"http://localhost:{host_port}"

        _container_urls[project_id] = url
        # Find the network
        networks = ctr.attrs["NetworkSettings"]["Networks"]
        network_id = ""
        for net_name, net_info in networks.items():
            if net_name.startswith(NETWORK_PREFIX):
                network_id = net_info.get("NetworkID", "")
                break
        _container_ids[project_id] = (ctr.id, network_id)

        recovered[project_id] = url
        logger.info("Recovered agent container for project %s at %s", project_id, url)

    return recovered


def cleanup_stale_containers() -> int:
    """Remove all containers and networks labelled ``managed-by=redteam-agent``.

    Useful at backend startup to clean up leftover resources.
    Returns the number of resources removed.
    """
    if not DOCKER_ENABLED:
        return 0

    try:
        client = _get_client()
    except RuntimeError:
        return 0

    removed = 0

    # Containers
    for ctr in client.containers.list(
        all=True, filters={"label": "managed-by=redteam-agent"}
    ):
        try:
            ctr.stop(timeout=3)
            ctr.remove(force=True)
            removed += 1
            logger.info("Cleaned up stale container %s", ctr.name)
        except Exception as exc:
            logger.warning("Failed to clean up container %s: %s", ctr.name, exc)

    # Networks
    for net in client.networks.list(filters={"label": "managed-by=redteam-agent"}):
        try:
            net.remove()
            removed += 1
            logger.info("Cleaned up stale network %s", net.name)
        except Exception as exc:
            logger.warning("Failed to clean up network %s: %s", net.name, exc)

    # Clear in-memory registries
    _container_urls.clear()
    _container_ids.clear()

    return removed
