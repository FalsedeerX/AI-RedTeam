from dataclasses import dataclass


@dataclass
class AgentProfile:
    beacon: BeaconProfile
    heartbeat: HeartbeatProfile
    envelope: EnvelopeProfile
    tasks: TasksProfile


@dataclass
class BeaconProfile:
    url: str
    timeout_sec: int
    max_retries: int
    retry_base_sec: int
    retry_jitter_percent: int
    max_backoff_sec: int


@dataclass
class HeartbeatProfile:
    interval: int
    jitter_percent: int
    workdays: list[int]
    workhours: list[int]


@dataclass
class EnvelopeProfile:
    encryption: dict[str, dict]
    enabled_encryption: list[str]
    enabled_compression: list[str]
    default_encryption: str | None
    default_compression: str | None


@dataclass
class TasksProfile:
    auto_load: bool
    enabled: list[str]


if __name__ == "__main__":
    pass
