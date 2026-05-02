#!/usr/bin/env bash
# Menghentikan stack AgentPay dengan rapi.
set -euo pipefail
cd "$(dirname "$0")"
docker compose down --remove-orphans "$@"
