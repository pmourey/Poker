# Migration vers Frontend React + Intégration Flask/Socket.IO — Détails

Ce document résume concrètement ce qui a été fait pour intégrer une application React au projet Poker existant (Flask + Socket.IO), ainsi que les impacts, le flux d’événements et les prochains pas recommandés.

## Objectif
- Séparer l’UI (client web) de la logique serveur.
- Utiliser React pour une meilleure gestion d’état client et une expérience temps réel basée sur Socket.IO.
- Garantir la confidentialité des cartes privées (chaque joueur ne voit que sa main).

## Résumé des changements
- Ajout d’un frontend React sous `frontend/` (Create React App).
- Câblage Socket.IO entre Flask et React, avec proxy de dev pour websocket.
- Sécurisation des diffusions: suppression d’envoi de cartes privées dans les broadcasts "généraux"; envoi des mains via rooms privées par joueur.
- Ajout d’une UI React minimale permettant de créer/rejoindre une partie, démarrer une main, voir l’état, et jouer des actions (check/call/raise/fold).
- Documentation de lancement mise à jour dans `README.md` (section Frontend React).

## Détails par fichier

### Backend (Flask)
- `app.py`
  - Connexion Socket.IO: lors de `connect`, chaque client rejoint automatiquement une "room" personnelle basée sur `session['player_id']` (via `join_room(player_id)`). Cela permet d’envoyer des événements privés (`hand_dealt`) exclusivement au joueur concerné.
  - Événement `start_game`:
    - Diffusion d’une mise à jour générale unique (`game_update`) à la room de la partie — sans révéler de mains privées.
    - Envoi des cartes privées via `hand_dealt` dans la room personnelle de chaque joueur.
  - Événement `player_action`:
    - Après traitement de l’action (fold/call/raise/check), diffusion d’une unique `game_update` générale à la room de la partie (toujours sans mains privées).
  - Remarque: la sérialisation de l’état (`to_dict`) masque par défaut les mains des autres joueurs; la diffusion générale n’utilise pas l’ID courant afin d’éviter toute fuite.

Aucun nouveau endpoint REST n’a été ajouté: la communication temps réel passe par Socket.IO, déjà présent dans le projet.

### Frontend (React)
- `frontend/package.json`
  - Ajout de la dépendance: `socket.io-client`.
  - Ajout du proxy CRA: `"proxy": "http://localhost:5000"` pour relayer les WebSockets vers Flask en dev, sans CORS.
- `frontend/src/socket.js`
  - Nouveau client Socket.IO unique réutilisable, connecté via la même origine (bénéficie du proxy CRA).
- `frontend/src/App.js`
  - Remplacement de l’app de démo par une UI de Poker minimaliste:
    - Lobby: créer une partie (avec nom), rejoindre une partie (avec nom + ID).
    - In-game: affichage phase, pot, board, main privée, liste des joueurs et joueur courant.
    - Actions: check, call, raise (montant), fold; démarrer une main; quitter.
  - Abonnements aux événements: `game_created`, `game_joined`, `game_started`, `hand_dealt`, `game_update`, `left_game`, `error`.
- `README.md`
  - Nouvelle section "Frontend React (intégration avec Flask)" avec prérequis et commandes pour lancer backend (port 5000) et frontend (port 3000).

## Flux des événements Socket.IO
- Côté client → serveur:
  - `create_game` { player_name }
  - `join_game` { player_name, game_id }
  - `start_game` { game_id }
  - `player_action` { game_id, action, amount? }
  - `leave_game` { game_id }
- Côté serveur → client:
  - `game_created` { game_id, player_id }
  - `game_joined` { game_id, player_id }
  - `game_started`
  - `game_update` { état général sans mains privées }
  - `hand_dealt` { hand } (émis vers la room personnelle du joueur)
  - `left_game`
  - `error` { message }

## Confidentialité et sécurité
- Les cartes privées ne sont plus jamais présentes dans les diffusions globales (`game_update`).
- Chaque joueur reçoit sa main via `hand_dealt` dans une room privée (ID = `player_id`).
- Le proxy CRA permet d’utiliser la même origine en dev, simplifiant la gestion des cookies de session Flask.

## Compatibilité et coexistence
- Les templates existants (`templates/index.html`, `templates/game.html`) restent en place côté Flask; le frontend React fonctionne en parallèle sur http://localhost:3000 en développement.
- En production, on pourra soit builder le frontend et le servir via Flask (dossier `build/` statique), soit utiliser un reverse proxy (Nginx) — à décider.

## Lancement et test (voir `README.md`)
- Backend: `python3 start_server.py` (port 5000).
- Frontend: `cd frontend && npm install && npm start` (port 3000).
- Test rapide: ouvrir deux onglets, créer une partie dans l’un (récupérer l’ID), rejoindre avec l’autre, démarrer une main et jouer des actions.

## Quality gates
- Build Python (syntaxe `app.py`): PASS.
- Lint/Typecheck: N/A (non configurés dans le repo au moment de la migration).
- Tests unitaires: N/A (non présents); validation manuelle via smoke test.

## Prochaines étapes suggérées
- Ajouter une page d’accueil React (routing) et/ou remplacer les templates Flask pour une UI unifiée.
- Exposer des endpoints REST complémentaires (ex: liste des parties) si besoin hors temps réel.
- Gérer `connect_error` / reconnexion côté client pour plus de robustesse.
- Mettre en place des tests end-to-end légers (Playwright/Cypress) pour le flux principal.
- Préparer le build de production du frontend et son intégration (Flask static ou reverse proxy).

