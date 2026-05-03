import requests
from typing import Any
from pathlib import Path
from express.core.identity import get_fingerprint
from express.core.config import load_configuration
from express.core.tasks.registry import TaskRegistry
from express.core import AGENT_VERSION, PROTOCOL_VERSION
from express.core.runtime import AgentContext, BootstrapContext
from express.core.tasks.loader import load_all_tasks, load_tasks
from express.core.envelope import EnvelopeRuntime, EnvelopPipeline
from express.core.protocol.messages.session import SessionRequestMessage
from express.core.envelope.transforms import load_compressions, load_encryptions
from .profile import (
    BeaconProfile,
    HeartbeatProfile,
    EnvelopeProfile,
    TasksProfile,
    AgentProfile,
)


def load_profile(config: dict[str, Any]) -> AgentProfile:
    # initialze the BeaconProfile
    beacon_cfg = config["BEACON"]
    beacon_profile = BeaconProfile(**beacon_cfg)

    # initailze the HeartbeatProfile
    heartbeat_cfg = config["HEARTBEAT"]
    heartbeat_profile = HeartbeatProfile(**heartbeat_cfg)

    # initialize the EnvelopeProfile
    envelope_cfg = config["ENVELOPE"]
    envelope_profile = EnvelopeProfile(**envelope_cfg)

    # initialize the TasksProfile
    tasks_cfg = config["TASKS"]
    tasks_profile = TasksProfile(**tasks_cfg)

    return AgentProfile(
        beacon=beacon_profile,
        heartbeat=heartbeat_profile,
        envelope=envelope_profile,
        tasks=tasks_profile,
    )


def create_runtime(profile: AgentProfile) -> EnvelopeRuntime:
    # load the enabled encryption and compression module
    return EnvelopeRuntime(
        encryption=load_encryptions(profile.envelope.enabled_encryption),
        compression=load_compressions(profile.envelope.enabled_compression),
    )


def create_bootstrap_context(config_path: Path) -> BootstrapContext:
    config = load_configuration(config_path)
    profile = load_profile(config)
    runtime = create_runtime(profile)

    # load enabled task modules
    if profile.tasks.auto_load:
        load_all_tasks()
    else:
        load_tasks(profile.tasks.enabled)

    return BootstrapContext(
        agent_version=AGENT_VERSION,
        protocol_version=PROTOCOL_VERSION,
        profile=profile,
        envelope_runtime=runtime,
        task_registry=TaskRegistry,
    )


def bootstrap(ctx: BootstrapContext) -> AgentContext:
    pipeline = EnvelopPipeline(ctx)
    beacon_cfg = ctx.profile.beacon

    # create session request message and send to server
    session_req = SessionRequestMessage(
        agent_version=ctx.agent_version,
        protocol_capabilities=ctx.envelope_runtime.list_capabilities(),
        task_capabilities=ctx.task_registry.list_capabilities(),
        extensions={"fingerprint": get_fingerprint()},
    )

    # debug session request message
    session_request = pipeline.wrap(session_req)
    print(session_request.decode('utf-8'))

    # send request to server
    #response = requests.post(
    #    beacon_cfg.url,
    #    data=pipeline.wrap(session_req),
    #    headers={"Content-Type": "application/octet-stream"},
    #)
    #print(response.content)


if __name__ == "__main__":
    pass
