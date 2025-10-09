# Poker

Multi-player puzzle in WIP provided by wala

https://www.codingame.com/ide/demo/10121965805634331ad7899c59adcb65091817e

#### Classement des mains:
    https://en.wikipedia.org/wiki/Texas_hold_'em#Hand_values

#### Combinaisons au poker:
    http://combinaison-poker.com/probabilite-poker?ssp=1&darkschemeovr=1&setlang=fr-FR&safesearch=moderate

---

## Frontend React (intégration avec Flask)

Une application React a été ajoutée dans `frontend/` et communique avec le serveur Flask via Socket.IO. Le proxy de développement est configuré pour rediriger les WebSockets et éviter les problèmes de CORS.

> Nouveau: pour publier le frontend sur GitHub Pages (hébergement statique), voir `Deployment_Github_Pages.md`.

### Prérequis
- Node.js LTS (>= 18) et npm
- Python 3.11+ (pour le backend Flask)

### Installation et démarrage

Backend Flask (port 5000):

```bash
# Depuis la racine du projet
python3 start_server.py
```

Frontend React (port 3000):

```bash
cd frontend
npm install
npm start
```

Le frontend est servi sur http://localhost:3000 et utilise un proxy vers http://localhost:5000 pour l’API Socket.IO.

### Utilisation rapide
1. Ouvrez http://localhost:3000
2. Entrez un nom de joueur et cliquez sur "Créer" pour créer une partie (un ID sera généré), ou entrez un ID de partie existant pour "Rejoindre".
3. Une fois au moins 2 joueurs dans la partie, cliquez sur "Démarrer une main".
4. Les actions disponibles (check/call/raise/fold) s’activent lorsque c’est votre tour.

### Détails techniques
- Client Socket.IO: `frontend/src/socket.js`
- UI principale: `frontend/src/App.js`
- Proxy CRA -> Flask: `frontend/package.json` (champ `proxy`)
- Côté Flask, chaque client rejoint une room personnelle basée sur son `player_id` pour recevoir des événements privés comme `hand_dealt`.

### Dépannage
- Assurez-vous que le backend écoute sur le port 5000 avant de lancer le frontend.
- Si le frontend ne se connecte pas au socket, vérifiez que `socket.io-client` est bien installé (`npm install` dans `frontend/`).
- Si vous avez modifié les ports, mettez à jour la valeur du `proxy` dans `frontend/package.json` et le point de connexion dans `frontend/src/socket.js`.

### Option B: Servir le build React via Flask
1. Construire le frontend:
```bash
cd frontend
npm install
npm run build
```
2. Lancer Flask (utilise le build si présent):
```bash
# À la racine du projet
export SECRET_KEY="change-me-in-prod"  # macOS/Linux
python3 start_server.py
```
3. Ouvrez http://localhost:5000 (le serveur Flask servira `frontend/build/index.html`).

#### Lancer en une commande
Avec Make (recommandé):
```bash
make option-b                        # utilise SECRET_KEY=change-me-in-prod, HOST=0.0.0.0, PORT=5000
make option-b SECRET_KEY="ma-cle"   # surcharger la clé secrète
make option-b HOST=127.0.0.1 PORT=5050  # surcharger hôte et port
```

Sans Make (script bash):
```bash
bash scripts/option_b.sh                              # utilise $SECRET_KEY/$HOST/$PORT si définis, sinon défauts
SECRET_KEY="ma-cle" HOST=127.0.0.1 PORT=5050 bash scripts/option_b.sh
```

Note: si vous utilisez gunicorn en production, suivez `Deployment_details.md` (worker eventlet requis) et configurez un reverse proxy (Nginx) pour les WebSockets.
