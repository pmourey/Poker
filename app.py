from flask import Flask, render_template, session, redirect, url_for, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import uuid
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum
import os

app = Flask(__name__)
# Lire le secret depuis l’env, avec fallback pour dev
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'poker-secret-key-2023')

# Configuration SocketIO basique
# NOTE: en production WSGI (ex: PythonAnywhere), préférez async_mode='threading' pour le polling
SOCKETIO_ASYNC_MODE = os.environ.get('SOCKETIO_ASYNC_MODE', 'threading')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=SOCKETIO_ASYNC_MODE)

# Dossier du build React (Option B)
BUILD_DIR = os.path.join(os.path.dirname(__file__), 'frontend', 'build')

# Global games storage
games: Dict[str, 'PokerGame'] = {}
# Mapping joueur -> partie
player_game_mapping = {}

# Constantes pour les cartes
suits = ['D', 'H', 'S', 'C']
card_values = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

NEXT_HAND_DELAY_SECONDS = int(os.environ.get('NEXT_HAND_DELAY_SECONDS', '4'))

@dataclass
class Card:
    value: int
    suit: str

    def __copy__(self):
        return Card(self.value, self.suit)

    def __repr__(self):
        return f'{card_values[self.value - 2]}{self.suit}'

    def __eq__(self, other):
        return self.suit == other.suit and self.value == other.value

    def __hash__(self):
        return hash((self.value, self.suit))

class GamePhase(Enum):
    WAITING = "waiting"
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"

@dataclass
class PokerPlayer:
    id: str
    name: str
    stack: int
    hand: List[Card] = field(default_factory=list)
    current_bet: int = 0
    total_bet: int = 0
    folded: bool = False
    all_in: bool = False
    connected: bool = True
    has_acted: bool = False

    def to_dict(self, hide_hand=True):
        return {
            'id': self.id,
            'name': self.name,
            'stack': self.stack,
            'current_bet': self.current_bet,
            'total_bet': self.total_bet,
            'folded': self.folded,
            'all_in': self.all_in,
            'connected': self.connected,
            'hand': [str(card) for card in self.hand] if not hide_hand else [],
            # Nouveau: indique si le joueur peut miser dans l'état courant
            'can_bet': (self.stack > 0 and not self.folded and not self.all_in)
        }

@dataclass
class PokerGame:
    id: str
    players: List[PokerPlayer] = field(default_factory=list)
    deck: List[Card] = field(default_factory=list)
    community_cards: List[Card] = field(default_factory=list)
    pot: int = 0
    current_bet: int = 0
    phase: GamePhase = GamePhase.WAITING
    dealer_pos: int = 0
    current_player: int = 0
    small_blind: int = 10
    big_blind: int = 20
    max_players: int = 6
    last_winner: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.create_deck()

    def create_deck(self):
        self.deck = [Card(value, suit) for suit in suits for value in range(2, 15)]
        random.shuffle(self.deck)

    def add_player(self, player_id: str, name: str, buy_in: int = 1000):
        if len(self.players) >= self.max_players:
            return "game_full"

        # PROTECTION: Rejeter automatiquement les noms générés automatiquement
        if name.startswith('Joueur') and len(name) > 6 and name[6:].isdigit():
            print(f"[ADD_PLAYER] REJETÉ: Nom automatique détecté '{name}' pour {player_id}")
            return "invalid_name"

        print(f"[ADD_PLAYER] Tentative d'ajout: {player_id} ({name})")
        print(f"[ADD_PLAYER] Joueurs actuels: {[(p.id, p.name, p.connected) for p in self.players]}")

        # Vérifier si le joueur existe déjà (reconnexion)
        existing_player = None
        for player in self.players:
            if player.id == player_id:
                existing_player = player
                break

        if existing_player:
            # Joueur existant qui se reconnecte
            existing_player.connected = True
            existing_player.name = name  # Mettre à jour le nom au cas où
            print(f"[ADD_PLAYER] RECONNEXION: {name} ({player_id}) reconnecté")
            return "reconnected"

        # Nouveau joueur
        player = PokerPlayer(
            id=player_id,
            name=name,
            stack=buy_in
        )
        self.players.append(player)
        print(f"[ADD_PLAYER] SUCCESS: {name} ({player_id}) ajouté. Total: {len(self.players)} joueurs")
        print(f"[ADD_PLAYER] Liste finale: {[(p.id, p.name) for p in self.players]}")
        return "added"

    def remove_player(self, player_id: str):
        self.players = [p for p in self.players if p.id != player_id]

    def start_hand(self):
        # Empêcher de démarrer s'il n'y a pas 2 joueurs capables de miser
        eligible = [p for p in self.players if p.stack > 0 and p.connected]
        if len(eligible) < 2:
            return False

        self.create_deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.phase = GamePhase.PREFLOP

        # Reset player states
        for player in self.players:
            player.hand = []
            player.current_bet = 0
            player.total_bet = 0
            # Marquer comme inactif ceux qui ne peuvent pas miser pour cette main
            if player.stack <= 0 or not player.connected:
                player.folded = True
                player.all_in = True
            else:
                player.folded = False
                player.all_in = False
            player.has_acted = False

        # Deal cards uniquement aux joueurs actifs
        for _ in range(2):
            for player in self.players:
                if not player.folded and not player.all_in:
                    player.hand.append(self.deck.pop())

        # Post blinds
        self.post_blinds()

        # Si à ce stade tous les joueurs actifs sont all-in, fast-forward jusqu'au showdown
        try:
            self.fast_forward_all_in_to_showdown()
        except AttributeError:
            # Fallback inline (dans le cas où une ancienne classe est chargée)
            if self.all_active_all_in():
                if self.phase == GamePhase.PREFLOP:
                    self.flop()
                if self.phase == GamePhase.FLOP:
                    self.turn()
                if self.phase == GamePhase.TURN:
                    self.river()
                self.showdown()

        return True

    def post_blinds(self):
        # Calculer les positions de blinds parmi les joueurs éligibles
        eligible_indices = [i for i, p in enumerate(self.players) if not p.folded and not p.all_in and p.stack > 0 and p.connected]
        if len(eligible_indices) < 2:
            return

        # Trouver le prochain index éligible après dealer_pos pour SB et BB
        def next_eligible(start_idx):
            n = len(self.players)
            idx = (start_idx + 1) % n
            for _ in range(n):
                if idx in eligible_indices:
                    return idx
                idx = (idx + 1) % n
            return eligible_indices[0]

        small_blind_pos = next_eligible(self.dealer_pos)
        big_blind_pos = next_eligible(small_blind_pos)

        # Small blind
        sb_player = self.players[small_blind_pos]
        sb_amount = min(self.small_blind, sb_player.stack)
        sb_player.current_bet = sb_amount
        sb_player.total_bet += sb_amount
        sb_player.stack -= sb_amount
        if sb_player.stack == 0:
            sb_player.all_in = True
        self.pot += sb_amount

        # Big blind
        bb_player = self.players[big_blind_pos]
        bb_amount = min(self.big_blind, bb_player.stack)
        bb_player.current_bet = bb_amount
        bb_player.total_bet += bb_amount
        bb_player.stack -= bb_amount
        if bb_player.stack == 0:
            bb_player.all_in = True
        self.pot += bb_amount

        # La mise courante est la contribution du BB (peut être partielle si all-in)
        self.current_bet = bb_player.current_bet
        # Le joueur suivant au BB
        self.current_player = next_eligible(big_blind_pos)

    def is_betting_round_complete(self) -> bool:
        """Le tour est complet si tous les joueurs actifs (non fold) ont AGI dans ce tour
        et soit ont égalisé la mise courante (current_bet), soit sont all-in."""
        active = [p for p in self.players if not p.folded]
        if len(active) <= 1:
            return True
        for p in active:
            if p.all_in:
                continue
            # Doit avoir agi et égalisé la mise
            if not p.has_acted or p.current_bet != self.current_bet:
                return False
        return True

    def all_active_all_in(self) -> bool:
        active = [p for p in self.players if not p.folded]
        return len(active) > 0 and all(p.all_in for p in active)

    def advance_phase_after_betting_if_needed(self):
        """Avancer d'une phase si le tour est complet. Si tous les joueurs actifs sont all-in,
        avancer automatiquement jusqu'au river/showdown."""
        # Avancer d'au moins une phase si tour complet
        if self.is_betting_round_complete():
            if self.phase == GamePhase.PREFLOP:
                self.flop()
            elif self.phase == GamePhase.FLOP:
                self.turn()
            elif self.phase == GamePhase.TURN:
                self.river()
            elif self.phase == GamePhase.RIVER:
                self.showdown()

            # Si tout le monde est all-in après l'avancement, fast-forward jusqu'au showdown
            while self.phase in (GamePhase.PREFLOP, GamePhase.FLOP, GamePhase.TURN) and self.all_active_all_in():
                if self.phase == GamePhase.PREFLOP:
                    self.flop()
                elif self.phase == GamePhase.FLOP:
                    self.turn()
                elif self.phase == GamePhase.TURN:
                    self.river()
            if self.phase == GamePhase.RIVER and self.all_active_all_in():
                self.showdown()

    def next_phase(self):
        if self.phase == GamePhase.PREFLOP:
            self.flop()
        elif self.phase == GamePhase.FLOP:
            self.turn()
        elif self.phase == GamePhase.TURN:
            self.river()
        elif self.phase == GamePhase.RIVER:
            self.showdown()

    def flop(self):
        self.phase = GamePhase.FLOP
        self.deck.pop()  # Burn card
        for _ in range(3):
            self.community_cards.append(self.deck.pop())
        self.reset_betting_round()

    def turn(self):
        self.phase = GamePhase.TURN
        self.deck.pop()  # Burn card
        self.community_cards.append(self.deck.pop())
        self.reset_betting_round()

    def river(self):
        self.phase = GamePhase.RIVER
        self.deck.pop()  # Burn card
        self.community_cards.append(self.deck.pop())
        self.reset_betting_round()

    def reset_betting_round(self):
        self.current_bet = 0
        for player in self.players:
            player.current_bet = 0
            player.has_acted = False
        # Trouver le premier joueur éligible (à partir du small blind)
        start = (self.dealer_pos + 1) % len(self.players) if self.players else 0
        idx = start
        for _ in range(len(self.players)):
            if not self.players[idx].folded and not self.players[idx].all_in:
                self.current_player = idx
                break
            idx = (idx + 1) % len(self.players)
        else:
            self.current_player = start

    def showdown(self):
        """Gérer la phase de showdown: déterminer le gagnant et stocker le résultat sans préparer la main suivante ici."""
        self.phase = GamePhase.SHOWDOWN
        active_players = [p for p in self.players if not p.folded]
        if active_players:
            winner = active_players[0]
            amount = self.pot
            winner.stack += self.pot
            self.last_winner = {
                'player_id': winner.id,
                'name': winner.name,
                'amount': amount,
                'reason': 'showdown'
            }
            print(f"Fin de main - Gagnant: {winner.name}, pot: {self.pot}")
            self.pot = 0
        else:
            self.last_winner = {}
        return True

    def prepare_next_hand(self):
        """Préparer la main suivante si possible"""
        # Vérifier combien de joueurs peuvent encore jouer (avec jetons ET connectés)
        active_players = [p for p in self.players if p.stack > 0 and p.connected]

        print(f"Préparation main suivante - Joueurs avec jetons: {len(active_players)}")
        for p in self.players:
            print(f"  {p.name}: stack={p.stack}, connected={p.connected}")

        if len(active_players) < 2:
            # Pas assez de joueurs pour continuer
            self.phase = GamePhase.WAITING
            print(f"Jeu terminé - pas assez de joueurs actifs ({len(active_players)})")
            return False

        # Avancer le dealer vers le prochain joueur existant (même si broke, la position sera ajustée aux blinds)
        if self.players:
            self.dealer_pos = (self.dealer_pos + 1) % len(self.players)

        # Réinitialiser pour la main suivante
        self.phase = GamePhase.WAITING
        self.community_cards = []
        self.current_bet = 0

        # Reset des états des joueurs pour la main suivante
        for player in self.players:
            player.hand = []
            player.current_bet = 0
            player.total_bet = 0
            player.folded = False
            player.all_in = False

        print(f"Main suivante préparée - {len(active_players)} joueurs actifs")
        return True

    def start_new_hand(self):
        """Démarrer une nouvelle main automatiquement"""
        # Vérifier qu'on a assez de joueurs actifs
        active_players = [p for p in self.players if p.stack > 0 and p.connected]
        if len(active_players) < 2:
            print(f"Impossible de démarrer nouvelle main - seulement {len(active_players)} joueurs actifs")
            return False

        print(f"Démarrage nouvelle main avec {len(active_players)} joueurs")
        # Démarrer la nouvelle main
        return self.start_hand()

    def get_active_players(self):
        return [p for p in self.players if not p.folded and p.stack > 0]

    def to_dict(self, current_player_id=None):
        active_players = [p for p in self.players if p.stack > 0 and p.connected]
        return {
            'id': self.id,
            'players': [p.to_dict(hide_hand=(p.id != current_player_id)) for p in self.players],
            'community_cards': [str(card) for card in self.community_cards],
            'pot': self.pot,
            'current_bet': self.current_bet,
            'phase': self.phase.value,
            'current_player': self.current_player,
            'dealer_pos': self.dealer_pos,
            # Nouveau: le front peut désactiver le bouton "Démarrer une main"
            'can_start_new_hand': len(active_players) >= 2
        }

def cleanup_games():
    """Nettoyer les parties et supprimer les joueurs avec des noms automatiques"""
    global games, player_game_mapping

    print("🧹 Nettoyage des parties au démarrage...")

    games_to_remove = []
    players_removed = 0

    for game_id, game in games.items():
        # Supprimer les joueurs avec des noms automatiques (Joueur + chiffres)
        original_count = len(game.players)
        game.players = [
            p for p in game.players
            if not (p.name.startswith('Joueur') and p.name[6:].isdigit())
        ]
        players_removed += original_count - len(game.players)

        # Si la partie n'a plus de joueurs, la marquer pour suppression
        if len(game.players) == 0:
            games_to_remove.append(game_id)

    # Supprimer les parties vides
    for game_id in games_to_remove:
        del games[game_id]
        print(f"🗑️ Partie vide supprimée: {game_id}")

    # Nettoyer le mapping des joueurs
    player_game_mapping.clear()

    print(f"✅ Nettoyage terminé: {players_removed} joueurs automatiques supprimés, {len(games_to_remove)} parties vides supprimées")

@app.route('/')
def index():
    # Si le build React existe, le servir à la racine
    index_path = os.path.join(BUILD_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(BUILD_DIR, 'index.html')
    # Sinon, fallback sur le template existant
    return render_template('index.html')

# Servir les assets du build React si présents (sans capturer /socket.io/)
@app.route('/static/<path:filename>')
def react_static(filename):
    static_dir = os.path.join(BUILD_DIR, 'static')
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path):
        return send_from_directory(static_dir, filename)
    # 404 si non présent (la route Flask /static des templates n’est pas utilisée ici)
    return ('', 404)

@app.route('/manifest.json')
@app.route('/asset-manifest.json')
@app.route('/favicon.ico')
def react_assets():
    # Servir certains assets à la racine du build React
    requested = request.path.lstrip('/')
    file_path = os.path.join(BUILD_DIR, requested)
    if os.path.exists(file_path):
        return send_from_directory(BUILD_DIR, requested)
    return ('', 404)

@app.route('/healthz')
def healthz():
    return {'status': 'ok'}, 200

@app.route('/game/<game_id>')
def game(game_id):
    if game_id not in games:
        return redirect(url_for('index'))
    return render_template('game.html', game_id=game_id)

@socketio.on('connect')
def handle_connect():
    """Gérer la connexion d'un client"""
    if 'player_id' not in session:
        session['player_id'] = str(uuid.uuid4())

    player_id = session['player_id']
    # Joindre une room personnelle basée sur l'id du joueur pour les événements ciblés
    try:
        join_room(player_id)
    except Exception as e:
        print(f"[JOIN_ROOM] Erreur lors de la jonction de la room {player_id}: {e}")
    print(f"✅ Session connectée: {player_id}")

@socketio.on('disconnect')
def handle_disconnect():
    player_id = session.get('player_id')
    if player_id:
        # Mark player as disconnected in all games
        for game in games.values():
            for player in game.players:
                if player.id == player_id:
                    player.connected = False
        print(f"Session déconnectée: {player_id}")

@socketio.on('create_game')
def handle_create_game(data):
    player_id = session.get('player_id')
    if not player_id:
        # Fallback: générer un id de joueur et rejoindre sa room perso
        player_id = str(uuid.uuid4())
        session['player_id'] = player_id
        try:
            join_room(player_id)
        except Exception as e:
            print(f"[CREATE_GAME] join_room perso échoué pour {player_id}: {e}")

    player_name = data.get('player_name')

    # Vérifier que le nom du joueur est fourni (comme pour join_game)
    if not player_name or player_name.strip() == '':
        emit('error', {'message': 'Nom de joueur requis pour créer une partie'})
        return

    # Créer une nouvelle partie
    game_id = str(uuid.uuid4())[:8]
    game = PokerGame(id=game_id)
    games[game_id] = game

    # Ajouter le joueur créateur
    result = game.add_player(player_id, player_name.strip())

    if result in ["added", "reconnected"]:
        join_room(game_id)
        player_game_mapping[player_id] = game_id

        # Envoyer les événements au créateur
        emit('game_created', {'game_id': game_id, 'player_id': player_id})
        emit('game_joined', {'game_id': game_id, 'player_id': player_id})
        emit('game_update', game.to_dict(player_id))

        # Aussi envoyer à toute la room
        socketio.emit('game_update', game.to_dict(), room=game_id)
        print(f"PARTIE CRÉÉE: {player_name} ({player_id}) a créé la partie {game_id}")
    else:
        del games[game_id]
        emit('error', {'message': f'Erreur lors de la création: {result}'})

@socketio.on('join_game')
def handle_join_game(data):
    player_id = session.get('player_id')
    if not player_id:
        # Fallback session manquante: créer un id et rejoindre room perso
        player_id = str(uuid.uuid4())
        session['player_id'] = player_id
        try:
            join_room(player_id)
        except Exception as e:
            print(f"[JOIN_GAME] join_room perso échoué pour {player_id}: {e}")

    game_id = data['game_id']
    player_name = data.get('player_name')

    # Vérifier que le nom du joueur est fourni
    if not player_name or player_name.strip() == '':
        emit('error', {'message': 'Nom de joueur requis'})
        return

    if game_id not in games:
        emit('error', {'message': 'Partie non trouvée'})
        return

    game = games[game_id]

    # Vérifier si le joueur existe déjà dans cette partie
    existing_player = next((p for p in game.players if p.id == player_id), None)
    if existing_player:
        # Reconnexion d'un joueur existant
        existing_player.connected = True
        join_room(game_id)
        player_game_mapping[player_id] = game_id
        emit('game_joined', {'game_id': game_id, 'player_id': player_id})
        socketio.emit('game_update', game.to_dict(), room=game_id)
        print(f"RECONNEXION: {player_name} ({player_id}) s'est reconnecté à la partie {game_id}")
        return

    result = game.add_player(player_id, player_name.strip())

    if result in ["added", "reconnected"]:
        join_room(game_id)
        player_game_mapping[player_id] = game_id
        emit('game_joined', {'game_id': game_id, 'player_id': player_id})
        socketio.emit('game_update', game.to_dict(), room=game_id)
        print(f"NOUVEAU JOUEUR: {player_name} ({player_id}) a rejoint la partie {game_id}")
    elif result == "invalid_name":
        emit('error', {'message': 'Nom automatique détecté. Veuillez choisir un nom personnalisé.'})
        print(f"NOM REJETÉ: {player_name} ({player_id}) - nom automatique")
    else:
        emit('error', {'message': f'Impossible de rejoindre: {result}'})

@socketio.on('start_game')
def handle_start_game(data):
    game_id = data['game_id']

    if game_id not in games:
        emit('error', {'message': 'Partie non trouvée'})
        return

    game = games[game_id]

    # Empêcher le démarrage si moins de 2 joueurs peuvent miser
    eligible = [p for p in game.players if p.stack > 0 and p.connected]
    if len(eligible) < 2:
        emit('error', {'message': "Impossible de démarrer: pas assez de joueurs capables de miser"})
        socketio.emit('game_update', game.to_dict(), room=game_id)
        return

    if game.start_hand():
        socketio.emit('game_started', room=game_id)
        socketio.emit('game_update', game.to_dict(), room=game_id)
        for player in game.players:
            if player.hand:
                socketio.emit('hand_dealt', {
                    'hand': [str(card) for card in player.hand]
                }, room=player.id)
        # Message global + résultat si fin instantanée (all-in préflop)
        if game.phase == GamePhase.SHOWDOWN and game.last_winner:
            try:
                socketio.emit('table_message', {'text': 'All‑in — révélation automatique des cartes'}, room=game_id)
            except Exception as e:
                print(f"[EMIT] table_message (instant) error: {e}")
            try:
                socketio.emit('hand_result', game.last_winner, room=game_id)
            except Exception as e:
                print(f"[EMIT] hand_result (instant) error: {e}")
            try:
                socketio.start_background_task(schedule_next_hand, game_id, NEXT_HAND_DELAY_SECONDS)
            except Exception as e:
                print(f"[TASK] schedule_next_hand (instant) error: {e}")
        print(f"Partie {game_id} commencée")
    else:
        emit('error', {'message': "Impossible de démarrer: pas assez de joueurs capables de miser"})

@socketio.on('player_action')
def handle_player_action(data):
    game_id = data['game_id']
    action = data['action']
    amount = data.get('amount', 0)

    if game_id not in games:
        emit('error', {'message': 'Partie non trouvée'})
        return

    game = games[game_id]
    player_id = session.get('player_id')

    # Trouver le joueur
    current_player = None
    player_index = None
    for i, player in enumerate(game.players):
        if player.id == player_id:
            current_player = player
            player_index = i
            break

    if not current_player or current_player.folded:
        emit('error', {'message': 'Action impossible'})
        return

    # Interdire l'action si le joueur ne peut pas miser (stack 0 ou all-in)
    if current_player.stack <= 0 or current_player.all_in:
        emit('error', {'message': 'Vous ne pouvez plus miser dans cette main'})
        return

    if player_index != game.current_player:
        emit('error', {'message': "Ce n'est pas votre tour"})
        return

    # Traiter l'action
    if action == 'fold':
        current_player.folded = True
        current_player.has_acted = True
    elif action == 'call':
        call_amount = min(game.current_bet - current_player.current_bet, current_player.stack)
        current_player.current_bet += call_amount
        current_player.stack -= call_amount
        current_player.total_bet += call_amount
        current_player.has_acted = True
        if current_player.stack == 0:
            current_player.all_in = True
        game.pot += call_amount
    elif action == 'raise':
        if amount > 0:
            bet_amount = min(amount, current_player.stack)
            current_player.current_bet += bet_amount
            current_player.stack -= bet_amount
            current_player.total_bet += bet_amount
            current_player.has_acted = True
            if current_player.stack == 0:
                current_player.all_in = True
            game.pot += bet_amount
            game.current_bet = current_player.current_bet
            # Requérir une action à nouveau pour les autres joueurs actifs
            for p in game.players:
                if p.id != current_player.id and not p.folded and not p.all_in:
                    p.has_acted = False
    elif action == 'check':
        if game.current_bet > current_player.current_bet:
            emit('error', {'message': 'Vous devez suivre ou relancer'})
            return
        current_player.has_acted = True

    # Déterminer fin de main ou passage au joueur suivant / phase suivante
    active_players = [p for p in game.players if not p.folded]
    hand_ended = False
    all_in_auto = False
    if len(active_players) <= 1:
        # Fin de main par abandon des autres
        if active_players:
            winner = active_players[0]
            amount = game.pot
            winner.stack += game.pot
            game.pot = 0
            game.phase = GamePhase.SHOWDOWN
            game.last_winner = {
                'player_id': winner.id,
                'name': winner.name,
                'amount': amount,
                'reason': 'all_folded'
            }
        else:
            game.phase = GamePhase.SHOWDOWN
            game.last_winner = {}
        hand_ended = True
    else:
        # Si le tour d'enchères est complet, avancer de phase (et potentiellement fast-forward si all-in)
        if game.is_betting_round_complete():
            # Détecter si tout le monde est all-in avant d'avancer (sera utilisé pour message global)
            became_all_in = game.all_active_all_in()
            game.advance_phase_after_betting_if_needed()
            if game.phase == GamePhase.SHOWDOWN and game.last_winner:
                hand_ended = True
                if became_all_in:
                    all_in_auto = True
        else:
            # Passer au joueur suivant en sautant ceux qui sont fold/all-in
            game.current_player = (game.current_player + 1) % len(game.players)
            while game.players[game.current_player].folded or game.players[game.current_player].all_in:
                game.current_player = (game.current_player + 1) % len(game.players)

    # Notifications et mises à jour
    if hand_ended:
        # Message global si la fin résulte d'un all-in auto reveal
        if all_in_auto:
            try:
                socketio.emit('table_message', {'text': 'All‑in — révélation automatique des cartes'}, room=game_id)
            except Exception as e:
                print(f"[EMIT] table_message error: {e}")
        # Informer du gagnant
        try:
            socketio.emit('hand_result', game.last_winner, room=game_id)
        except Exception as e:
            print(f"[EMIT] hand_result error: {e}")
        # Planifier la prochaine main
        try:
            socketio.start_background_task(schedule_next_hand, game_id, NEXT_HAND_DELAY_SECONDS)
        except Exception as e:
            print(f"[TASK] schedule_next_hand error: {e}")
    else:
        socketio.emit('game_update', game.to_dict(), room=game_id)

@socketio.on('leave_game')
def handle_leave_game(data):
    game_id = data['game_id']
    player_id = session.get('player_id')

    if game_id not in games:
        emit('error', {'message': 'Partie non trouvée'})
        return

    game = games[game_id]
    game.remove_player(player_id)

    if player_id in player_game_mapping:
        del player_game_mapping[player_id]

    leave_room(game_id)
    emit('left_game', {'message': 'Vous avez quitté la partie'})
    socketio.emit('game_update', game.to_dict(), room=game_id)
    print(f"Joueur {player_id} a quitté la partie {game_id}")

def schedule_next_hand(game_id: str, delay: int = None):
    """Attendre un délai avant de préparer et éventuellement démarrer la prochaine main."""
    d = delay if delay is not None else NEXT_HAND_DELAY_SECONDS
    try:
        socketio.sleep(d)
    except Exception as e:
        print(f"[SLEEP] erreur: {e}")
    game = games.get(game_id)
    if not game:
        return
    # Préparer la main suivante puis éventuellement la démarrer automatiquement
    if game.prepare_next_hand():
        if game.start_new_hand():
            socketio.emit('game_started', room=game_id)
            socketio.emit('game_update', game.to_dict(), room=game_id)
            for player in game.players:
                if player.hand:
                    socketio.emit('hand_dealt', {
                        'hand': [str(card) for card in player.hand]
                    }, room=player.id)
            # Si la nouvelle main se termine instantanément (all-in), message + résultat + replanifier
            if game.phase == GamePhase.SHOWDOWN and game.last_winner:
                try:
                    socketio.emit('table_message', {'text': 'All‑in — révélation automatique des cartes'}, room=game_id)
                except Exception as e:
                    print(f"[EMIT] table_message (auto) error: {e}")
                try:
                    socketio.emit('hand_result', game.last_winner, room=game_id)
                except Exception as e:
                    print(f"[EMIT] hand_result (auto) error: {e}")
                try:
                    socketio.start_background_task(schedule_next_hand, game_id, NEXT_HAND_DELAY_SECONDS)
                except Exception as e:
                    print(f"[TASK] schedule_next_hand (chain) error: {e}")
        else:
            socketio.emit('game_update', game.to_dict(), room=game_id)
    else:
        socketio.emit('game_update', game.to_dict(), room=game_id)

# Nettoyage des parties et joueurs fantômes au démarrage
cleanup_games()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
