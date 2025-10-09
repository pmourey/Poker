# Déploiement — Option B: Servir le build React via Flask

Ce guide décrit comment utiliser Flask pour servir directement le build React (sans serveur web frontal), tout en gardant Socket.IO fonctionnel pour le temps réel. Idéal pour un déploiement simple (monolithique) ou pour des environnements de test/staging.

---

## 1) Prérequis
- Python 3.11+ et `pip`
- Node.js LTS (≥ 18) et `npm`
- Dépendances backend installées: `pip install -r requirements.txt`

---

## 2) Construire le frontend
À partir de la racine du projet:

```bash
cd frontend
npm install
npm run build
```

Résultat: le dossier `frontend/build` contient `index.html`, les bundles JS/CSS et les assets.

---

## 3) Comportement de Flask (déjà codé)
Le serveur Flask est configuré pour:
- Servir `frontend/build/index.html` à la racine `/` si le build existe.
- Servir les assets React sur `/static/<fichier>` (ceux du build React).
- Servir certains fichiers à la racine (`/manifest.json`, `/asset-manifest.json`, `/favicon.ico`).
- Rester compatible avec Socket.IO (endpoint par défaut `/socket.io/`).
- Exposer une route de santé: `/healthz` → `{ "status": "ok" }`.

Important: les anciennes pages Jinja (templates) peuvent entrer en conflit avec `/static` du build React. Pendant la migration vers React, préférez utiliser l’UI React; sinon, envisagez d’isoler les assets React sous un autre préfixe.

---

## 4) Lancement en local (simple)
Depuis la racine du projet:

```bash
# Définissez un secret non trivial (obligatoire en prod)
export SECRET_KEY="change-me-in-prod"

# Démarrer le serveur Flask (Socket.IO intégré)
python3 start_server.py
```

Ouvrez: http://localhost:5000

Observations:
- La page d’accueil sert le build React si `frontend/build/index.html` existe.
- Les WebSockets Socket.IO fonctionnent sur `/socket.io/`.

---

## 5) Production minimale (gunicorn + eventlet)
Même sans Nginx, vous pouvez lancer un service réseau directement (non recommandé sans proxy/HTTPS, mais possible pour un POC ou un réseau interne).

```bash
# Dans la racine du projet
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn

# 1 worker (état en mémoire), eventlet pour WebSocket
export SECRET_KEY="votre-secret-fort"
.venv/bin/gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 app:app
```

Bonnes pratiques:
- Restez sur un seul worker `-w 1` (état de jeu en mémoire du processus).
- Ajoutez un reverse proxy (Nginx/Traefik) + HTTPS pour une vraie prod (voir `Deployment_details.md`).
- Restreignez `cors_allowed_origins` de Flask-SocketIO aux domaines de confiance en production.

---

## 6) Variables d’environnement
- `SECRET_KEY`: clé secrète Flask. Définit impérativement une valeur forte en prod (ne pas commiter en dur).
- Ports: modifiez le bind de gunicorn (ex: `-b 127.0.0.1:5000`) si vous mettez un reverse proxy en face.

---

## 7) Vérifications et santé
- Santé: http://localhost:5000/healthz doit répondre `{ "status": "ok" }`.
- Socket.IO: le client React se connecte automatiquement; surveillez la console navigateur et les logs serveur pour les événements `connect`.
- 404 assets: vérifiez que `frontend/build` existe et que le serveur a les droits de lecture.

---

## 8) Dépannage
- 404 sur `/static/...`: assurez-vous d’avoir exécuté `npm run build` et que `frontend/build/static` existe.
- La page ne s’affiche pas après build:
  - Vérifiez que `index.html` est présent dans `frontend/build`.
  - Redémarrez le serveur Flask après avoir généré un nouveau build.
- Conflits avec les templates Flask:
  - L’URL `/static` sert désormais les assets React. Si vos anciens templates dépendent d’`/static` côté Flask, ils peuvent ne plus trouver leurs assets.
  - Solutions: migrer l’UI vers React, ou servir les assets React sur un autre préfixe (ajustement code requis), ou ne pas utiliser les templates en parallèle.
- WebSocket ne se connecte pas:
  - Vérifiez que vous utilisez `eventlet` avec gunicorn.
  - Derrière un reverse proxy, assurez-vous d’avoir les headers Upgrade/Connection (voir `Deployment_details.md`).

---

## 9) Rappel sécurité & scalabilité
- Clé secrète forte et gardée hors dépôt.
- CORS restreint en prod.
- 1 seul worker tant que l’état n’est pas externalisé.
- Pour scaler: bus d’événements (Redis via `message_queue` Flask-SocketIO) + état externalisé (DB/Redis).

---

## 10) Résumé
- Build React → `frontend/build`
- Flask sert automatiquement le build à `/` s’il est présent
- Socket.IO reste accessible sur `/socket.io/`
- Local: `python3 start_server.py`
- Prod minimale: `gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 app:app`
- Pour une prod robuste (HTTPS, proxy WebSocket), voir `Deployment_details.md`

