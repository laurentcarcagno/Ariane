#!/bin/sh
# Runs once, on first start of the data volume: one database and one owner per service.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE USER ariane WITH PASSWORD '${ARIANE_DB_PASSWORD}';
CREATE DATABASE ariane OWNER ariane;
CREATE USER keycloak WITH PASSWORD '${KEYCLOAK_DB_PASSWORD}';
CREATE DATABASE keycloak OWNER keycloak;
SQL
