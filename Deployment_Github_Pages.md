# Déployer le frontend sur GitHub Pages

Ce guide explique comment publier le frontend React de ce projet sur GitHub Pages. Le backend Flask/Socket.IO reste hébergé séparément (ex: PythonAnywhere).

Points clés:
- GitHub Pages sert des fichiers statiques (frontend uniquement).
- Le backend doit être accessible publiquement (HTTPS recommandé) et autoriser les connexions cross‑origin.
- Ce dépôt contient déjà un workflow GitHub Actions prêt à l’emploi pour construire et déployer le frontend.

---

## Prérequis
- Un dépôt GitHub avec ce projet.
- GitHub Pages activé en mode “GitHub Actions”.
- Un backend accessible en HTTPS (existant: `https://poker06.eu.pythonanywhere.com`).

---

## Ce que fait le dépôt pour vous
- Workflow Pages: `.github/workflows/deploy-frontend.yml`
  - Construit `frontend/` avec Node 18 et publie `frontend/build` sur GitHub Pages.
  - Injecte `REACT_APP_SOCKET_URL` dans le build. Si la variable n’est pas définie dans GitHub, un fallback utilise `https://poker06.eu.pythonanywhere.com`.
- CRA (Create React App) configuré pour Pages:
  - `frontend/package.json` inclut `"homepage": "."` pour des chemins relatifs.
  - `postbuild` copie `index.html` en `404.html` (fallback SPA nécessaire sur Pages).

---

## Configuration une fois dans GitHub
1) Activer GitHub Pages (piloté par Actions)
- Repository → Settings → Pages
- Build and deployment → Source: GitHub Actions

2) (Optionnel) Définir l’URL backend dans les Variables
- Repository → Settings → Secrets and variables → Actions → Variables (onglet “Variables”)
- Ajouter: `REACT_APP_SOCKET_URL = https://poker06.eu.pythonanywhere.com`
- Si vous ne définissez pas la variable, le workflow utilisera le fallback défini (PythonAnywhere ci‑dessus).

---

## Déployer
- Poussez vos changements sur la branche `main` (le workflow s’exécute automatiquement), ou lancez‑le manuellement dans l’onglet “Actions”.
- À la fin, l’URL publique est disponible dans la sortie du job “Deploy to GitHub Pages”. Elle aura la forme:
  - `https://<votre-compte>.github.io/<nom-du-repo>/`

---

## Je ne trouve pas l’onglet “Actions”
Si vous ne voyez pas l’onglet “Actions” en haut du dépôt (Code, Issues, Pull requests, Actions, …):

- Accédez directement à l’URL des Actions en remplaçant `<compte>` et `<repo>`:
  - `https://github.com/<compte>/<repo>/actions`
- Vérifiez que vous avez bien poussé le workflow dans la branche par défaut (fichier `.github/workflows/deploy-frontend.yml`). Sans workflow, l’onglet doit quand même apparaître, mais l’accès direct vous confirmera l’état.
- Sur un fork: GitHub désactive souvent les Actions par défaut. Ouvrez l’onglet “Actions” et cliquez sur “Enable Actions on Fork” (ou le bouton d’activation). Sinon, dans `Settings → Actions → General`, autorisez l’exécution des workflows sur le fork.
- Dans une organisation: il se peut que les Actions soient désactivées au niveau organisation. Demandez à un propriétaire d’activer: `Organization settings → Actions → General → Allow GitHub Actions to be used in this organization` puis, côté dépôt, `Settings → Actions → General → Allow all actions and reusable workflows`.
- Permissions: assurez‑vous d’avoir au moins un rôle “Write” sur le dépôt pour voir/relancer les workflows. Les visiteurs non collaborateurs n’ont pas tous les contrôles.
- Interface compacte/mobile: sur affichage réduit, les onglets sont regroupés derrière un menu hamburger “More”/“…”; ouvrez ce menu pour trouver “Actions”.
- Alternative de suivi: `Settings → Pages` affiche aussi l’état des derniers déploiements GitHub Pages et des liens “View deployment”.

---

## Tester en local (optionnel)
Si vous souhaitez tester le build Pages avant publication:

```bash
cd frontend
# Utiliser l’URL backend publique (HTTPS)
REACT_APP_SOCKET_URL=https://poker06.eu.pythonanywhere.com npm run build
# Servir les fichiers statiques localement
npx serve build
```

Ouvrez l’URL affichée par `serve` et vérifiez la connexion Socket.IO depuis la page.

---

## Dépannage
- Mixed content / HTTPS:
  - GitHub Pages est servi en HTTPS. Assurez‑vous que le backend est aussi en HTTPS (c’est le cas avec PythonAnywhere) pour éviter les blocages navigateur.
- CORS:
  - Le backend doit autoriser les origines externes. Dans ce projet, Flask‑SocketIO est configuré avec `cors_allowed_origins="*"`.
- WebSockets indisponibles:
  - Sur certains hébergements, les WebSockets natifs peuvent être limités. Socket.IO retombe automatiquement sur le “polling”. L’app fonctionnera, avec des performances légèrement inférieures.
- 404 lors d’un rafraîchissement:
  - Le `404.html` (copie de `index.html`) couvre le fallback SPA côté Pages. Assurez‑vous que le build contient bien `build/404.html`.
- Chemins cassés en sous‑chemin `/repo`:
  - Le champ `homepage: "."` dans `package.json` garantit des chemins relatifs compatibles avec Pages.
- Cache Pages/Navigateurs:
  - En cas de changements non visibles, forcez un hard refresh (Ctrl/Cmd+Shift+R) ou purge du cache.

---

## Maintenance
- Mise à jour Node/CRA:
  - Le workflow utilise Node 18 (compat. react‑scripts 5). Si vous migrez vers une autre toolchain, adaptez `actions/setup-node` en conséquence.
- Changer l’URL backend:
  - Modifiez la variable `REACT_APP_SOCKET_URL` dans les “Variables” du dépôt. Un nouveau build suffira pour prendre en compte la nouvelle valeur.

---

## Référence: workflow (résumé)
Le fichier `.github/workflows/deploy-frontend.yml` exécute les étapes clés:

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '18'

- working-directory: frontend
  run: npm install

- working-directory: frontend
  env:
    REACT_APP_SOCKET_URL: ${{ vars.REACT_APP_SOCKET_URL || 'https://poker06.eu.pythonanywhere.com' }}
  run: npm run build

- uses: actions/upload-pages-artifact@v3
  with:
    path: frontend/build

- uses: actions/deploy-pages@v4
```

C’est tout: poussez sur `main` et votre frontend est publié automatiquement. Le backend reste accessible sur `https://poker06.eu.pythonanywhere.com`.
