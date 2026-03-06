#!/usr/bin/env bash
set -euo pipefail

# Convenience launcher for local/dev container runs.
PORT="${PORT:-8501}"
SERVER_NAME="${SERVER_NAME:-0.0.0.0}"

exec streamlit run app.py \
  --server.address "${SERVER_NAME}" \
  --server.port "${PORT}" \
  --server.headless true
