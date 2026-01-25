-- [Database Automatic Setup]
-- Coded by Falsedeer / Copyright @ All Rights Reserved
-- Please run this script as user 'postgres'
--
--
-- Setup Users for Database's master, runtime and migration
\echo 
DO $$
BEGIN
	IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aesir') THEN
		RAISE NOTICE 'Creating role: aesir';
		CREATE ROLE falsedeer LOGIN PASSWORD 'change_me!';
	ELSE
		RAISE NOTICE 'Role falsedeer already exists !';
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
CREATE SCHEMA app AUTHORIZATION aesir;
ALTER DATABASE airedteam SET search_path TO app;
