# Guide de déploiement — Poker (Flask + React + Socket.IO)

Ce document décrit comment déployer l’application Poker en développement et en production, avec les bonnes pratiques pour Socket.IO (WebSocket), la construction du frontend React et la configuration d’un reverse proxy (Nginx).

## 1) Architecture générale
- Backend: Flask + Flask-SocketIO (événements temps réel). État en mémoire (dictionnaire `games`).
- Frontend: React (Create React App), communique via Socket.IO.
- En dev: proxy CRA → Flask (WebSocket inclus).
- En prod: deux approches recommandées:
  - A. Reverse proxy (Nginx) + serveur d’appli (gunicorn + eventlet) pour Flask, et React build servi par Nginx (ou un CDN).
  - B. Monolithique: builder le frontend et le servir via Flask (statique), toujours avec gunicorn + eventlet.

Important (scalabilité): l’état du jeu est en mémoire du processus Python. En production, utilisez UN SEUL worker/processus (pas de multi-process/scale-out), sinon partagez l’état et les événements via Redis (message queue) et externalisez l’état (refactor requis). Voir « Contraintes & Scalabilité ».

---

## 2) Développement local
Prérequis: Python 3.11+, Node.js LTS (≥ 18).

- Backend Flask (port 5000):
```bash
python3 start_server.py
```
- Frontend React (port 3000):
```bash
cd frontend
npm install
npm start
```
Le frontend (http://localhost:3000) utilise un proxy vers http://localhost:5000, compatible WebSocket (voir `frontend/package.json`, clé `proxy`).

---

## 3) Production — Option A: Nginx + gunicorn (eventlet) + React build

### 3.1 Construire le frontend
```bash
cd frontend
npm ci   # ou npm install --omit=dev en contexte CI/CD
npm run build
```
Le dossier `frontend/build` contient les fichiers statiques optimisés.

### 3.2 Installer les dépendances backend et gunicorn
Sur le serveur:
```bash
# Dans la racine du projet
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```
Note: Flask-SocketIO nécessite un worker asynchrone; ici nous utilisons `eventlet` (déjà présent dans `requirements.txt`).

### 3.3 Lancer le backend avec gunicorn + eventlet
```bash
# 1 worker (obligatoire vu l’état en mémoire), bind sur 127.0.0.1:5000
.venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:5000 app:app
```
Remarques:
- Le worker eventlet active le support WebSocket pour Flask-SocketIO.
- Gardez `-w 1` tant que l’état de jeu n’est pas externalisé.
- En alternative, un script `start_server.py` existe (dev), mais pour la prod préférez gunicorn supervisé (systemd).

### 3.4 Configurer Nginx (reverse proxy + WebSocket + fichiers statiques)
Exemple de serveur (HTTPS recommandé en prod):
```nginx
server {
    listen 80;
    server_name exemple.com;

    # Servir le build React
    root /chemin/vers/projet/frontend/build;
    index index.html;

    # Proxy pour l’API Socket.IO (chemin par défaut /socket.io/)
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    # (Optionnel) Proxy vers d’autres routes Flask si vous exposez des endpoints HTTP
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # SPA fallback: servir index.html pour les routes front (si routing côté client)
    location / {
        try_files $uri /index.html;
    }
}
```
Après modification, recharger Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 3.5 Service systemd (backend)
Unit file minimal `/etc/systemd/system/poker.service`:
```ini
[Unit]
Description=Poker Flask SocketIO (gunicorn+eventlet)
After=network.target

[Service]
User=www-data
WorkingDirectory=/chemin/vers/projet
Environment="PYTHONUNBUFFERED=1"
Environment="SECRET_KEY=${SECRET_KEY}"
ExecStart=/chemin/vers/projet/.venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:5000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
Activer et démarrer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable poker
sudo systemctl start poker
sudo systemctl status poker --no-pager
```

---

## 4) Production — Option B: Servir le build React via Flask
Si vous préférez un seul service:
1. Construire le frontend (`npm run build`).
2. Configurer Flask pour servir `frontend/build` comme statiques (ex: via `send_from_directory`) et définir la route `index` pour renvoyer `index.html`.
3. Lancer avec gunicorn + eventlet comme en 3.3.

Avantages: un binaire/service à gérer. Inconvénients: moins flexible côté cache/CDN.

---

## 5) Variables d’environnement & paramètres
- `SECRET_KEY`: remplacez la valeur codée en dur par une variable d’environnement en prod.
- CORS: actuellement `cors_allowed_origins="*"` dans Socket.IO; restreignez aux domaines nécessaires en prod (ex: `cors_allowed_origins=["https://exemple.com"]`).
- Ports & bind: exposez Flask seulement en loopback (127.0.0.1) derrière Nginx; Nginx écoute en 80/443.

---

## 6) Santé, logs et supervision
- Gunicorn: logs stdout/stderr capturés par journald (systemd). Utilisez `journalctl -u poker`.
- Nginx: surveillez les logs d’accès/erreurs; vérifiez les 101 Switching Protocols pour WebSocket.
- Health check: exposez une route HTTP simple (ex: `/healthz`) côté Flask si nécessaire.

---

## 7) Sécurité
- Activez HTTPS (Let’s Encrypt via certbot) et forcez HTTP→HTTPS.
- Limitez `cors_allowed_origins`.
- Mettez à jour régulièrement dépendances (`pip`, `npm`).
- Isolez le processus (utilisateur dédié, permissions minimales).

---

## 8) Contraintes & Scalabilité
- L’état de jeu est en mémoire du processus.
  - Ne pas utiliser plusieurs workers/processus ou plusieurs instances derrière le load-balancer.
  - Si vous devez scaler horizontalement: 
    - Utilisez Redis comme `message_queue` pour Flask-SocketIO (pub/sub des événements).
    - Externalisez/partagez l’état (ex: Redis/DB) et supprimez les singletons en mémoire.
- Sticky sessions côté proxy peuvent être nécessaires si vous ajoutez plusieurs backends.

---

## 9) Déploiement automatisé (optionnel)
- CI/CD: 
  - Job 1: build React (`npm ci && npm run build`) → artefact `frontend/build`.
  - Job 2: packager backend + artefact build → déployer sur serveur → `systemctl restart poker`.
- Docker (piste): multi-stage pour builder React puis copier dans une image Python.

Exemple d’image backend minimale (illustratif):
```dockerfile
FROM node:20 AS build-frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . ./
COPY --from=build-frontend /app/frontend/build ./frontend/build
EXPOSE 5000
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "app:app"]
```

---

## 10) Checklist de production
- [ ] `SECRET_KEY` défini via env (pas en dur)
- [ ] `cors_allowed_origins` restreint
- [ ] gunicorn avec `-k eventlet -w 1`
- [ ] Nginx proxy /socket.io/ avec Upgrade/Connection
- [ ] React build servi (Nginx ou Flask)
- [ ] HTTPS activé
- [ ] Logs/supervision en place

Pour toute question ou si vous souhaitez une configuration Docker/Nginx prête à l’emploi, voyez la section 9 ou demandez un exemple adapté à votre environnement.

