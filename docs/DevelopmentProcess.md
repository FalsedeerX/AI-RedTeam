# Devlopment Process

---

## Repository Architecture

```text
.
├── backend
│   ├── alembic
│   ├── alembic.ini
│   ├── app
│   ├── backend.py
│   └── requirements.txt
├── backup
│   └── frontend
├── docs
│   ├── AIRedTeam_Software-Development-Plan.pdf
│   ├── DevelopmentProcess.md
│   ├── structure.md
│   └── Verification and Validation - Team 6.pdf
├── frontend
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── public
│   ├── README.md
│   ├── src
│   └── vite.config.js
├── README.md
├── scripts
│   ├── RAG
│   └── setup
└── template_dotenv
```

Structure Explanation:
1. **backend** - For backend codebase.
2. **frontend** - For frontend codebase.
3. **scripts** - For helper scripts for installation or environment setup.
4. **backup** - A temporary folder for storing previous version upon changes.
5. **template_dotenv** - Template of the global configuration file for the whole project.

---

## Branching / Workflow Model

We are planning to do it in GitHub flow, making the `main` branch be always stable and deployable among version changes, additional branches will be dedicated to local development and testing. The naming convention of all branches will follw **snake case** naming convention.

## Code Devlopment & Review Policy

We will address all pull requests and merging at the end of each week to reduce the chances of merge conflicts. When a merge conflict encounters, only allows merging into `main` branch when you are sure it won't break anything, making `main` branch always remain stable and usable. During conflict resolving, it is not allowed to perform a push force.
