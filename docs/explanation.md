# Explanation — AI RedTeam

---

## System Overview

AI RedTeam is an automated, LLM-powered penetration testing framework designed to lower the barrier for security assessments. The platform enables users to define scan targets (IPs or URLs) and deploy autonomous agents that execute reconnaissance and vulnerability discovery.

A core pillar of our design is the Human-in-the-Loop (HITL) mechanism. Unlike fully autonomous tools that might cause unintended service disruptions, our system pauses for operator approval before executing high-risk actions. To ensure data privacy -- a critical requirement for security work -- the entire stack runs locally, utilizing Ollama for LLM inference to prevent sensitive findings from leaving the local environment.

---

## Architecture Diagrams

### High-Level Architecture

The following diagram illustrates the interaction between our React frontend, the FastAPI backend, and the specialized AI Agent service.

```
[ User Interface ] <--- REST API ---> [ FastAPI Backend ] <--- Async ---> [ PostgreSQL ]
                                              |
                                              v
                                      [ LangGraph Agent ] <--- Local API ---> [ Ollama LLM ]
                                              |
                                              v
                                      [ Security Tools ] (nmap, Metasploit, etc.)
```

### AI Agent Internal Flow

The AI agent has its own internal graph structure. This is the flow of how the agent makes decisions:

![AI RedTeam Architecture] (./agent_graph_planner.png)

---

## Key Components

### 1. Backend: FastAPI & PostgreSQL

The backend serves as the central nervous system, managing the lifecycle of security "runs." We use SQLAlchemy for ORM and Alembic for migrations to maintain a version-controlled database schema. The system employs a 3-role security model (Owner, Migrate, Runtime) to enforce the principle of least privilege at the database level.


### 2. AI Intelligence: LangGraph & Ollama

Instead of a simple chatbot, our agent is a directed graph built with LangGraph. This allows for iterative reasoning; if a tool fails, the agent can "loop back" to the Tactician to refine its approach. By using Ollama (qwen3:8b), we maintain complete sovereignty over the scan data.

### 3. RAG Pipeline: ChromaDB

To improve tool accuracy, we implemented a Retrieval-Augmented Generation (RAG) pipeline using ChromaDB. When the agent is unsure how to use a specific Metasploit module, it queries a vector store containing official documentation, ensuring the generated commands are syntactically correct.

---

## Design Decisions

### Why Local LLM (Ollama) over Cloud APIs?

Security practitioners are rightfully hesitant to send vulnerability data to third-party providers. We chose Ollama because it provides a RESTful API for local inference, satisfying our privacy requirements while still delivering sufficient reasoning capabilities for command generation.

### Choosing LangGraph for Agentic Control

Standard LLM chains often struggle with complex, multi-step tasks like penetration testing. We selected LangGraph because it treats the "thinking process" as a state machine, allowing us to implement the Critic and Risk Gate nodes as mandatory checkpoints before any tool execution.

### Containerization with Docker

To ensure consistent environments across different operating systems, we containerized the database and backend services. This simplifies the setup process for new developers and ensures that dependencies like PostgreSQL and ChromaDB are configured identically every time.

---

## Tradeoffs and Limitations

### Authentication in Transition

The project is currently transitioning to a production-grade identity provider. While Clerk is being integrated for overall account management, I have maintained a temporary X-User-Id header with a UUID for the current API implementation. This allows us to verify backend logic and Scan Engine stability independently before the final integration.

### Resource Intensity

Running both a local LLM and an active security scan is hardware-intensive. Users on machines without dedicated GPUs may experience latency in the agent's decision-making process.

### Agent/Backend Integration

The agent currently operates as a semi-autonomous service. Full seamless integration is still being refined.