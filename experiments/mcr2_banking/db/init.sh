#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_password="$MCR_DB_APP_PASSWORD" -f /opt/mcr/schema.sql
