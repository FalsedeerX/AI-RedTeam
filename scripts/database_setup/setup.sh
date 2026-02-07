#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="../../.env"


# file existance check
if [[ ! -f "$ENV_FILE" ]]; then
	echo "[ERROR] .env file not found at $ENV_FILE !!"
	exit 1
fi

# load in the required variable from .env
set -a
source ../../.env
set +a

# auto setup the database
sudo -u postgres psql \
	-v db_name="$DB_NAME" \
	-v db_schema="$DB_SCHEMA" \
	-v db_owner_user="$DB_OWNER_USER" \
	-v db_owner_password="$DB_OWNER_PASSWORD" \
	-v db_runtime_user="$DB_RUNTIME_USER" \
	-v db_runtime_password="$DB_RUNTIME_PASSWORD" \
	-v db_migrate_user="$DB_MIGRATE_USER" \
	-v db_migrate_password="$DB_MIGRATE_PASSWORD" \
	-f init.sql

