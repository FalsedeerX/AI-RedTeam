from enum import StrEnum


class RunType(StrEnum):
    OSINT = "osint"
    SCAN = "scan"
    EXPLOIT = "exploit"
    STRESS_TEST = "stress_test"


class RunPurpose(StrEnum):
    PRIMARY = "primary"
    SUBTASK = "subtask"
    ENRICHMENT = "enrichment"
    RETRY = "retry"
    VALIDATION = "validation"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunOutputFormat(StrEnum):
    BINARY = "binary"
    FILE = "file"
    TEXT = "text"
    JSON = "json"
    XML = "xml"
    CSV = "csv"



if __name__ == "__main__":
    pass

