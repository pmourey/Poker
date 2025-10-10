#!/usr/bin/env python3
"""
Tests rapides pour vérifier la rotation du bouton (dealer_pos), l'attribution des blinds (SB/BB)
et l'ordre de parole préflop/postflop, pour 2 puis 3 joueurs.

Exécution:
  python test_blinds.py

Sortie: affiche PASS/FAIL pour chaque sous-test et renvoie un code de sortie 0 si tout est OK.
"""
from __future__ import annotations
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import PokerGame  # type: ignore


def assert_equal(actual, expected, label: str, errors: list[str]):
    if actual != expected:
        errors.append(f"{label}: expected {expected}, got {actual}")


def expected_positions(n: int, dealer_pos: int) -> tuple[int, int, int, int]:
    """Retourne (dealer, sb, bb, utg) en supposant que tous les joueurs sont éligibles.
    utg = joueur après BB (premier à parler préflop).
    """
    dealer = dealer_pos % n
    sb = (dealer + 1) % n
    bb = (sb + 1) % n
    utg = (bb + 1) % n
    return dealer, sb, bb, utg


def inspect_blinds(game: PokerGame) -> tuple[int | None, int | None]:
    """Détecte les index SB et BB d'après les mises courantes immédiatement après start_hand()."""
    sb_idx = None
    bb_idx = None
    # Chercher SB (mise == small_blind) et BB (mise == current_bet), en supposant stacks suffisants
    for i, p in enumerate(game.players):
        if p.current_bet == game.small_blind:
            sb_idx = i
        if p.current_bet == game.current_bet and p.current_bet > 0:
            # En début de main, current_bet doit être la BB
            bb_idx = i
    return sb_idx, bb_idx


def test_two_players() -> list[str]:
    errors: list[str] = []
    game = PokerGame(id="t2")
    game.add_player("p1", "Alice")
    game.add_player("p2", "Bob")

    n = len(game.players)
    # Main 1
    ok = game.start_hand()
    if not ok:
        errors.append("2P: start_hand() a échoué pour la main 1")
        return errors
    dealer, sb_exp, bb_exp, utg_exp = expected_positions(n, dealer_pos=0)
    # dealer_pos ne tourne pas pour la première main (reste 0)
    assert_equal(game.dealer_pos, dealer, "2P H1 dealer_pos", errors)
    sb_idx, bb_idx = inspect_blinds(game)
    assert_equal(sb_idx, sb_exp, "2P H1 SB index", errors)
    assert_equal(bb_idx, bb_exp, "2P H1 BB index", errors)
    assert_equal(game.current_player, utg_exp, "2P H1 UTG (ordre de parole préflop)", errors)

    # Vérifier ordre postflop: après flop(), le premier à parler est à gauche du bouton
    game.flop()
    postflop_first = (game.dealer_pos + 1) % n
    assert_equal(game.current_player, postflop_first, "2P H1 premier à parler postflop (BB en heads-up)", errors)

    # Main 2
    ok = game.start_hand()
    if not ok:
        errors.append("2P: start_hand() a échoué pour la main 2")
        return errors
    # dealer tourne de 1 (de 0 -> 1)
    dealer, sb_exp, bb_exp, utg_exp = expected_positions(n, dealer_pos=1)
    assert_equal(game.dealer_pos, dealer, "2P H2 dealer_pos", errors)
    sb_idx, bb_idx = inspect_blinds(game)
    assert_equal(sb_idx, sb_exp, "2P H2 SB index", errors)
    assert_equal(bb_idx, bb_exp, "2P H2 BB index", errors)
    assert_equal(game.current_player, utg_exp, "2P H2 UTG (ordre de parole préflop)", errors)

    game.flop()
    postflop_first = (game.dealer_pos + 1) % n
    assert_equal(game.current_player, postflop_first, "2P H2 premier à parler postflop (BB en heads-up)", errors)

    return errors


def test_three_players() -> list[str]:
    errors: list[str] = []
    game = PokerGame(id="t3")
    game.add_player("p1", "Alice")
    game.add_player("p2", "Bob")
    game.add_player("p3", "Carol")

    n = len(game.players)

    # Main 1
    ok = game.start_hand()
    if not ok:
        errors.append("3P: start_hand() a échoué pour la main 1")
        return errors
    # dealer initial = 0
    dealer, sb_exp, bb_exp, utg_exp = expected_positions(n, dealer_pos=0)
    assert_equal(game.dealer_pos, dealer, "3P H1 dealer_pos", errors)
    sb_idx, bb_idx = inspect_blinds(game)
    assert_equal(sb_idx, sb_exp, "3P H1 SB index", errors)
    assert_equal(bb_idx, bb_exp, "3P H1 BB index", errors)
    assert_equal(game.current_player, utg_exp, "3P H1 UTG (ordre de parole préflop)", errors)

    game.flop()
    postflop_first = (game.dealer_pos + 1) % n
    assert_equal(game.current_player, postflop_first, "3P H1 premier à parler postflop (SB en 3+)", errors)

    # Main 2
    ok = game.start_hand()
    if not ok:
        errors.append("3P: start_hand() a échoué pour la main 2")
        return errors
    dealer, sb_exp, bb_exp, utg_exp = expected_positions(n, dealer_pos=1)
    assert_equal(game.dealer_pos, dealer, "3P H2 dealer_pos", errors)
    sb_idx, bb_idx = inspect_blinds(game)
    assert_equal(sb_idx, sb_exp, "3P H2 SB index", errors)
    assert_equal(bb_idx, bb_exp, "3P H2 BB index", errors)
    assert_equal(game.current_player, utg_exp, "3P H2 UTG (ordre de parole préflop)", errors)

    game.flop()
    postflop_first = (game.dealer_pos + 1) % n
    assert_equal(game.current_player, postflop_first, "3P H2 premier à parler postflop (SB en 3+)", errors)

    # Main 3
    ok = game.start_hand()
    if not ok:
        errors.append("3P: start_hand() a échoué pour la main 3")
        return errors
    dealer, sb_exp, bb_exp, utg_exp = expected_positions(n, dealer_pos=2)
    assert_equal(game.dealer_pos, dealer, "3P H3 dealer_pos", errors)
    sb_idx, bb_idx = inspect_blinds(game)
    assert_equal(sb_idx, sb_exp, "3P H3 SB index", errors)
    assert_equal(bb_idx, bb_exp, "3P H3 BB index", errors)
    assert_equal(game.current_player, utg_exp, "3P H3 UTG (ordre de parole préflop)", errors)

    game.flop()
    postflop_first = (game.dealer_pos + 1) % n
    assert_equal(game.current_player, postflop_first, "3P H3 premier à parler postflop (SB en 3+)", errors)

    return errors


def main() -> int:
    all_errors: list[str] = []
    print("🧪 Test blinds & dealer: 2 joueurs...")
    errs = test_two_players()
    if errs:
        for e in errs:
            print("❌", e)
    else:
        print("✅ 2 joueurs: OK")
    all_errors.extend(errs)

    print("\n🧪 Test blinds & dealer: 3 joueurs...")
    errs = test_three_players()
    if errs:
        for e in errs:
            print("❌", e)
    else:
        print("✅ 3 joueurs: OK")
    all_errors.extend(errs)

    if all_errors:
        print(f"\n❌ ECHOUÉ — {len(all_errors)} erreur(s)")
        return 1
    print("\n✅ SUCCÈS — Tous les tests sont verts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
