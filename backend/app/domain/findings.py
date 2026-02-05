from enum import StrEnum


class FindingType(StrEnum):
    VULNERABILITY = "vulnerability"
    MISCONFIGURATION = "misconfiguration"
    CREDENTIAL = "credential"
    INFORMATION = "information"


class FindingSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"



if __name__ == "__main__":
    pass
