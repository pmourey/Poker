#!/usr/bin/env python3
"""
Test rapide pour vérifier que la correction anti-duplication fonctionne
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import PokerGame

def test_no_duplicates():
    """Test que l'ajout de joueurs ne crée plus de doublons"""
    print("🧪 Test de la correction anti-duplication...")

    # Créer une partie de test
    game = PokerGame(id="test123")

    # Tester l'ajout normal
    result1 = game.add_player("player1", "Alice")
    print(f"Ajout 1: {result1} - Joueurs: {len(game.players)}")

    # Tenter d'ajouter le même joueur (devrait nettoyer et re-ajouter)
    result2 = game.add_player("player1", "Alice")
    print(f"Ajout 2 (même joueur): {result2} - Joueurs: {len(game.players)}")

    # Vérifier qu'il n'y a qu'un seul joueur
    player_ids = [p.id for p in game.players]
    duplicates = len(player_ids) - len(set(player_ids))

    print(f"📊 Résultats:")
    print(f"  - Total joueurs: {len(game.players)}")
    print(f"  - Doublons détectés: {duplicates}")
    print(f"  - IDs uniques: {len(set(player_ids))}")

    if duplicates == 0 and len(game.players) == 1:
        print("✅ SUCCÈS: Aucun doublon détecté!")
        return True
    else:
        print("❌ ÉCHEC: Des doublons persistent!")
        return False

if __name__ == "__main__":
    success = test_no_duplicates()
    sys.exit(0 if success else 1)
