#!/usr/bin/env bash
# Dev launcher: backend (Flask-SocketIO) + frontend (CRA) en parallèle
# - macOS/bash compatible (pas de `wait -n`)
# - arrêt coordonné (Ctrl+C arrête les deux)

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Paramètres avec valeurs par défaut (surchargez via env)
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
CLIENT_MODE="${CLIENT_MODE:-direct}"   # direct | proxy
FLASK_LOG_ACCESS="${FLASK_LOG_ACCESS:-0}" # 0 = couper logs d'accès Werkzeug
PY="${PY:-python3}"
NPM_BIN="${NPM_BIN:-npm}"

# Gestion des processus
PIDS=()
cleanup() {
  local status=$?
  echo "[dev] Arrêt des processus (PIDs: ${PIDS[*]:-})"
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  # Attendre leur fin pour éviter les orphelins
  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
  exit $status
}
trap cleanup INT TERM

# 1) Backend
(
  # Propager options Socket.IO serveur si fournies
  export HOST PORT FLASK_LOG_ACCESS WEBSOCKET_ENABLED ALLOW_UPGRADES SOCKETIO_ASYNC_MODE
  echo "[dev] Backend → http://localhost:${PORT} (HOST=${HOST})"
  if [ -n "${WEBSOCKET_ENABLED:-}" ]; then
    echo "[dev] WS serveur: WEBSOCKET_ENABLED=${WEBSOCKET_ENABLED} ALLOW_UPGRADES=${ALLOW_UPGRADES:-} ASYNC_MODE=${SOCKETIO_ASYNC_MODE:-auto}"
  fi
  exec "$PY" start_server.py
) &
PIDS+=($!)

# 2) Frontend
(
  cd "$ROOT_DIR/frontend"
  if [ ! -d node_modules ]; then
    echo "[dev] Installation des dépendances frontend (npm install)…"
    "$NPM_BIN" install
  fi
  if [ "$CLIENT_MODE" = "direct" ]; then
    export REACT_APP_SOCKET_URL="${REACT_APP_SOCKET_URL:-http://localhost:${PORT}}"
    export REACT_APP_PROXY_SOCKETIO_WS=0
    echo "[dev] Frontend (direct) → http://localhost:${FRONTEND_PORT} (REACT_APP_SOCKET_URL=${REACT_APP_SOCKET_URL})"
    exec "$NPM_BIN" run dev:direct
  else
    # Proxy CRA classique (forcer WS proxy, et éviter une URL directe si héritée de l'environnement)
    unset REACT_APP_SOCKET_URL || true
    export REACT_APP_PROXY_SOCKETIO_WS="${REACT_APP_PROXY_SOCKETIO_WS:-1}"
    echo "[dev] Frontend (proxy CRA) → http://localhost:${FRONTEND_PORT} (WS proxy=${REACT_APP_PROXY_SOCKETIO_WS})"
    exec "$NPM_BIN" start
  fi
) &
PIDS+=($!)

# Boucle de surveillance portable (Bash 3/macOS): s'arrête si l'un des deux meurt
while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "[dev] Le processus PID=$pid s'est terminé — arrêt des autres…"
      cleanup
    fi
  done
  sleep 1
done

