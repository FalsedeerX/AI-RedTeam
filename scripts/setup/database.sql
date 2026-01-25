-- [Database Automatic Setup]
-- Coded by Falsedeer / Copyright @ All Rights Reserved
-- Please run this script as user 'postgres'
--
--
-- Setup Users for Database's master, runtime and migration
\echo Creating required users for database management and runtime...... 
DO $$
BEGIN
	IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aesir') THEN
		RAISE NOTICE 'Creating role: aesir';
		CREATE ROLE aesir LOGIN PASSWORD 'change_me!';
	ELSE
		RAISE NOTICE 'Role aesir already exists !';
	END IF;

	IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'airedteam_runtime') THEN
		RAISE NOTICE 'Creating role: airedteam_runtime';
		CREATE ROLE airedteam_runtime LOGIN PASSWORD 'change_me!';
	ELSE
		RAISE NOTICE 'Role airedteam_runtime already exists !';
	END IF;

	IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'airedteam_alembic') THEN
		RAISE NOTICE 'Creating role: airedteam_alembic';
		CREATE ROLE airedteam_alembic LOGIN PASSWORD 'change_me!';
	ELSE
		RAISE NOTICE 'Role airedteam_alembic alredy exists !';
	END IF;
END
$$ ;

-- Setup and assign ownership of database and schema
\echo Setting up database......
CREATE DATABASE airedteam OWNER aesir;
\connect airedteam
CREATE SCHEMA app AUTHORIZATION airedteam_alembic;
ALTER DATABASE airedteam SET search_path TO app;

-- Install extensions for UUID generation
\echo Installing extension: pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA app;

-- Permission configuration
\echo Granting required permissions to runtime and migration user......
GRANT CONNECT ON DATABASE airedteam TO airedteam_runtime, airedteam_alembic;

-- Runtime user only allow CRUD permission
GRANT USAGE ON SCHEMA app TO airedteam_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO airedteam_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO airedteam_runtime;

-- Allow future sequences, table created by migration user accessible by runtime user
ALTER DEFAULT PRIVILEGES FOR ROLE airedteam_alembic IN SCHEMA app
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO airedteam_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE airedteam_alembic IN SCHEMA app
GRANT USAGE, SELECT ON SEQUENCES TO airedteam_runtime;
