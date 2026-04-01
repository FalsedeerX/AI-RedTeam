# How to Guide - AIRedTeam

---

## For Developer

### How to install required dependencies

#### Purpose

Prepare a local development environment to run the frontend & backend system.

#### Precondition

- Linux system (Arch preferred, but should work on Debian/Ubuntu too)
- Python ver-3.14+ installed
- NodeJS ver-25+ instaled

#### Steps

1. Clone this repo to your local system

```bash
git clone https://github.com/FalsedeerX/AI-RedTeam
```

2. Create a virtual envrionement and install required packages for backend.

```bash
cd backend
virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Install the required packages for frontend.

```bash
cd frontend
npm install
```

#### Expected Result

The development environment is set up with all required dependencies installed.

### How to configure the environment variables for server

#### Purpose

Configure the database credentials required by the server, including master, runtime, and migration users.

#### Precondition

- Linux system with a preferred text editor installed (ex. `nano`, `vi`, `vim` ......etc)

#### Steps

1. Copy the template to project root

```bash
cp scripts/dotenv_template .env
```

2. Fill up the placeholders inside `.env` with your favoriate text editor

```bash
vim .env
```

#### Expected Results

The server can successfully authenticate with the database using the configured users for different operations, and the database setup scripts will automatically use these credentials to create and initialize the database.

### How to initialize the database

#### Purpose

Setup the database and schemas from the preconfigured envrionment variables.

#### Precondition

- Envrionment variables configured in project root (`.env`)
- Linux system (Arch preferred, but should work on Debian/Ubuntu too)
- PostgreSQL installed

#### Steps

1. Ensure the conguration file exists

```bash
[ -f /path/to/file ] && echo "configuration file exists" || echo "configuration file not found"
```

2. Invoke the database setup script

```bash
cd scripts/database-setup
chmod 744 setup.sh
./setup.sh
```

#### Expected Results

The database instance is created and initialized with the required schema and tables.

### How to start the server

#### Purpose

Start the backend and frontend server for development and testing.

#### Precondition

- Required dependencies installed
- Database schema and tables fully initiailzied
- Envrionment variables configured in project root (`.env`)
- Linux system (Arch preferred, but should work on Debian/Ubuntu too)
- PostgreSQL installed

#### Steps

1. Invoke the backend server

```bash
cd backend
source .venv/bin/activate
python backend.py &
```

2. Invoke the frontend server

```bash
cd frontend
npm run dev &
```

#### Expected Results

The backend and frontend servers start successfully, and the frontend can be accessed through a local browser.

---

## For End User

### How to register a new account

#### Purpose

Create a new user account to access the system.

#### Preconditions

- The server is running
- The web interface is accessible through a browser

#### Steps

1. Open the web interface.
2. Navigate to the registration page.
3. Enter the required information. (e.g., username, email, password)
4. Submit the registration form.

#### Expected Results

A new account is created successfully, and the user can log in to the system.

### How to create a new project

#### Purpose

Create a new project to organize and manage analysis tasks.

#### Preconditions

- The server is running
- User have a valid user account to access dashboard

#### Steps

1. Login the system.
1. Navigate to the dashboard.
2. Click the `Create Project` button.
3. Enter the project name and any required details.
4. Submit the form.

#### Expected Result

A new project is created and appears in the project list.

### How to configure a target

#### Purpose

Define the target for analysis within a project.

#### Preconditions

- The server is running
- User have a valid user account to access dashboard
- A project has been created

#### Steps

1. Login the system
1. Open the desired project on the dashboard.
3. Enter the target information (e.g., domain, IP address, CIDR).
4. Click `Add Target` button.

#### Expected Result

The target is saved and associated with the selected project.

### How to start analysis on a project

#### Purpose

Start the analysis process for a configured project.

#### Preconditions

- The server is running
- User have a valid user account to access dashboard
- A project with a configured target exists

#### Steps

1. Login the system.
1. Open the desired project on the dashboard.
2. Click on the “Start Analysis” or “Run” button.

### Expected Result

The system starts the analysis process and redirect user to the web terminal.

---

## GenAI Usage Statement

No AI is used for creating this documenation.
