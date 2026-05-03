# Reference – AI RedTeam (Team S06)

## System Structure

| Component | Technology | Default Port | Role |
|-----------|------------|--------------|------|
| Frontend | React + Vite | 5173 | User interface for project management, scan control, and report viewing |
| Backend | FastAPI + Uvicorn | 8000 | REST API server; handles auth, projects, targets, scans, reports |
| Database | PostgreSQL 14 | 5432 | Persistent storage for all application data |
| Vector Store | ChromaDB | — | Embedding persistence for RAG document retrieval |
| LLM Service | Ollama | 11434 | Local inference endpoint for the AI agent |
| Metasploit RPC | msfrpcd | 55552 | Remote procedure interface for exploit module execution |

---

## Key APIs / Interfaces

All protected endpoints require the request header `X-User-Id: <UUID>`, obtained from `POST /users/auth`.

### Users

| Endpoint | Method | Request | Response | Status |
|----------|--------|---------|----------|--------|
| `/users/register` | POST | `UserCreate` (email: EmailStr, password: SecretStr ≥ 8 chars) | `UserInfo` (id, email, is_verified, created_at) | 201; 409 if email exists |
| `/users/auth` | POST | `UserAuth` (email, password) | `UserIdentity` (user_id: UUID) | 200; 401 on bad credentials |
| `/users/me` | GET | Header: `X-User-Id` | `UserInfo` | 200; 401 if not found |
| `/users/profile` | PATCH | Header: `X-User-Id` | `UserInfo` | Not implemented |

### Projects

| Endpoint | Method | Request | Response | Status |
|----------|--------|---------|----------|--------|
| `/projects` | GET | Header: `X-User-Id` | `list[ProjectSummary]` | 200 |
| `/projects` | POST | `ProjectCreate` (name, description optional) + Header | `ProjectSummary` | 201 |
| `/projects/{project_id}` | GET | Header: `X-User-Id` | `ProjectDetail` (includes target_ids, run_ids, report_ids) | 200; 404 if not owner |
| `/projects/{project_id}` | DELETE | Header: `X-User-Id` | 204 No Content | 204; 404 if not owner |

### Findings & Reports (Project-scoped)

| Endpoint | Method | Request | Response | Status |
|----------|--------|---------|----------|--------|
| `/projects/{project_id}/findings` | GET | Header: `X-User-Id` | `list[FindingResponse]` (id, finding_type, severity, title, content, evidence, confidence, run_id) | 200; 404 if not owner |
| `/projects/{project_id}/reports` | GET | Header: `X-User-Id` | `list[ReportResponse]` (id, title, summary, content, report_format, project_id, created_at) | 200; 404 if not owner |

### Targets

| Endpoint | Method | Request | Response | Status |
|----------|--------|---------|----------|--------|
| `/projects/{project_id}/targets` | GET | Header: `X-User-Id` | `list[TargetDetail]` | 200 |
| `/projects/{project_id}/targets` | POST | `TargetCreateRequest` (value, label optional, target_type optional) + Header | `TargetDetail` | 201; target_type auto-inferred from value if omitted |
| `/projects/{project_id}/targets/{target_id}` | GET | Header: `X-User-Id` | `TargetDetail` | 200; 404 if not owner |
| `/projects/{project_id}/targets/{target_id}` | PATCH | `TargetPatch` (value, label, target_type — all optional) + Header | `TargetDetail` | 200; 400 on empty payload |
| `/projects/{project_id}/targets/{target_id}` | DELETE | Header: `X-User-Id` | 204 No Content | 204; 404 if not owner |

**Target type inference rules** (applied when `target_type` is omitted):

| Pattern | Inferred Type |
|---------|---------------|
| Starts with `http://` or `https://` | `url` |
| Matches `d.d.d.d/n` | `cidr` |
| Matches `d.d.d.d` | `ip` |
| Anything else | `domain` |

### Scans

| Endpoint | Method | Request | Response | Status |
|----------|--------|---------|----------|--------|
| `/scans/start` | POST | `ScanStartRequest` (project_id: UUID, targets: list[str], scan_type: `"web"` or `"network"`) + Header | `ScanStartResponse` (run_id: str) | 201 |
| `/scans/{run_id}/status` | GET | Header: `X-User-Id` | `ScanStatusResponse` (status, logs: list[dict], pending_action optional, report_type, report_id optional) | 200; 404 if not found |
| `/scans/{run_id}/findings` | GET | Header: `X-User-Id` | `list[FindingResponse]` | 200 |
| `/scans/{run_id}/approve` | POST | Header: `X-User-Id` | `ActionResponse` (success: bool) | 200; 404 if not found |
| `/scans/{run_id}/deny` | POST | Header: `X-User-Id` | `ActionResponse` | 200; 404 if not found |
| `/scans/{run_id}/kill` | POST | Header: `X-User-Id` | `ActionResponse` | 200; 404 if not found |

### Reports

| Endpoint | Method | Request | Response | Status |
|----------|--------|---------|----------|--------|
| `/reports/{report_id}` | GET | Header: `X-User-Id` (report_id parsed as UUID) | `ReportResponse` (id, title, summary, content, report_format, project_id, created_at) | 200; 404 if not found |

---

## Configuration

### Database

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `DB_HOST` | str | required | PostgreSQL hostname | `backend/app/core/config.py` |
| `DB_PORT` | int | required | PostgreSQL port | `backend/app/core/config.py` |
| `DB_NAME` | str | required | Database name | `backend/app/core/config.py` |
| `DB_SCHEMA` | str | required | SQL schema name | `backend/app/core/config.py` |
| `DB_OWNER_USER` | str | required | Alembic / DDL user | `backend/app/core/config.py` |
| `DB_OWNER_PASSWORD` | str | required | Owner password | `backend/app/core/config.py` |
| `DB_RUNTIME_USER` | str | required | App runtime user (DML only) | `backend/app/core/config.py` |
| `DB_RUNTIME_PASSWORD` | str | required | Runtime password | `backend/app/core/config.py` |
| `DB_MIGRATE_USER` | str | required | Migration user | `backend/app/core/config.py` |
| `DB_MIGRATE_PASSWORD` | str | required | Migration password | `backend/app/core/config.py` |

### Frontend

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `VITE_API_BASE_URL` | str | `http://127.0.0.1:8000` | Backend API base URL | `frontend/web/.env.example` |

### RAG & LLM (Ollama / ChromaDB)

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `LLM_BASE_URL` | str | `http://localhost:11434` | Ollama API endpoint | `service/redteam_agent/config.py` |
| `LLM_MODEL_NAME` | str | `qwen3:8b` | Model name pulled from Ollama | `service/redteam_agent/config.py` |
| `EMBEDDING_MODEL_NAME` | str | `bge-m3` | Embedding model for RAG | `service/redteam_agent/config.py` |
| `CHROMA_PERSIST_DIRECTORY` | str | `service/redteam_agent/chroma_db` | ChromaDB persistence path | `service/redteam_agent/config.py` |
| `COLLECTION_NAME` | str | `example_collection` | ChromaDB collection name | `service/redteam_agent/config.py` |
| `DOCS_SOURCE_DIRECTORY` | str | `service/redteam_agent/lib` | Document ingest directory | `service/redteam_agent/config.py` |
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
| `MSF_RPC_SSL` | str (bool) | `false` | Use SSL for RPC connection | `service/redteam_agent/config.py` |
| `MSF_LHOST` | str | value of `MSF_RPC_HOST` | Reverse payload LHOST | `service/redteam_agent/config.py` |
| `MSF_WSL_MODE` | str (bool) | `false` | Enable WSL networking mode | `service/redteam_agent/config.py` |
| `MSF_WINDOWS_HOST_IP` | str | — | Windows host IP when running from WSL | `service/redteam_agent/config.py` |

### Engagement Scope

| Variable | Type | Default | Purpose | File |
|----------|------|---------|---------|------|
| `ALLOWED_TARGETS` | comma-separated str | `""` (empty = no restriction) | IP/CIDR whitelist for scan targets | `service/redteam_agent/config.py` |

---

## Database Schemas

All tables reside in the schema named by `DB_SCHEMA` (default `app`). Timestamps are `DateTime(tz=True)`. Primary keys are `UUID` with `server_default gen_random_uuid()`.

### app.users

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | |
| email | Text | UNIQUE, NOT NULL | |
| hashed_password | Text | NOT NULL | Argon2 hash |
| is_verified | Boolean | NOT NULL, server_default `false` | |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | |

**Relationships:** one-to-many → `projects`

---

### app.projects

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | |
| owner_id | UUID | FK → `app.users.id` ON DELETE CASCADE, NOT NULL | |
| name | String(255) | NOT NULL | |
| description | Text | Nullable | |
| project_status | Enum | NOT NULL, server_default `active` | Values: `active`, `archived` |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | |

**Relationships:** many-to-one → `users`; one-to-many → `targets`, `runs`, `reports`

---

### app.targets

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | |
| project_id | UUID | FK → `app.projects.id` ON DELETE CASCADE, NOT NULL | |
| target_type | Enum | NOT NULL | Values: `ip`, `cidr`, `domain`, `url` |
| value | Text | NOT NULL | |
| label | String(255) | Nullable | |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | |

**Relationships:** many-to-one → `projects`; one-to-many → `runs`

---

### app.runs

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | |
| project_id | UUID | FK → `app.projects.id` ON DELETE CASCADE, NOT NULL | |
| target_id | UUID | FK → `app.targets.id` ON DELETE SET NULL, Nullable | |
| run_type | Enum | Nullable | Values: `osint`, `scan`, `exploit`, `stress_test` |
| purpose | Enum | Nullable | Values: `primary`, `subtask`, `enrichment`, `retry`, `validation` |
| status | Enum | NOT NULL, server_default `queued` | Values: `queued`, `running`, `completed`, `failed` |
| tool_name | String(64) | Nullable | |
| tool_version | String(64) | Nullable | |
| raw_command | Text | NOT NULL | |
| output_format | Enum | Nullable | Values: `binary`, `file`, `text`, `json`, `xml`, `csv` |
| started_at | DateTime(tz) | Nullable | |
| finished_at | DateTime(tz) | Nullable | |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | |

**Relationships:** many-to-one → `projects`, `targets`; one-to-many → `findings`

---

### app.findings

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | |
| run_id | UUID | FK → `app.runs.id` ON DELETE CASCADE, NOT NULL | |
| finding_type | Enum | NOT NULL | Values: `vulnerability`, `misconfiguration`, `credential`, `information` |
| severity | Enum | NOT NULL | Values: `low`, `medium`, `high`, `critical` |
| title | String(255) | NOT NULL | |
| content | Text | NOT NULL | |
| evidence | Text | NOT NULL | |
| confidence | SmallInteger | NOT NULL | Range: 0–100 |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | |

**Relationships:** many-to-one → `runs`

---

### app.reports

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, server_default `gen_random_uuid()` | |
| project_id | UUID | FK → `app.projects.id` ON DELETE CASCADE, NOT NULL | |
| title | String(255) | NOT NULL | |
| summary | Text | Nullable | |
| content | Text | NOT NULL | |
| report_format | Enum | NOT NULL | Values: `pdf`, `html`, `json`, `markdown` |
| created_at | DateTime(tz) | NOT NULL, server_default `now()` | |

**Relationships:** many-to-one → `projects`

---

## LangGraph Agent

Defined in `service/redteam_agent/agent.py`. The agent is a compiled `StateGraph` using `InMemorySaver` for checkpointing.

### State Schema (`MessagesState`)

| Field | Type | Accumulation |
|-------|------|--------------|
| `messages` | `list[AnyMessage]` | Append-only (`operator.add`) |
| `llm_calls` | `int` | Overwrite |
| `current_phase` | `str` | Overwrite |
| `directive` | `str` | Overwrite |
| `findings` | `list[dict]` | Append-only (`operator.add`) |
| `last_tool_results` | `list[dict]` | Overwrite |
| `phase_history` | `list[str]` | Append-only (`operator.add`) |
| `rag_query` | `str` | Overwrite |
| `rag_reason` | `str` | Overwrite |
| `rag_caller` | `str` | Overwrite |

Valid values for `current_phase`: `recon`, `enumeration`, `exploitation`, `complete` (enforced in order; phase skipping is auto-corrected).

### Node Inventory

| Node Name | Handler | Primary Input | Primary Output |
|-----------|---------|---------------|----------------|
| `planner` | `planner_node` | `messages`, `current_phase` | `current_phase`, `directive`, `phase_history`; or RAG redirect |
| `tactician` | `tactician_node` | `messages` | `AIMessage` with `tool_calls`; or RAG redirect |
| `critic_node` | `critic_node` | `messages` | `HumanMessage` with criticism; or empty; or RAG prefetch |
| `risk_gate_node` | `risk_gate_node` | `messages` | `interrupt` on HIGH risk; `HumanMessage` on deny; or empty |
| `tool_node` | `tool_node` | `messages` | `list[ToolMessage]`, `last_tool_results` |
| `analyst_node` | `analyst_node` | `messages` | `findings`, `HumanMessage` analysis; or RAG redirect |
| `rag_node` | `RAGNode.__call__` | `rag_query`, `rag_reason`, `rag_caller` | `HumanMessage` with retrieved context; clears `rag_query`, `rag_reason` |

**Graph flow:**

```
START → planner → tactician → critic_node → risk_gate_node → tool_node → analyst_node → planner
```

Any thinking node (`planner`, `tactician`, `critic_node`, `analyst_node`) can detour to `rag_node` and return.

### Tools

Defined in `service/redteam_agent/tools.py`. Bound to the tactician model.

| Tool | Arguments | Return Type | Constraints |
|------|-----------|-------------|-------------|
| `execute_nmap_scan` | `command: str` | `str` | Command must start with `nmap`; 300 s subprocess timeout; output truncated at 3000 chars |
| `execute_msf_module` | `module_type: str`, `module_name: str`, `options: dict`, `payload: str` (default `""`) | `str` | Connects to MSF RPC; 120 s poll timeout; payload compatibility validated before execution |
| `search_msf_modules` | `keyword: str` | `str` | Results capped at 30 entries |

---

## Critic Pipeline

Defined in `service/redteam_agent/critic.py`. Executes three sequential validation stages on every proposed tool call before execution.

### Validation Stages

| Stage | Name | Methods | Checks | Pass Condition | Reject Action |
|-------|------|---------|--------|----------------|---------------|
| 1 | Schema Validation | `validate_nmap_schema`, `validate_msf_schema` | Command format, presence of target, valid module_type, valid RPORT range | No issues found | Return `HumanMessage` "CRITICISM DETECTED (schema validation)" to tactician |
| 2 | Scope Check | `assess_nmap_blocked`, `assess_msf_blocked` | Target IP/CIDR against `ALLOWED_TARGETS` whitelist | No blocked targets | Return `HumanMessage` "CRITICISM DETECTED (scope violation)" to tactician |
| 3 | LLM Review | `stage_llm_review` | Proposed command against RAG documentation context | Response line 1 matches `VALID` | Return `HumanMessage` "CRITICISM DETECTED" to tactician |

If `ALLOWED_TARGETS` is empty, Stage 2 passes unconditionally (no restriction enforced).

### Risk Classification

Evaluated by `risk_gate_node` after Stage 1–3 pass. HIGH-risk actions trigger a `langgraph.types.interrupt` requiring operator approval before execution.

| Tool | Condition | Risk Level |
|------|-----------|------------|
| `search_msf_modules` | Any | SAFE (exempt from risk gate) |
| `execute_nmap_scan` | `--script` with category `exploit`, `vuln`, `brute`, or `dos` | HIGH |
| `execute_nmap_scan` | `-T5` timing flag | HIGH |
| `execute_nmap_scan` | Full-port UDP scan (`-sU` with `-p-` or `1-65535`) | HIGH |
| `execute_nmap_scan` | Target CIDR prefix ≤ `/16` | HIGH |
| `execute_nmap_scan` | All other cases | MEDIUM |
| `execute_msf_module` | `module_type = "exploit"` | HIGH |
| `execute_msf_module` | `module_type = "auxiliary"` | MEDIUM |
