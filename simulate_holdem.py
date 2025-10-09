import random

def simulate_holdem(num_simulations=10000):
    wins = 0

    for _ in range(num_simulations):
        # Simuler une situation de jeu (deux cartes en main et cinq sur la table)
        player_hand = random.sample(range(52), 2)  # 52 cartes dans un jeu standard
        table_cards = random.sample(set(range(52)) - set(player_hand), 5)

        # Simuler la main d'un adversaire (deux cartes en main et cinq sur la table)
        opponent_hand = random.sample(set(range(52)) - set(player_hand) - set(table_cards), 2)

        # Évaluation des mains et détermination du gagnant
        player_rank = evaluate_hand(player_hand + table_cards)
        opponent_rank = evaluate_hand(opponent_hand + table_cards)

        if player_rank < opponent_rank:
            wins += 1

    win_probability = wins / num_simulations
    return win_probability

# Exemple d'utilisation
probability = simulate_holdem()
print(f"Probabilité de gagner : {probability:.2%}")