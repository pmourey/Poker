import re
from time import perf_counter

import random

from dataclasses import dataclass

from typing import List, Optional

import sys
import math


def idebug(*args):
    return
    print(*args, file=sys.stderr)


def debug(*args):
    # return
    print(*args, file=sys.stderr)


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
        # Utilisez une combinaison de hachages des attributs
        return hash((self.value, self.suit))


@dataclass
class Player:
    id: int
    stack: int
    chip_in_pot: int
    hand: List[Card] = None
    last_action: str = ''

    def __repr__(self):
        player: str = 'ME' if self.id == player_id else 'OP'
        return f'{player} #{self.id} - last action = {self.last_action} stack: {self.stack} - chip_in_pot: {self.chip_in_pot}'

    def get_numeric_hand(self) -> List[int]:
        return [i for i, c in deck.items() if c in self.hand]

    def evaluate_hand(self, table_cards: List[Card], list_functions: List) -> int:
        cards: List[Card] = table_cards + player.hand
        winning_hands = [f for f in list_functions if f(cards) is not None]
        return max(winning_hands, key=lambda f: f(cards)) if winning_hands else None


def simulate_holdem(players: List[Player]):
    wins = 0
    player = players[player_id]
    opponents = [p for p in players if p.id != player_id]
    player_num_hand = player.get_numeric_hand()

    i = 0
    while perf_counter() - tic < MAX_TIME_OUT / 1000:
        # Simuler une situation de jeu (deux cartes en main et cinq sur la table)
        # table_cards = random.sample(list(set(range(52)) - set(player_num_hand)), 5)
        # board_cards = [deck[i] for i in table_cards]
        # Simuler la main d'un adversaire (deux cartes en main et cinq sur la table)
        new_table_cards = table_cards
        new_board_cards = board_cards
        if len(table_cards) < 5:
            new_cards: List[int] = random.sample(list(set(range(52)) - set(player_num_hand) - set(new_table_cards)), 2)
            new_table_cards += new_cards
            new_board_cards += [deck[i] for i in new_cards]
        reserved_cards = set()
        for opponent in opponents:
            opponent_num_hand = random.sample(
                list(set(range(52)) - set(player_num_hand) - set(new_table_cards) - reserved_cards), 2)
            reserved_cards |= set(opponent_num_hand)
            opponent.hand = [deck[i] for i in opponent_num_hand]

        # Évaluation des mains et détermination du gagnant
        player_score = player.evaluate_hand(new_board_cards, list_functions)
        best_opponent_score = max([p.evaluate_hand(new_board_cards, list_functions) for p in opponents])
        if player_score > best_opponent_score:
            wins += 1
        i += 1

    win_probability = wins / i
    return win_probability, i


def longest_consecutive_sequence(nums):
    if not nums:
        return []

    nums_set = set(nums)
    longest_sequence = []

    for num in nums:
        if num - 1 not in nums_set:  # Start of a new sequence
            current_sequence = [num]
            current_num = num + 1

            while current_num in nums_set:
                current_sequence.append(current_num)
                current_num += 1

            # Update the longest sequence if needed
            if len(current_sequence) > len(longest_sequence):
                longest_sequence = current_sequence

    return longest_sequence[-5:]


def all_cards_in_table(cards_sets: List[tuple]):
    for t in cards_sets:
        for c in t:
            if c in player.hand:
                return False
    return True


def switch_ace(values: List[int]) -> List[int]:
    new_values: List[int] = []
    for v in values:
        new_values += [1] if v == 14 else [v]
    return new_values


def strait_flush(cards: List[Card]) -> float:
    """Straight of the same suit"""
    success = 1000
    for s in suits:
        values: List[int] = [c.value for c in cards if c.suit == s]
        sequence: List[int] = longest_consecutive_sequence(values)
        if len(sequence) == 5:
            return success  # + sequence[-1]
        sequence: List[int] = longest_consecutive_sequence(switch_ace(values))
        if len(sequence) == 5:
            return success  # + sequence[-1]


def get_four_of_a_kind(cards: List[Card]) -> List[tuple]:
    """Four cards of the same value"""
    four_of_a_kind: List[tuple] = []
    for v in range(len(card_values)):
        cards_candidates = [c for c in cards if c.value == v + 2]
        if len(cards_candidates) == 4:
            four_of_a_kind.append(tuple(cards_candidates))
    return four_of_a_kind


def four_of_a_kind(cards: List[Card]) -> float:
    success = 900
    four_sets = get_four_of_a_kind(cards)
    if len(four_sets) >= 1 and not all_cards_in_table(four_sets):
        return success


def full_house(cards: List[Card]) -> float:
    """	Combination of three of a kind and a pair"""
    success = 800
    three_sets: List[tuple] = get_three_of_a_kind(cards)
    pairs: List[tuple] = get_pairs(cards)
    for pair in pairs:
        for three_set in three_sets:
            cards = [pair] + [three_set]
            if not all_cards_in_table(cards):
                return success


def flush(cards: List[Card]) -> float:
    """5 cards of the same suit, not in sequential order"""
    success = 700
    for s in suits:
        cards_candidates = [c for c in cards if c.suit == s]
        s1, s2 = set(cards_candidates), set(board_cards)
        cards_in_table = s1 - s2
        if len(cards_candidates) == 5 and len(cards_in_table) != 5:
            return success


def straight(cards: List[Card]) -> float:
    """Sequence of 5 cards in increasing value (Ace can precede 2 and follow up King), not of the same suit"""
    success = 600
    values = list(set([c.value for c in cards]))
    sequence: List[int] = longest_consecutive_sequence(values)
    if len(sequence) == 5:
        return success  # + sequence[-1]
    sequence: List[int] = longest_consecutive_sequence(switch_ace(values))
    if len(sequence) == 5:
        return success  # + sequence[-1]


# def all_three_sets_in_table(three_sets: List[tuple]):
#     for c1, c2, c3 in three_sets:
#         if c1 in player.hand or c2 in player.hand or c3 in player.hand:
#             return False
#     return True


def get_three_of_a_kind(cards: List[Card]) -> List[tuple]:
    """Three cards with the same value"""
    three_sets: List[tuple] = []
    for v in range(1, len(card_values) + 1):
        cards_candidates = [c for c in cards if c.value == v]
        if len(cards_candidates) == 3:
            three_sets.append(tuple(cards_candidates))
    return three_sets


def three_of_a_kind(cards: List[Card]) -> float:
    three_sets = get_three_of_a_kind(cards)
    if len(three_sets) >= 1 and not all_cards_in_table(three_sets):
        return 500


# def all_pairs_in_table(pairs: List[tuple]):
#     for c1, c2 in pairs:
#         if c1 in player.hand or c2 in player.hand:
#             return False
#     return True


def get_pairs(cards: List[Card]) -> List[tuple]:
    """Two times two cards with the same value"""
    pairs: List[tuple] = []
    for v in range(len(card_values)):
        cards_candidates = [c for c in cards if c.value == v + 2]
        if len(cards_candidates) == 2:
            pairs.append(tuple(cards_candidates))
    return pairs


def two_pairs(cards: List[Card]) -> float:
    pairs = get_pairs(cards)
    if len(pairs) >= 2 and not all_cards_in_table(pairs):
        return 400


def one_pair(cards: List[Card]) -> float:
    success = 300
    pairs = get_pairs(cards)
    if len(pairs) >= 1 and not all_cards_in_table(pairs):
        bonus: int = pairs[0][0].value - 13 # don't fold if I own a pair of (J, Q, Q, A)
        return success + bonus


def high_card(cards: List[Card]) -> float:
    """	Simple value of the card. Lowest: 2 – Highest: Ace (King in the example)"""
    success = 200
    highest_card: Card = max(cards, key=lambda c: c.value)
    if highest_card.value == 14 and highest_card not in board_cards:
        return success  # + highest_card_value


def game_state(table_cards_count):
    if table_cards_count == 0:
        return 'PREFLOP'
    elif table_cards_count == 3:
        return 'FLOP'
    elif table_cards_count == 4:
        return 'TURN'
    else:
        return 'RIVER'


def get_bet_action(actions: List[str]) -> Optional[int]:
    pattern = re.compile(r"BET")
    list_actions = [a for a in actions if pattern.search(a)]
    if list_actions:
        bet_action = list_actions[0]
        return int(bet_action.split('_')[1])

def detect_duplicate_cards(cards: List[str]):
    duplicates = set()
    uniq_cards = set()
    for card in cards:
        if card in uniq_cards:
            duplicates.add(card)
        else:
            uniq_cards.add(card)
    return list(duplicates)

# Auto-generated code below aims at helping you parse
# the standard input according to the problem statement.

small_blind = int(input())  # initial small blind's value
idebug(small_blind)
big_blind = int(input())  # initial big blind's value
idebug(big_blind)
hand_nb_by_level = int(input())  # number of hands to play to reach next level
idebug(hand_nb_by_level)
level_blind_multiplier = int(input())  # blinds are multiply by this coefficient when the level changes
idebug(level_blind_multiplier)
buy_in = int(input())  # initial stack for each player
idebug(buy_in)
first_big_blind_id = int(input())  # id of the first big blind player
idebug(first_big_blind_id)
player_nb = int(input())  # number of players (2 to 4)
idebug(player_nb)
player_id = int(input())  # your id
idebug(player_id)

suits = ['D', 'H', 'S', 'C']
card_values = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

list_functions: List = [strait_flush, four_of_a_kind, full_house, flush, straight, three_of_a_kind, two_pairs, one_pair,
                        high_card]

deck = {13 * i + j: Card(value=j + 2, suit=s) for i, s in enumerate(['D', 'H', 'S', 'C']) for j in range(13)}

played_cards: List[Card] = []

is_start = True
MAX_TIME_OUT = 1000

# game loop
while True:
    _round = int(input())  # referee round (starts at 1-game ends when it reaches 600)
    idebug(_round)

    tic = perf_counter()

    hand_nb = int(input())  # hand number (starts at 1)
    idebug(hand_nb)

    players: List[Player] = []
    for i in range(player_nb):
        # stack: number of chips in the player's stack
        # chip_in_pot: number of player's chips in the pot
        stack, chip_in_pot = [int(j) for j in input().split()]
        idebug(stack, chip_in_pot)
        players.append(Player(i, stack, chip_in_pot))

    board_cards = input()  # board cards (example : AD_QH_2S_X_X)
    idebug(board_cards)
    player_cards = input()  # your cards (example : TC_JH)
    idebug(player_cards)

    action_nb = int(input())  # number of actions since your last turn
    idebug(action_nb)

    for i in range(action_nb):
        line = input()
        idebug(line)
        inputs = line.split()
        action_round = int(inputs[0])  # round of the action
        # debug(f'action_round = {action_round}')
        action_hand_nb = int(inputs[1])  # hand number of the action
        action_player_id = int(inputs[2])  # player id of the action
        action = inputs[3]  # action (examples : BET_200, FOLD, NONE...)
        action_board_cards = inputs[4]  # board cards when the action is done (example : AD_QH_2S_4H_X)
        players[action_player_id].last_action = action

    show_down_nb = int(input())  # number of hands that ended since your last turn
    idebug(show_down_nb)
    for i in range(show_down_nb):
        line = input()
        idebug(line)
        inputs = line.split()
        show_down_hand_nb = int(inputs[0])  # hand number
        show_down_board_cards = inputs[1]  # board cards at the showdown
        show_down_player_cards = inputs[2]  # players cards (example : QH_3S_E_E_5C_H_7D_KC player0's cards, followed by player1's cards ...)

    possible_action_nb = int(input())  # number of actions you can do
    idebug(possible_action_nb)

    possible_actions = []
    for i in range(possible_action_nb):
        possible_action = input()  # your possible action (BET_240 means 240 is the minimum raise but you can bet more)
        idebug(possible_action)
        possible_actions.append(possible_action)

    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)

    # try to count cards (useless here :-( played cards are resubmitted before end of deck)
    if show_down_nb:
        # 4H_7H_4C_TS_9H 6C_9S_QS_5C_KH_6D
        for v in show_down_board_cards.split('_'):
            if v not in ('X', 'E'):
                played_cards.append(Card(*conv(v)))
        for v in show_down_player_cards.split('_'):
            if v not in ('X', 'E'):
                played_cards.append(Card(*conv(v)))
    debug(f'{len(played_cards)} played cards: {played_cards}')
    duplicate_cards: List[str] = detect_duplicate_cards(played_cards)
    debug(f'{len(duplicate_cards)} duplicate played cards: {duplicate_cards}')
    if len(played_cards) >= 52:
        played_cards.clear()

    player: Player = players[player_id]

    conv = lambda v: (card_values.index(v[0]) + 2, v[1])
    board_cards = [Card(*conv(v)) for v in board_cards.split('_') if v != 'X']
    table_cards: List[int] = [i for i, c in deck.items() if c in board_cards]
    player.hand = [Card(*conv(v)) for v in player_cards.split('_') if v != 'X']

    visible_cards: List[Card] = board_cards + player.hand

    list_functions: List = [strait_flush, four_of_a_kind, full_house, flush, straight, three_of_a_kind, two_pairs, one_pair, high_card]
    winning_hands = [f for f in list_functions if f(visible_cards) is not None]

    best_hand = max(winning_hands, key=lambda f: f(visible_cards)) if winning_hands else None
    # player_score = player.evaluate_hand(board_cards, list_functions)
    player_score = best_hand(visible_cards) if best_hand else 0

    if best_hand:
        debug(f'best hand: {best_hand.__name__} - score: {player_score}')

    # win_probability, num_iterations = simulate_holdem(players=players)
    # debug(f'win probability: {win_probability:.2%} - num_iteration = {num_iterations}')

    if is_start:
        MAX_TIME_OUT = 49
        is_start = False

    debug(f'players = {players}')

    bluffing_players: List[Player] = [p for p in players if
                                      p.id < player_id and ('BET' in p.last_action or 'ALL-IN' in p.last_action)]
    debug(f'bluffing players = {bluffing_players}')

    # MESSAGE = f'$0 {win_probability:.0%} - {best_hand.__name__}: {player_score}'
    bluffing_player: Player = None
    all_in_player: Player = None
    max_bet = 0
    for p in bluffing_players:
        if p.last_action == 'ALL-IN':
            all_in_player = p
        else:
            bet_amount: int = int(p.last_action.split('_')[1])
            if bet_amount > max_bet:
                bluffing_player = p
                max_bet = bet_amount
    bluffing_player = bluffing_player if not all_in_player else all_in_player

    MESSAGE = f'${player_id} - {best_hand.__name__}' if best_hand else f'You bluff, ${bluffing_player.id}! :-D' if bluffing_player else f'${player_id} is bored :-d'
    FOLD_MESSAGE = f"${player_id} rage quits"
    state = game_state(len(board_cards))
    debug(f'state = {state} - score: {player_score}')
    debug(f'possible_actions = {possible_actions}')
    if player_score < 200:
        if state == 'RIVER':
            action = f"FOLD;{FOLD_MESSAGE}"
        elif 'CHECK' in possible_actions:
            action = f"CHECK;{MESSAGE}"
        elif 'CALL' in possible_actions and not all_in_player:
            action = f"CALL;{MESSAGE}"
        else:
            action = f"FOLD;{FOLD_MESSAGE}"
    elif player_score < 400:
        if 'CALL' in possible_actions:
            if state == 'RIVER' and player_score > 300: # does not fold if I have a pair of (J, Q, K, A)
                action = f"CALL;{MESSAGE}"
            else:
                action = f"FOLD;{FOLD_MESSAGE}"
        elif get_bet_action(possible_actions):
            amount = get_bet_action(possible_actions)
            action = f"BET {amount};{MESSAGE}"
        else:
            action = f"FOLD;{FOLD_MESSAGE}"
    elif player_score < 600:
        if get_bet_action(possible_actions):
            amount = max(get_bet_action(possible_actions), player.stack // 2)
            action = f"BET {amount};{MESSAGE}"
        else:
            action = f"CALL;{MESSAGE}"
    else:
        action = f"ALL_IN;{MESSAGE}"

    debug(f'elapsed time = {round((perf_counter() - tic) * 1000, 2)} ms')
    print(action)
