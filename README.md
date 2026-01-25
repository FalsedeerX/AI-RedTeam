# AI RedTeam

> **AI-Driven Red Team Simulation Platform for Cybersecurity**  
Senior Design Project – ECE 49595SD (Software Track) – Purdue University  
Team S06 – Fall 2025 - Spring 2026

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

## Setup & Installation

### 1. Create and Activate Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install Flask flask-cors
```

---

## Running the Application

### Step 1: Start the Backend Server

```bash
python backend/backend.py
```

The backend will run on `http://127.0.0.1:5000`

### Step 2: Start the Frontend Server

Open a **new terminal window** (keep the backend running) and run:

```bash
cd frontend
python -m http.server 8080
```

The frontend will be available at `http://localhost:8080/demo.html`

### Step 3: Access the Application

Open your browser and navigate to:
```
http://localhost:8080/demo.html
```

---

## Project Structure

```
AI-RedTeam/
├── backend/
│   ├── backend.py          # Flask API server (port 5000)
│   └── emails.json         # Stores verified emails
└── frontend/
    └── demo.html           # Main frontend application
```

---

## Current File Structure and Status

### Top-Level Directory
- **README.md** - Project documentation containing setup instructions, running procedures, and project overview.
- **.gitignore** - Git ignore configuration file that excludes virtual environments, Python cache files, IDE files, and sensitive data files.

### Backend Directory (`backend/`)
- **backend.py** - Flask API server that handles email verification routes, processes email submissions via the `/verify` endpoint, extracts usernames from emails, and manages email storage.
- **emails.json** - JSON data file that stores verified email addresses along with extracted usernames and timestamps for each verification.

### Frontend Directory (`frontend/`)
- **demo.html** - Primary application UI built with React that provides the email entry form, handles email verification API calls, and displays the dashboard interface with scan type selection and attack initiation.

---

## Notes

- The backend must be running before using the frontend
- Emails submitted through the `/verify` endpoint are saved to `backend/emails.json`
- Keep both terminal windows open while using the application
