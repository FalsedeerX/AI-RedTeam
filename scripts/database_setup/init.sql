-- [Database Automatic Setup]
-- Coded by Falsedeer / Copyright @ All Rights Reserved
-- Please run this script as user 'postgres'-

\set ON_ERROR_STOP on

-- Dummy check before creating database
\echo [INFO] Checking whether database :db_name exists before proceeding ......
SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name') AS db_exists
\gset
\if :db_exists
	\echo [ERROR] Database :db_name already exists, aborting !!
	\quit
\endif

-- Setup Users for Database's master, runtime and migration
\echo [INFO] Creating required roles ...... 
SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_owner_user') AS role_exists
\gset
\if :role_exists
	\echo [WARNING] Role :db_owner_user already exists, skipping ......
\else
	\echo Creating role :db_owner_user ......
	CREATE ROLE :"db_owner_user" LOGIN PASSWORD :'db_owner_password';
\endif

SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_runtime_user') AS role_exists
\gset
\if :role_exists
	\echo [WARNING] Role :db_runtime_user already exists, skipping ......
\else
	\echo [INFO] Creating role :db_runtime_user ......
	CREATE ROLE :"db_runtime_user" LOGIN PASSWORD :'db_runtime_password';
\endif

SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_migrate_user') AS role_exists
\gset
\if :role_exists
	\echo [WARNING] Role :db_migrate_user already exists, skipping ......
\else
	\echo [INFO] Creating role :db_migrate_user ......
	CREATE ROLE :"db_migrate_user" LOGIN PASSWORD :'db_migrate_password';
\endif

-- Setup and assign ownership of database and schema
\echo [INFO] Creating database :db_name with owner :db_owner_user ......
CREATE DATABASE :"db_name" OWNER :"db_owner_user";
\connect :"db_name"

-- lockdown the public schema
\echo [INFO] Locking down default permissions ......
REVOKE ALL ON DATABASE :"db_name" FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- setup the desrired schema and set owner to migration user
\echo [INFO] Creating schema :db_schema owned by :db_migrate_user ......
CREATE SCHEMA :"db_schema" AUTHORIZATION :"db_migrate_user";

-- Install extensions for UUID generation
\echo [INFO] Installing extension: pgcrypto ......
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA :"db_schema";

-- Permission configuration
\echo [INFO] Granting permissions ......
GRANT CONNECT ON DATABASE :"db_name" TO :"db_runtime_user", :"db_migrate_user";

-- Database owner are allowed to inspect on the tables and field
GRANT USAGE ON SCHEMA :"db_schema" TO :"db_owner_user";
GRANT SELECT ON ALL TABLES IN SCHEMA :"db_schema" TO :"db_owner_user";

-- Runtime user only allow CRUD permission in schema
GRANT USAGE ON SCHEMA :"db_schema" TO :"db_runtime_user";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA :"db_schema" TO :"db_runtime_user";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA :"db_schema" TO :"db_runtime_user";

-- Allow future sequences, table created by migration user accessible by runtime user
ALTER DEFAULT PRIVILEGES FOR ROLE :"db_migrate_user" IN SCHEMA :"db_schema"
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"db_runtime_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"db_migrate_user" IN SCHEMA :"db_schema"
GRANT USAGE, SELECT ON SEQUENCES TO :"db_runtime_user";

-- Allow future created tables to be seen by database owner
ALTER DEFAULT PRIVILEGES FOR ROLE :"db_migrate_user" IN SCHEMA :"db_schema"
GRANT SELECT ON TABLES TO :"db_owner_user";


\echo [INFO] Database initialize completed successfully.

