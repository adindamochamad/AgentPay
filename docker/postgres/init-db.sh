#!/bin/sh
set -e

# Hanya dijalankan saat volume data PostgreSQL pertama kali diinisialisasi.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE agentpay_test;
EOSQL
