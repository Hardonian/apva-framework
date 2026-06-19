#!/usr/bin/env bash
set -Eeuo pipefail

HOST="${1:-}"
PORT="${2:-}"
TIMEOUT="${3:-60}"

if [ -z "${HOST}" ] || [ -z "${PORT}" ]; then
  echo "Usage: $0 <host> <port> [timeout_seconds]" >&2
  exit 2
fi

start=$(date +%s)
until python - <<PY
import socket
host = "${HOST}"
port = int("${PORT}")
with socket.create_connection((host, port), timeout=2):
    pass
PY
do
  now=$(date +%s)
  if [ $((now - start)) -ge "${TIMEOUT}" ]; then
    echo "Timed out waiting for ${HOST}:${PORT}" >&2
    exit 1
  fi
  sleep 1
done
