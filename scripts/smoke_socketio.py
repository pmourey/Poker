#!/usr/bin/env python3
"""
Smoke test Socket.IO (polling-only) contre le serveur local Flask-SocketIO.

Scénario:
- Client A (Alice) se connecte et crée une partie => récupère game_id
- Client B (Bob) se connecte et rejoint la partie
- Client A démarre la partie
- Les deux clients doivent recevoir: game_update + hand_dealt (et game_started broadcast)

Configuration:
- Lis SMOKE_SERVER_URL depuis l'env (défaut: http://127.0.0.1:5000)
- Lis SMOKE_TIMEOUT (secondes) depuis l'env (défaut: 15)

Retour:
- Code 0 si succès, !=0 sinon
"""
import os
import sys
import time
import threading

try:
    import socketio  # python-socketio (client)
except Exception as e:
    print(f"python-socketio non installé: {e}")
    sys.exit(1)

SERVER_URL = os.environ.get('SMOKE_SERVER_URL', 'http://127.0.0.1:5000')
TIMEOUT = float(os.environ.get('SMOKE_TIMEOUT', '15'))

# Événements de synchronisation
created_evt = threading.Event()
joined_evt = threading.Event()
started_evt = threading.Event()
hand_a_evt = threading.Event()
hand_b_evt = threading.Event()

result = {
    'game_id': None,
    'alice': {'connected': False, 'hand': None},
    'bob': {'connected': False, 'hand': None},
}

# Créer deux clients Socket.IO en polling-only
cA = socketio.Client(reconnection=True)
cB = socketio.Client(reconnection=True)

# Handlers communs

def bind_handlers(client_name: str, client: socketio.Client):
    @client.event
    def connect():
        result[client_name]['connected'] = True
        print(f"[{client_name}] connected")

    @client.event
    def disconnect():
        print(f"[{client_name}] disconnected")

    @client.on('game_update')
    def on_game_update(payload):
        # Peu verbeux; confirme juste réception
        print(f"[{client_name}] game_update: phase={payload.get('phase')} players={len(payload.get('players', []))}")

    @client.on('hand_dealt')
    def on_hand_dealt(payload):
        hand = payload.get('hand')
        result[client_name]['hand'] = hand
        print(f"[{client_name}] hand_dealt: {hand}")
        if client_name == 'alice':
            hand_a_evt.set()
        else:
            hand_b_evt.set()

    @client.on('game_started')
    def on_game_started(_payload=None):
        print(f"[{client_name}] game_started")
        started_evt.set()

    @client.on('game_created')
    def on_game_created(payload):
        gid = payload.get('game_id')
        result['game_id'] = gid
        print(f"[{client_name}] game_created: {gid}")
        created_evt.set()

    @client.on('game_joined')
    def on_game_joined(payload):
        gid = payload.get('game_id')
        print(f"[{client_name}] game_joined: {gid}")
        joined_evt.set()

# Binder les handlers
bind_handlers('alice', cA)
bind_handlers('bob', cB)

# Connexion en polling-only
try:
    print(f"[main] Connecting clients to {SERVER_URL} (polling-only)…")
    cA.connect(SERVER_URL, transports=['polling'], wait=True, wait_timeout=TIMEOUT)
    cB.connect(SERVER_URL, transports=['polling'], wait=True, wait_timeout=TIMEOUT)
except Exception as e:
    print(f"Echec de connexion clients: {e}")
    sys.exit(2)

# Étape 1: Alice crée une partie
try:
    cA.emit('create_game', {'player_name': 'Alice'})
    if not created_evt.wait(TIMEOUT):
        print("Timeout en attente de game_created")
        raise TimeoutError
    game_id = result['game_id']
    if not game_id:
        print("game_id manquant après création")
        raise RuntimeError
except Exception:
    cA.disconnect(); cB.disconnect()
    sys.exit(3)

# Étape 2: Bob rejoint la partie
try:
    cB.emit('join_game', {'game_id': game_id, 'player_name': 'Bob'})
    if not joined_evt.wait(TIMEOUT):
        print("Timeout en attente de game_joined pour Bob")
        raise TimeoutError
except Exception:
    cA.disconnect(); cB.disconnect()
    sys.exit(4)

# Petit délai pour laisser les updates arriver
time.sleep(0.5)

# Étape 3: Alice démarre la partie
try:
    cA.emit('start_game', {'game_id': game_id})
    if not started_evt.wait(TIMEOUT):
        print("Timeout en attente de game_started")
        raise TimeoutError
    # Chaque joueur doit recevoir sa main
    if not hand_a_evt.wait(TIMEOUT):
        print("Timeout en attente de hand_dealt pour Alice")
        raise TimeoutError
    if not hand_b_evt.wait(TIMEOUT):
        print("Timeout en attente de hand_dealt pour Bob")
        raise TimeoutError
except Exception:
    cA.disconnect(); cB.disconnect()
    sys.exit(5)

# Succès
print("\nSMOKE TEST OK ✅")
print(f"game_id={game_id}")
print(f"Alice hand: {result['alice']['hand']}")
print(f"Bob hand: {result['bob']['hand']}")

# Nettoyage
cA.disconnect()
cB.disconnect()

sys.exit(0)

