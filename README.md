# Poker — Multi‑joueur (depuis le multi puzzle CodinGame de « wala »)

Projet WIP qui transforme une base CodinGame « multi puzzle » (auteur: wala) en un petit jeu de Texas Hold’em jouable en temps réel depuis un navigateur.

Lien d’origine: https://www.codingame.com/ide/demo/10121965805634331ad7899c59adcb65091817e


## Objectif du projet
- Offrir un bac à sable pédagogique pour un poker multi‑joueur temps réel (sockets, rooms, états de table, etc.).
- Démarrer vite en local (Python/Flask côté serveur, React côté client) puis itérer.
- Rester volontairement simple: certaines règles sont simplifiées et l’évaluation des mains est encore minimaliste (WIP).


## Architecture (vue d’ensemble)
- Backend: Flask + Flask‑SocketIO
  - Python 3.11+
  - Événements Socket.IO: `create_game`, `join_game`, `start_game`, `player_action`, `leave_game`
  - Diffusions côté serveur: `game_update`, `game_started`, `hand_dealt`, `hand_result`, `error`, `table_message`
  - Fichiers clés: `app.py` (mécanique de table, événements), `start_server.py` (lancement)
- Frontend: React (Create React App) + `socket.io-client`
  - Dossier: `frontend/`
  - Composant principal: `src/App.js`, client Socket: `src/socket.js`
  - En dev: serveur React (3000) avec proxy vers Flask (5000)
- Déploiement simple: build React servi statiquement par Flask (Option B)

Schéma simplifié:
Client (React) ⇄ Socket.IO ⇄ Flask (moteur de jeu)


## Gameplay (Texas Hold’em simplifié)
- Jusqu’à 6 joueurs; tapis initial: 1000; blinds: 10/20
- Phases: Préflop → Flop (3) → Turn (1) → River (1) → Showdown
- Actions quand c’est votre tour: check, call, raise, fold
- Si tous les joueurs restants sont all‑in, la révélation est automatique
- Les joueurs rejoignant une table en cours ne deviennent actifs qu’à la main suivante
- Note WIP: l’évaluation des mains est simplifiée/placeholder; le but est la démonstration temps réel

Références utiles:
- Classement des mains: https://en.wikipedia.org/wiki/Texas_hold_'em#Hand_values
- Probabilités/combinaisons: http://combinaison-poker.com/probabilite-poker?ssp=1&darkschemeovr=1&setlang=fr-FR&safesearch=moderate


## Démarrage rapide (local)
- Serveur (port 5000): exécuter `python3 start_server.py` à la racine
- Client (port 3000): dans `frontend/`, `npm install` puis `npm start`
- Option B: `npm run build` dans `frontend/` puis servir le build via Flask en relançant `start_server.py`

Astuce: en dev, accédez à l’UI sur http://localhost:3000 (le proxy redirige vers Flask). Le build statique est servi sur http://localhost:5000 quand présent.


## Démarrage combiné (full‑dev)

Pour lancer backend + frontend en une commande:

- Direct (client connecté directement au backend Socket.IO, pas de proxy WS CRA):
```bash
make dev
```
- Via le proxy CRA (utile si vous voulez tester le proxy /socket.io et /api):
```bash
make dev-proxy
```
- Polling only (client direct, WebSockets désactivés côté client — utile si votre réseau bloque WS):
```
make dev-polling
```
- WS forcé via proxy CRA (tester l’upgrade WebSocket de bout en bout):
make dev-ws

Variables utiles (surchargables en ligne de commande):
- HOST et PORT: où écoute le backend Flask (défauts: 0.0.0.0:5000)
- FRONTEND_PORT: port du serveur CRA (défaut: 3000)
- FLASK_LOG_ACCESS: 0 pour couper les logs d’accès Werkzeug (défaut: 0)
- PY: binaire Python (défaut: python3)
- NPM_BIN: binaire npm (défaut: npm)

Exemples:
```bash
# Backend sur 127.0.0.1:5001, frontend sur 3001
HOST=127.0.0.1 PORT=5001 FRONTEND_PORT=3001 make dev

# Lancer en mode proxy CRA
HOST=127.0.0.1 PORT=5000 make dev-proxy

# Lancer en mode direct avec polling forcé côté client
make dev-polling

# Lancer via proxy avec WS forcé
make dev-ws
```

Notes:
- Le mode direct équivaut à `npm run dev:direct` côté frontend: `REACT_APP_SOCKET_URL` est fixé à `http://localhost:${PORT}` et `REACT_APP_PROXY_SOCKETIO_WS=0`.
- Le mode polling only force `REACT_APP_SIO_POLLING_ONLY=1` côté client (pas de tentative WebSocket).
- Le mode WS forcé configure côté serveur `WEBSOCKET_ENABLED=1`, `ALLOW_UPGRADES=1`, `SOCKETIO_ASYNC_MODE=eventlet` et côté client `REACT_APP_PROXY_SOCKETIO_WS=1`. La dépendance `eventlet` est déjà listée dans `requirements.txt`.
- Le script de lancement est `scripts/dev.sh`. S’il n’est pas exécutable, rendez‑le exécutable:
```bash
chmod +x scripts/dev.sh
```
- Arrêt coordonné: Ctrl+C arrête backend et frontend.


## Alternatives et réglages fins

Pour éliminer les alertes récurrentes côté Flask (ex: `GET /ws 404`) et les erreurs WebSocket côté React/CRA (ex: `[HPM] WebSocket error: write after end`), voici des options pratiques.

1) Lancer le frontend en connexion directe (sans proxy WebSocket CRA)
- Avantage: supprime les erreurs HPM liées au proxy WS; le client se connecte directement au backend Socket.IO.
- Commandes:
```bash
cd frontend
npm run dev:direct
# ou pour surcharger l’URL côté client
REACT_APP_SOCKET_URL=http://127.0.0.1:5000 npm run dev:direct
```
- Détails: `dev:direct` définit `REACT_APP_SOCKET_URL` (par défaut http://localhost:5000) et `REACT_APP_PROXY_SOCKETIO_WS=0`.

2) Continuer avec le proxy CRA, mais ajuster le WS
- Par défaut, `npm start` active le proxy WS si aucune `REACT_APP_SOCKET_URL` n’est définie.
- Pour désactiver le WS du proxy (et donc éviter les erreurs HPM):
```bash
cd frontend
REACT_APP_PROXY_SOCKETIO_WS=0 npm start
```
- Pour forcer le WS côté client même via proxy, laissez `REACT_APP_PROXY_SOCKETIO_WS` à 1 et assurez‑vous que le backend supporte WS (voir point 4).

3) Forcer le polling côté client Socket.IO
- Utile si votre réseau/hébergeur bloque les WebSockets (VPN, proxy d’entreprise, PaaS):
```bash
cd frontend
REACT_APP_SIO_POLLING_ONLY=1 npm run dev:direct
# ou avec le proxy CRA
REACT_APP_SIO_POLLING_ONLY=1 npm start
```

4) Activer correctement WebSocket côté serveur Flask‑SocketIO
- Installer un worker asynchrone compatible WS et activer les upgrades:
```bash
pip install eventlet  # ou gevent
```
- Variables utiles:
  - `WEBSOCKET_ENABLED=1` pour activer WS explicitement (sinon auto si eventlet/gevent présent)
  - `ALLOW_UPGRADES=1` pour autoriser l’upgrade polling→websocket
  - `SOCKETIO_ASYNC_MODE=eventlet|gevent|threading` pour choisir le mode

5) Réduire/masquer le bruit des logs côté Flask
- Couper les logs d’accès Werkzeug:
```bash
export FLASK_LOG_ACCESS=0
python3 start_server.py
```
- Par défaut, certaines lignes d’accès vers `/ws` et `/socket.io` sont filtrées afin d’alléger la console en dev.

6) Dépannage rapide
- Vous voyez `[HPM] WebSocket error: write after end` dans la console React:
  - Lancez `npm run dev:direct`, ou bien `REACT_APP_PROXY_SOCKETIO_WS=0 npm start`.
  - Ou forcez le polling: `REACT_APP_SIO_POLLING_ONLY=1`.
- Vous voyez des `GET /ws 404` dans la console Flask:
  - Inoffensif (heartbeat WDS). Déjà filtré en dev; sinon exportez `FLASK_LOG_ACCESS=0`.
- Les WebSockets ne s’établissent pas:
  - Vérifiez l’installation d’`eventlet` (ou `gevent`) et exportez `WEBSOCKET_ENABLED=1`.
