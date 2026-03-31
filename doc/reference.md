# Reference – AI RedTeam

## System Structure

AI RedTeam is a full-stack security assessment platform consisting of a React frontend (Vite), FastAPI backend, PostgreSQL database, ChromaDB vector store for RAG, and a local Ollama LLM service. The backend exposes RESTful endpoints for authentication, project management, target definition, scan orchestration, and report generation. All components communicate over HTTP/TCP on localhost in development; authentication is via `X-User-Id` header (transitioning to Clerk in production). The system does not transmit scan data or LLM inference to external services.

---

## Key APIs / Interfaces

### Users

| Endpoint | Method | Request | Response | Notes |
|----------|--------|---------|----------|-------|
| `/users/register` | POST | `UserCreate` (email: EmailStr, password: SecretStr min 8 chars) | `UserInfo` (id, email, is_verified, created_at) | Returns 201; 409 if email exists |
| `/users/auth` | POST | `UserAuth` (email, password) | `UserIdentity` (user_id: UUID) | Validates credentials; returns UUID for header |
| `/users/me` | GET | Header: `X-User-Id: <UUID>` | `UserInfo` | Current user profile |
| `/users/profile` | PATCH | Header: `X-User-Id: <UUID>` | `UserInfo` | Handler not yet wired (pass) |

### Projects

| Endpoint | Method | Request | Response | Notes |
|----------|--------|---------|----------|-------|
| `/projects` | GET | Header: `X-User-Id` | `list[ProjectSummary]` | Lists user's projects; filtered by owner |
| `/projects` | POST | `ProjectCreate` (name, description optional) + Header: `X-User-Id` | `ProjectSummary` | Returns 201; creates owned resource |
| `/projects/{project_id}` | GET | Header: `X-User-Id` | `ProjectDetail` (includes target_ids, run_ids, report_ids) | Full project view |
| `/projects/{project_id}` | DELETE | Header: `X-User-Id` | 204 No Content | Ownership-gated; cascades to targets, runs, reports |

### Findings & Reports (Project-scoped)

| Endpoint | Method | Request | Response | Notes |
|----------|--------|---------|----------|-------|
| `/projects/{project_id}/findings` | GET | Header: `X-User-Id` | `list[FindingResponse]` (id, finding_type, severity, title, content, evidence, confidence, run_id) | All findings across project runs |
| `/projects/{project_id}/reports` | GET | Header: `X-User-Id` | `list[ReportResponse]` (id, title, summary, content, report_format, project_id, created_at) | All reports for project |

### Targets

| Endpoint | Method | Request | Response | Notes |
|----------|--------|---------|----------|-------|
| `/projects/{project_id}/targets` | GET | Header: `X-User-Id` | `list[TargetDetail]` | Lists targets in project |
| `/projects/{project_id}/targets` | POST | `TargetCreateRequest` (value, label optional, target_type optional) + Header: `X-User-Id` | `TargetDetail` | Returns 201; auto-infers type (IP, CIDR, DOMAIN, URL) |
| `/projects/{project_id}/targets/{target_id}` | GET | Header: `X-User-Id` | `TargetDetail` | Single target view |
| `/projects/{project_id}/targets/{target_id}` | PATCH | `TargetPatch` (value, label, target_type optional) + Header: `X-User-Id` | `TargetDetail` | Update target |
| `/projects/{project_id}/targets/{target_id}` | DELETE | Header: `X-User-Id` | 204 No Content | Ownership-gated; soft-delete or cascade per model |

### Scans

| Endpoint | Method | Request | Response | Notes |
|----------|--------|---------|----------|-------|
| `/scans/start` | POST | `ScanStartRequest` (project_id: UUID, targets: list[str], scan_type: "web"\|"network") + Header: `X-User-Id` | `ScanStartResponse` (run_id: str) | Returns 201; enqueues async scan coroutine |
| `/scans/{run_id}/status` | GET | Header: `X-User-Id` | `ScanStatusResponse` (status, logs: list[dict], pending_action optional, report_type, report_id optional) | Polls for scan progress and HITL gate status |
| `/scans/{run_id}/findings` | GET | Header: `X-User-Id` | `list[FindingResponse]` | Findings from this specific run |
| `/scans/{run_id}/approve` | POST | Header: `X-User-Id` | `ActionResponse` (success: bool) | User approves high-impact action; fires `asyncio.Event` |
| `/scans/{run_id}/deny` | POST | Header: `X-User-Id` | `ActionResponse` | User denies action; skip or fail step |
| `/scans/{run_id}/kill` | POST | Header: `X-User-Id` | `ActionResponse` | Terminate running scan |

### Reports

| Endpoint | Method | Request | Response | Notes |
|----------|--------|---------|----------|-------|
| `/reports/{report_id}` | GET | Header: `X-User-Id` (report_id parsed as UUID) | `ReportResponse` (id, title, summary, content, report_format, project_id, created_at) | Single report; JSON export supported; PDF planned |

---

## Configuration

### Database

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `DB_HOST` | str | required | PostgreSQL hostname | `backend/app/core/config.py` |
| `DB_PORT` | int | required | PostgreSQL port | `backend/app/core/config.py` |
| `DB_NAME` | str | required | Database name (e.g., `airedteam`) | `backend/app/core/config.py` |
| `DB_SCHEMA` | str | required | SQL schema (e.g., `app`) | `backend/app/core/config.py` |
| `DB_OWNER_USER` | str | required | Alembic / DDL user | `backend/app/core/config.py` |
| `DB_OWNER_PASSWORD` | str | required | Owner password | `backend/app/core/config.py` |
| `DB_RUNTIME_USER` | str | required | App runtime user (DML only) | `backend/app/core/config.py` |
| `DB_RUNTIME_PASSWORD` | str | required | Runtime password | `backend/app/core/config.py` |
| `DB_MIGRATE_USER` | str | required | Migration user | `backend/app/core/config.py` |
| `DB_MIGRATE_PASSWORD` | str | required | Migration password | `backend/app/core/config.py` |

### Frontend

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `VITE_API_BASE_URL` | str | `http://127.0.0.1:8000` | Backend API base URL for frontend | `frontend/web/.env.example` |

### RAG & LLM (Ollama / ChromaDB)

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `LLM_BASE_URL` | str | `http://localhost:11434` | Ollama API endpoint | `service/redteam_agent/config.py` |
| `LLM_MODEL_NAME` | str | `qwen3:8b` | Model name pulled from Ollama | `service/redteam_agent/config.py` |
| `EMBEDDING_MODEL_NAME` | str | `bge-m3` | Embedding model for RAG | `service/redteam_agent/config.py` |
| `CHROMA_PERSIST_DIRECTORY` | str | `service/redteam_agent/chroma_db` | ChromaDB persistence path | `service/redteam_agent/config.py` |
| `COLLECTION_NAME` | str | `example_collection` | ChromaDB collection name | `service/redteam_agent/config.py` |
| `DOCS_SOURCE_DIRECTORY` | str | `service/redteam_agent/lib` | Document ingest directory for RAG | `service/redteam_agent/config.py` |
| `CHUNK_SIZE` | int | `1000` | RAG document chunk size | `service/redteam_agent/config.py` |
| `CHUNK_OVERLAP` | int | `200` | RAG chunk overlap | `service/redteam_agent/config.py` |
| `RETRIEVER_K` | int | `5` | Number of similar docs to retrieve | `service/redteam_agent/config.py` |
| `LANGSMITH_TRACING` | str | `false` | Enable LangSmith observability | `service/redteam_agent/config.py` |

### Metasploit (MSF RPC)

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `MSF_RPC_HOST` | str | `172.31.191.206` | Metasploit RPC server host | `service/redteam_agent/config.py` |
| `MSF_RPC_PORT` | int | `55552` | Metasploit RPC port | `service/redteam_agent/config.py` |
| `MSF_RPC_USER` | str | `msf` | RPC authentication user | `service/redteam_agent/config.py` |
| `MSF_RPC_PASS` | str | `msf123` | RPC authentication password | `service/redteam_agent/config.py` |
| `MSF_RPC_SSL` | str (bool) | `false` | Use SSL for RPC | `service/redteam_agent/config.py` |
| `MSF_LHOST` | str | (uses MSF_RPC_HOST) | Reverse payload LHOST | `service/redteam_agent/config.py` |
| `MSF_WSL_MODE` | str (bool) | `false` | Enable WSL networking mode | `service/redteam_agent/config.py` |
| `MSF_WINDOWS_HOST_IP` | str | None | Windows host IP when running from WSL | `service/redteam_agent/config.py` |

### Engagement Scope

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `ALLOWED_TARGETS` | comma-separated str | empty string | IP/CIDR whitelist; empty = no restriction | `service/redteam_agent/config.py` |

---

## Database Schemas

All tables reside in the `app` schema (configurable via `DB_SCHEMA`). Timestamps use `DateTime(tz=True)` (timezone-aware). UUIDs are `server_default gen_random_uuid()`.

### app.users

| Column | Type | Constraints | Notes |
|--------|------|-----------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | User identifier |
| email | Text | UNIQUE, NOT NULL | Email address |
| hashed_password | Text | NOT NULL | Argon2 hash (argon2-cffi) |
| is_verified | Boolean | NOT NULL, server_default False | Email verification flag |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | Account creation timestamp |

**Relationships:** One-to-many with `projects` (owner)

---

### app.projects

| Column | Type | Constraints | Notes |
|--------|------|-----------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | Project identifier |
| owner_id | UUID | FK → app.users.id, ON DELETE CASCADE, NOT NULL | Project owner |
| name | String(255) | NOT NULL | Project name |
| description | Text | Nullable | Optional description |
| project_status | Enum | NOT NULL, server_default `ACTIVE` | Status: ACTIVE, ARCHIVED, DELETED |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | Project creation timestamp |

**Relationships:** Many-to-one with `users` (owner); one-to-many with `targets`, `runs`, `reports`

---

### app.targets

| Column | Type | Constraints | Notes |
|--------|------|-----------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | Target identifier |
| project_id | UUID | FK → app.projects.id, ON DELETE CASCADE, NOT NULL | Parent project |
| target_type | Enum | NOT NULL | Type: IP, CIDR, DOMAIN, URL (auto-inferred on creation) |
| value | Text | NOT NULL | IP, CIDR block, domain, or URL string |
| label | String(255) | Nullable | Human-readable label |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | Creation timestamp |

**Relationships:** Many-to-one with `projects`; one-to-many with `runs`

---

### app.runs

| Column | Type | Constraints | Notes |
|--------|------|-----------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | Run identifier |
| project_id | UUID | FK → app.projects.id, ON DELETE CASCADE, NOT NULL | Parent project |
| target_id | UUID | FK → app.targets.id, ON DELETE SET NULL, Nullable | Associated target |
| run_type | Enum | Nullable | Type: ACTIVE, PASSIVE (planned) |
| purpose | Enum | Nullable | Purpose: RECONNAISSANCE, EXPLOITATION, etc. |
| status | Enum | NOT NULL, server_default `QUEUED` | Status: QUEUED, RUNNING, COMPLETED, FAILED |
| tool_name | String(64) | Nullable | Tool used (e.g., nmap, nikto) |
| tool_version | String(64) | Nullable | Tool version |
| raw_command | Text | NOT NULL | Full command executed |
| output_format | Enum | Nullable | Output format: JSON, TEXT, etc. |
| started_at | DateTime(tz) | Nullable | Scan start time |
| finished_at | DateTime(tz) | Nullable | Scan end time |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | Record creation timestamp |

**Relationships:** Many-to-one with `projects`, `targets`; one-to-many with `findings`

---

### app.findings

| Column | Type | Constraints | Notes |
|--------|------|-----------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | Finding identifier |
| run_id | UUID | FK → app.runs.id, ON DELETE CASCADE, NOT NULL | Source run |
| finding_type | Enum | NOT NULL | Type: VULNERABILITY, MISCONFIGURATION, INFO, etc. |
| severity | Enum | NOT NULL | Severity: CRITICAL, HIGH, MEDIUM, LOW, INFO |
| title | String(255) | NOT NULL | Short title |
| content | Text | NOT NULL | Detailed description |
| evidence | Text | NOT NULL | Raw proof (command output, screenshot ref, etc.) |
| confidence | SmallInteger | NOT NULL | Confidence 0–100 (int, not float) |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | Creation timestamp |

**Relationships:** Many-to-one with `runs`

---

### app.reports

| Column | Type | Constraints | Notes |
|--------|------|-----------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | Report identifier |
| project_id | UUID | FK → app.projects.id, ON DELETE CASCADE, NOT NULL | Parent project |
| title | String(255) | NOT NULL | Report title |
| summary | Text | Nullable | Executive summary |
| content | Text | NOT NULL | Full report body |
| report_format | Enum | NOT NULL | Format: JSON, PDF (PDF not yet implemented) |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | Generation timestamp |

**Relationships:** Many-to-one with `projects`

---

## Future: LangGraph Integration

The `service/redteam_agent/` directory contains a standalone LangGraph agent (graph nodes, routing, RAG pipeline, critic validation, tool bindings) that is not yet wired to the FastAPI backend. Integration is planned; the drop-in point is documented in `backend/app/services/scan_engine.py` around line 147.