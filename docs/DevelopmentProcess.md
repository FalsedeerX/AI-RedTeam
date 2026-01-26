# Development Process

## Repository Architecture

```plaintext
.
├── backend
│   ├── alembic
│   ├── alembic.ini
│   ├── app
│   ├── backend.py
│   └── requirements.txt
├── docs
│   ├── AIRedTeam_Software-Development-Plan.pdf
│   ├── DevelopmentProcess.md
│   ├── structure.md
│   └── Verification and Validation - Team 6.pdf
├── frontend
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── src
│   ├── public
│   ├── README.md
│   └── vite.config.js
├── scripts
│   ├── RAG
│   └── setup
├── backup
│   └── frontend
├── README.md
└── template_dotenv
```

### Structure Description

* **backend**: This folder contains all our server-side code and database migration files.
* **frontend**: This is for our client-side application built with Vite (React + Vite)
* **docs**: We put all our project documents and assignment files here as required.
* **scripts**: These are helper scripts for us to set up the environment or run RAG.
* **template_dotenv**: A template file for our environment variables so everyone can set up their config easily.

Our structure follows the common standard for modern full-stack web applications, separating the logic of frontend and backend to make development easier.

### References/Standards

**Gitflow Workflow**:

https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow

## Branching / Workflow Model

We use a simplified version of the Gitflow model, omitting release and hotfix branches due to the scale of the project. Once we have stable releases, then we may reevaluate the model and add release branch functionality.

### Branch Naming and Purpose

Branch names use lowercase letters with descriptive names separated by underscores where needed.

* `main`: This is the stable origin branch that always has code that works. We only merge into it when we finish an updated version.
* `develop`: The branch where we do all development work on this project. Once we finish a version and the whole system is tested completely, push to main as a new version.
* `feature/<description>`: Temporary branches that are used to develop new features. These features are merged to the develop branch, and when properly tested, squash the feature branch into one commit and delete the feature branch.
* `fix/<description>`: Temporary branches that are used for fixing bugs in develop branch.

### Commits Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commits Type Categories

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(rag): establish RAG system` |
| `fix` | Bug fix | `fix(rag): handle RAG workflow timeout` |
| `docs` | Documentation update | `docs(DevelopmentProcess): update DevelopmentProcess.md` |
| `test` | Test-related | `test(rag): add RAG unit tests` |
| `ci` | CI/CD changes | `ci(actions): add CI job` |

## Code Development & Review Policy

To make sure our code is properly  and doesn't break the project, we follow these rules:

1. **Pull Requests (PR)**: We never push directly to main or develop. Everyone must open a PR to merge their work.
2. **Code Review**: At least one other teammate must look at the PR and approve it before merging. We check for bugs and see if the code follows our style.
3. **CI Checks**: Our GitHub Actions will run tests and lint checks automatically. If these checks fail, the PR cannot be merged.
4. **Frequency**: We plan to merge our PRs regularly, at least once or twice a week, so we don't have too many merge conflicts at the end.
5. **Conflict Resolution**: If there is a merge conflict, the person responsible for the feature must fix it. We do not allow force pushing to shared branches.
