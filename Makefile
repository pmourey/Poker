SHELL := /bin/bash

# Valeurs par défaut; surchargez via: make option-b SECRET_KEY=... HOST=... PORT=...
SECRET_KEY ?= change-me-in-prod
HOST ?= 0.0.0.0
PORT ?= 5000
FRONTEND_PORT ?= 3000
FLASK_LOG_ACCESS ?= 0

# Interpréteur Python (surchargable):
PY ?= python3
# Gestionnaire Node (surchargable):
NPM_BIN ?= npm
# Délai d'attente après démarrage serveur avant test (secondes):
WAIT ?= 3

.PHONY: option-b
option-b:
	@echo "[make] Lancement Option B (build React + start Flask)"
	@SECRET_KEY=$(SECRET_KEY) HOST=$(HOST) PORT=$(PORT) bash scripts/option_b.sh

.PHONY: smoke
smoke:
	@set -euo pipefail; \
	echo "[smoke] Installation des dépendances Python..."; \
	$(PY) -m pip install -r requirements.txt >/dev/null; \
	echo "[smoke] Vérification de la connectivité Redis..."; \
	$(PY) scripts/check_redis.py; \
	echo "[smoke] Démarrage du serveur Flask-SocketIO (polling-only)..."; \
	SMOKE_HOST=$${HOST:-127.0.0.1}; \
	SMOKE_PORT=$${PORT:-5000}; \
	$(PY) start_server.py >/tmp/poker_smoke_server.log 2>&1 & \
	SERVER_PID=$$!; \
	echo $$SERVER_PID > .smoke_server.pid; \
	sleep $(WAIT); \
	TARGET_URL=$${SMOKE_SERVER_URL:-http://$$SMOKE_HOST:$$SMOKE_PORT}; \
	echo "[smoke] Exécution du smoke test contre $$TARGET_URL ..."; \
	SMOKE_SERVER_URL="$$TARGET_URL" $(PY) scripts/smoke_socketio.py; \
	STATUS=$$?; \
	echo "[smoke] Arrêt du serveur (PID=$$SERVER_PID)"; \
	kill $$SERVER_PID >/dev/null 2>&1 || true; \
	rm -f .smoke_server.pid; \
	exit $$STATUS

.PHONY: smoke-verbose
smoke-verbose:
	@set -euo pipefail; \
	if $(MAKE) -s smoke; then \
	  exit 0; \
	else \
	  echo "[smoke-verbose] Échec du smoke test — extrait du journal serveur:"; \
	  tail -n 200 /tmp/poker_smoke_server.log || true; \
	  exit 1; \
	fi

# Variante sans Redis: ne vérifie pas la connectivité Redis et lance le serveur avec REDIS_URL vidé
.PHONY: smoke-no-redis
smoke-no-redis:
	@set -euo pipefail; \
	echo "[smoke-no-redis] Installation des dépendances Python..."; \
	$(PY) -m pip install -r requirements.txt >/dev/null; \
	echo "[smoke-no-redis] Démarrage du serveur Flask-SocketIO sans Redis (polling-only)..."; \
	SMOKE_HOST=$${HOST:-127.0.0.1}; \
	SMOKE_PORT=$${PORT:-5000}; \
	REDIS_URL= $(PY) start_server.py >/tmp/poker_smoke_server.log 2>&1 & \
	SERVER_PID=$$!; \
	echo $$SERVER_PID > .smoke_server.pid; \
	sleep $(WAIT); \
	TARGET_URL=$${SMOKE_SERVER_URL:-http://$$SMOKE_HOST:$$SMOKE_PORT}; \
	echo "[smoke-no-redis] Exécution du smoke test contre $$TARGET_URL ..."; \
	SMOKE_SERVER_URL="$$TARGET_URL" $(PY) scripts/smoke_socketio.py; \
	STATUS=$$?; \
	echo "[smoke-no-redis] Arrêt du serveur (PID=$$SERVER_PID)"; \
	kill $$SERVER_PID >/dev/null 2>&1 || true; \
	rm -f .smoke_server.pid; \
	exit $$STATUS

.PHONY: smoke-verbose-no-redis
smoke-verbose-no-redis:
	@set -euo pipefail; \
	if $(MAKE) -s smoke-no-redis; then \
	  exit 0; \
	else \
	  echo "[smoke-verbose-no-redis] Échec du smoke test — extrait du journal serveur:"; \
	  tail -n 200 /tmp/poker_smoke_server.log || true; \
	  exit 1; \
	fi

# Smoke test contre une instance distante (ex: PythonAnywhere) — ne démarre pas de serveur local
.PHONY: smoke-remote
smoke-remote:
	@set -euo pipefail; \
	if [ -z "$$SMOKE_SERVER_URL" ]; then \
	  echo "[smoke-remote] ERREUR: définissez SMOKE_SERVER_URL (ex: https://<user>.pythonanywhere.com)"; \
	  exit 2; \
	fi; \
	echo "[smoke-remote] Exécution du smoke test contre $$SMOKE_SERVER_URL ..."; \
	$(PY) scripts/smoke_socketio.py

.PHONY: smoke-remote-verbose
smoke-remote-verbose:
	@set -euo pipefail; \
	if $(MAKE) -s smoke-remote; then \
	  exit 0; \
	else \
	  echo "[smoke-remote-verbose] Échec du smoke test distant. Vérifiez les logs WSGI sur PythonAnywhere (onglet Web > View logs)."; \
	  exit 1; \
	fi

# Démarrage combiné: backend + frontend (mode direct par défaut)
.PHONY: dev dev-proxy dev-polling dev-ws
dev:
	@echo "[make] Dev (backend+frontend — direct)"
	@HOST=$(HOST) PORT=$(PORT) FRONTEND_PORT=$(FRONTEND_PORT) FLASK_LOG_ACCESS=$(FLASK_LOG_ACCESS) PY=$(PY) NPM_BIN=$(NPM_BIN) CLIENT_MODE=direct bash scripts/dev.sh

dev-proxy:
	@echo "[make] Dev (backend+frontend — proxy CRA)"
	@HOST=$(HOST) PORT=$(PORT) FRONTEND_PORT=$(FRONTEND_PORT) FLASK_LOG_ACCESS=$(FLASK_LOG_ACCESS) PY=$(PY) NPM_BIN=$(NPM_BIN) CLIENT_MODE=proxy bash scripts/dev.sh

# Variante directe avec polling forcé côté client
# Utile si votre réseau/hébergeur bloque les WebSockets

dev-polling:
	@echo "[make] Dev (backend+frontend — direct, polling only)"
	@HOST=$(HOST) PORT=$(PORT) FRONTEND_PORT=$(FRONTEND_PORT) FLASK_LOG_ACCESS=$(FLASK_LOG_ACCESS) PY=$(PY) NPM_BIN=$(NPM_BIN) CLIENT_MODE=direct REACT_APP_SIO_POLLING_ONLY=1 bash scripts/dev.sh

# Variante proxy avec WebSocket forcé de bout en bout
# Nécessite eventlet (ou gevent) installé — déjà présent dans requirements.txt

dev-ws:
	@echo "[make] Dev (backend+frontend — proxy CRA, WebSocket forcé)"
	@HOST=$(HOST) PORT=$(PORT) FRONTEND_PORT=$(FRONTEND_PORT) FLASK_LOG_ACCESS=$(FLASK_LOG_ACCESS) PY=$(PY) NPM_BIN=$(NPM_BIN) CLIENT_MODE=proxy WEBSOCKET_ENABLED=1 ALLOW_UPGRADES=1 SOCKETIO_ASYNC_MODE=eventlet REACT_APP_PROXY_SOCKETIO_WS=1 bash scripts/dev.sh
