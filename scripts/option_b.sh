#!/usr/bin/env bash
set -euo pipefail

# Petit script pour builder le frontend et démarrer le backend en mode Option B (Flask sert le build React)
# Utilisation:
#   bash scripts/option_b.sh

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
FRONT_DIR="$BASE_DIR/frontend"

info() { echo -e "[option-b] $*"; }

# 1) Build frontend
info "Build du frontend React…"
cd "$FRONT_DIR"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
npm run build

# 2) Démarrage backend Flask (utilise le build si présent)
cd "$BASE_DIR"
: "${SECRET_KEY:=change-me-in-prod}"
: "${HOST:=0.0.0.0}"
: "${PORT:=5000}"
info "SECRET_KEY=${SECRET_KEY} (défini via env; changez-le en prod)"
info "HOST=${HOST} | PORT=${PORT}"

# 2.5) Vérifier que le port est libre
info "Vérification disponibilité du port…"
if ! HOST="$HOST" PORT="$PORT" python3 - "$HOST" "$PORT" <<'PY'
import os, socket, sys
host = os.environ.get('HOST', '0.0.0.0')
port = int(os.environ.get('PORT', '5000'))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind((host, port))
except OSError as e:
    print(f"Port occupé sur {host}:{port} — {e}", file=sys.stderr)
    sys.exit(1)
finally:
    s.close()
PY
then
  echo "[option-b] ❌ Le port ${PORT} semble occupé sur ${HOST}." >&2
  if command -v lsof >/dev/null 2>&1; then
    echo "[option-b] Processus à l'écoute (lsof):" >&2
    lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN || true
  else
    echo "[option-b] Astuce: essayez 'lsof -nP -iTCP:${PORT} -sTCP:LISTEN' pour identifier le processus." >&2
  fi
  echo "[option-b] ➜ Libérez le port ou relancez avec un autre PORT, ex.: PORT=5050" >&2
  exit 1
fi

info "Démarrage du serveur Flask (${HOST}:${PORT})…"
HOST="$HOST" PORT="$PORT" python3 start_server.py
