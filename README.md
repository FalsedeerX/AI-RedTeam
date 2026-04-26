# AI RedTeam

> **AI-Driven Red Team Simulation Platform for Cybersecurity**  
Senior Design Project – ECE 49595SD (Software Track) – Purdue University  
Team S06 – Fall 2025 - Spring 2026

---

## Key Features
- Autonomous security auditing and remediation via LLM-generated commands  
- Custom implant with C2 infrastructure for remote execution and control  
- RAG-driven command generation for context-aware decision making  

---

## Contributors
- **Si Ci Chou (Simon)** – chou170@purdue.edu  
- **Yu-Kuang Chen (Falsedeer)** - chen5292@purdue.edu
- **Apostolos Cavounis (Paul)** - acavouni@purdue.edu

---

![Build Status](https://img.shields.io/badge/build-developing-brightgreen)
![License](https://img.shields.io/badge/license-apache-blue)
![Contributors](https://img.shields.io/badge/contributors-3-orange)

---

## Project Structure

```
AI-RedTeam/
├── backend/                        # FastAPI backend (port 8000)
│   ├── backend.py                  # App entrypoint — registers all routers
│   ├── requirements.txt            # Python dependencies
│   ├── alembic/                    # Database migration scripts
│   ├── app/
│   │   ├── api/routes/             # HTTP route handlers (users, projects, targets, scans)
│   │   ├── db/                     # SQLAlchemy models and brokers (CRUD layer)
│   │   ├── domain/                 # Enums and domain types
│   │   ├── schema/                 # Pydantic request/response schemas
│   │   ├── services/               # scan_engine.py — AI agent drop-in point
│   │   └── core/                   # Config, security (argon2 hashing)
│   └── README.md                   # Database schema reference
├── frontend/
│   └── web/                        # React + Vite frontend (port 5173)
│       └── src/
│           ├── lib/api.js          # Shared fetch helpers + X-User-Id injection
│           └── pages/              # EmailEntry, TermsModal, ProjectScopeManager, Dashboard, ReportView
├── scripts/
│   ├── dotenv_template             # Template for .env file
│   └── database_setup/            # init.sql + setup.sh for Postgres bootstrap
├── service/                        # LangChain/RAG AI service (standalone)
├── test/                           # Legacy Flask demo tests
└── docs/                           # Project documentation and assignment files
```

---

## Prerequisites

- Python 3.11
- Node.js 18+
- PostgreSQL 14 (macOS: `brew install postgresql@14`)

---

## One-Time Setup

### 1. Create the Python virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Configure environment variables

```bash
cp scripts/dotenv_template .env
```

Open `.env` and fill in the two blank password fields:
```
DB_RUNTIME_PASSWORD=<choose a password>
DB_MIGRATE_PASSWORD=<choose a password>
```

The other values (`DB_PORT`, `DB_HOST`, `DB_NAME`, etc.) are pre-filled for a standard local Postgres setup.

### 3. Bootstrap the database

Start Postgres, then run the database setup script. On macOS with Homebrew:

```bash
brew services start postgresql@14

source .env && psql postgres \
  -v db_name="$DB_NAME" \
  -v db_schema="$DB_SCHEMA" \
  -v db_owner_user="$DB_OWNER_USER" \
  -v db_owner_password="$DB_OWNER_PASSWORD" \
  -v db_runtime_user="$DB_RUNTIME_USER" \
  -v db_runtime_password="$DB_RUNTIME_PASSWORD" \
  -v db_migrate_user="$DB_MIGRATE_USER" \
  -v db_migrate_password="$DB_MIGRATE_PASSWORD" \
  -f scripts/database_setup/init.sql
```

On Linux, use `sudo -u postgres psql` instead and run from `scripts/database_setup/` using `bash setup.sh`.

### 4. Run database migrations

```bash
cd backend
alembic upgrade head
cd ..
```

### 5. Install frontend dependencies

```bash
cd frontend/web
npm install
cd ../..
```

---

## Running the Application

Open two terminal windows from the project root.

**Terminal 1 — Backend**
```bash
source venv/bin/activate
python backend/backend.py
```
Backend runs at `http://127.0.0.1:8000`  
Interactive API docs (Swagger UI): `http://127.0.0.1:8000/docs`

**Terminal 2 — Frontend**
```bash
cd frontend
npm run dev
```
Frontend runs at `http://localhost:5173`

### Clerk configuration

Authentication is powered by [Clerk](https://dashboard.clerk.com). Before
first run, set the following values in your `.env` (backend) and
`frontend/.env` (Vite):

Backend (`.env`):
```
CLERK_ISSUER=https://<your-slug>.clerk.accounts.dev
CLERK_JWKS_URL=https://<your-slug>.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=            # optional; only if you configured a custom JWT aud
AUTH_DEV_BYPASS=0          # set to 1 *only* for local-only dev before Clerk is wired
```

Frontend (`frontend/.env`):
```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

> **Dev cutover**: the migration removes `users.hashed_password`. Before
> running `alembic upgrade head` the first time after pulling this change,
> wipe any legacy accounts with `TRUNCATE app.users CASCADE;` in psql,
> otherwise the NOT-NULL drop will fail.

> On every subsequent session you only need to activate the venv and start both servers. If Postgres was stopped (e.g. after a reboot), run `brew services start postgresql@14` first.

---

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users/me` | Hydrate the local DB row for the current Clerk session |
| GET | `/projects` | List all projects for current user |
| POST | `/projects` | Create a new project |
| GET | `/projects/{id}` | Get project detail |
| DELETE | `/projects/{id}` | Delete a project |
| GET | `/projects/{id}/targets` | List targets for a project |
| POST | `/projects/{id}/targets` | Add a target (type auto-inferred from value) |
| DELETE | `/projects/{id}/targets/{tid}` | Remove a target |
| POST | `/scans/start` | Start a scan — returns `run_id` |
| GET | `/scans/{run_id}/status` | Poll scan status and logs |
| POST | `/scans/{run_id}/approve` | Approve a pending HITL action |
| POST | `/scans/{run_id}/deny` | Deny a pending HITL action |
| POST | `/scans/{run_id}/kill` | Emergency stop |
| POST | `/agent/start` | Start an agent run |
| GET | `/agent/{run_id}/status` | Poll agent status / HITL / findings |
| POST | `/agent/{run_id}/approve` · `/deny` · `/kill` | Agent HITL control |
| GET | `/reports/{id}` | Fetch a persisted report |

Every protected route expects an `Authorization: Bearer <clerk-jwt>` header.
The frontend's `lib/api.js` attaches this automatically via Clerk's
`useAuth().getToken()` hook, so app code just calls `apiGet` / `apiPost` /
`apiDelete` as before.  Registration, sign-in, and password flows now live
entirely inside Clerk's hosted `<SignIn>` / `<SignUp>` components.

---

## Notes

- The backend must be running before the frontend is opened
- The AI scan engine (`backend/app/services/scan_engine.py`) currently runs a simulated scan. Replace the body of `run_agent()` with the real LangChain agent when it is ready
- Database schema reference: `backend/README.md`
