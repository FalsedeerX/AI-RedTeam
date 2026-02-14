# Database Schema (app)

## Tables

### users
- id: UUID (PK)
- email: text (unique)
- hashed_password: text
- is_verified: boolean
- created_at: timestamptz

### projects
- id: UUID (PK)
- created_at: timestamptz
- project_status: project_status_enum
- name: varchar(255)
- description: text
- owner_id → users.id

### targets
- id: UUID (PK)
- created_at: timestamptz
- target_type: target_type_enum
- label: varchar(255)
- value: text
- project_id → projects.id

### runs
- id: UUID (PK)
- created_at: timestamptz
- run_type: run_type_enum
- purpose: run_purpose_enum
- status: run_status_enum
- tool_name: varchar(64)
- tool_version: varchar(64)
- raw_command: text
- started_at: timestamptz
- finished_at: timestamptz
- output_format: run_output_format_enum
- project_id → projects.id
- target_id → targets.id

### findings
- id: UUID (PK)
- created_at: timestamptz
- finding_type: finding_type_enum
- severity: finding_severity_enum
- title: varchar(255)
- content: text
- evidence: text
- confidence: smallint
- run_id → runs.id

### reports
- id: UUID (PK)
- created_at: timestamptz
- title: varchar(255)
- summary: text
- content: text
- report_format: report_format_enum
- run_id → runs.id

---

## Enum Types (Python ↔ Database)

### FindingType → finding_type_enum
| Python Key | DB Value |
|-----------|----------|
| VULNERABILITY | `vulnerability` |
| MISCONFIGURATION | `misconfiguration` |
| CREDENTIAL | `credential` |
| INFORMATION | `information` |

### FindingSeverity → finding_severity_enum
| Python Key | DB Value |
|-----------|----------|
| LOW | `low` |
| MEDIUM | `medium` |
| HIGH | `high` |
| CRITICAL | `critical` |

### ProjectStatus → project_status_enum
| Python Key | DB Value |
|-----------|----------|
| ACTIVE | `active` |
| ARCHIVED | `archived` |

### ReportFormat → report_format_enum
| Python Key | DB Value |
|-----------|----------|
| PDF | `pdf` |
| HTML | `html` |
| JSON | `json` |
| MARKDOWN | `markdown` |

### RunType → run_type_enum
| Python Key | DB Value |
|-----------|----------|
| OSINT | `osint` |
| SCAN | `scan` |
| EXPLOIT | `exploit` |
| STRESS_TEST | `stress_test` |

### RunPurpose → run_purpose_enum
| Python Key | DB Value |
|-----------|----------|
| PRIMARY | `primary` |
| SUBTASK | `subtask` |
| ENRICHMENT | `enrichment` |
| RETRY | `retry` |
| VALIDATION | `validation` |

### RunStatus → run_status_enum
| Python Key | DB Value |
|-----------|----------|
| QUEUED | `queued` |
| RUNNING | `running` |
| COMPLETED | `completed` |
| FAILED | `failed` |

### RunOutputFormat → run_output_format_enum
| Python Key | DB Value |
|-----------|----------|
| BINARY | `binary` |
| FILE | `file` |
| TEXT | `text` |
| JSON | `json` |
| XML | `xml` |
| CSV | `csv` |

### TargetType → target_type_enum
| Python Key | DB Value |
|-----------|----------|
| IP | `ip` |
| CIDR | `cidr` |
| DOMAIN | `domain` |
| URL | `url` |

