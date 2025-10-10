# filepath: /Users/display/PycharmProjects/Poker/hand_eval.py
from typing import List, Dict, Tuple, Any

# Réutilisable avec tout objet possédant des attributs .value (2..14) et .suit ('D','H','S','C')

CARD_LABELS_FR = {
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: '10',
    11: 'Valet', 12: 'Dame', 13: 'Roi', 14: 'As'
}

HandRank = Tuple[int, Tuple]  # (category, tie-break tuple)

# Catégories (ordre croissant)
HIGH_CARD = 0
ONE_PAIR = 1
TWO_PAIR = 2
THREE_OF_A_KIND = 3
STRAIGHT = 4
FLUSH = 5
FULL_HOUSE = 6
FOUR_OF_A_KIND = 7
STRAIGHT_FLUSH = 8
ROYAL_FLUSH = 9


def longest_consecutive_sequence(values: List[int]) -> List[int]:
    if not values:
        return []
    s = set(values)
    best: List[int] = []
    for v in s:
        if v - 1 not in s:
            cur = [v]
            w = v + 1
            while w in s:
                cur.append(w)
                w += 1
            if len(cur) > len(best):
                best = cur
    return best


def straight_high(values: List[int]) -> int:
    """Retourne la plus haute carte d'une suite, 0 si aucune. Prend en charge l'As bas (A-2-3-4-5)."""
    uniq = sorted(set(values))
    # Cas particulier: A-2-3-4-5 (As bas)
    if {14, 2, 3, 4, 5}.issubset(uniq):
        return 5
    # Général
    best = 0
    run = 1
    for i in range(1, len(uniq)):
        if uniq[i] == uniq[i - 1] + 1:
            run += 1
        else:
            run = 1
        if run >= 5:
            best = uniq[i]
    return best


def straight_flush_high(cards: List[Any]) -> int:
    by_suit: Dict[str, List[int]] = {}
    for c in cards:
        by_suit.setdefault(c.suit, []).append(c.value)
    best = 0
    for suit, vals in by_suit.items():
        if len(vals) < 5:
            continue
        hi = straight_high(vals)
        if hi >= 10 and {10, 11, 12, 13, 14}.issubset(set(vals)):
            return 14  # quinte royale (gérée séparément mais utile pour tri)
        best = max(best, hi)
    return best


def evaluate_7cards(cards: List[Any]) -> Tuple[HandRank, str]:
    """Évalue les 7 cartes: retourne ((cat, tie), nom_fr)."""
    # Comptes par valeur et par couleur
    counts: Dict[int, int] = {}
    by_suit: Dict[str, List[int]] = {}
    for c in cards:
        counts[c.value] = counts.get(c.value, 0) + 1
        by_suit.setdefault(c.suit, []).append(c.value)

    values_sorted = sorted(counts.keys(), reverse=True)

    # Quinte flush / Royale
    sf_hi = 0
    sf_suit_best = None
    for suit, vals in by_suit.items():
        if len(vals) < 5:
            continue
        hi = straight_high(vals)
        if hi > sf_hi:
            sf_hi = hi
            sf_suit_best = suit
    if sf_hi >= 5:
        # Quinte royale si 10-J-Q-K-A dans la même couleur
        is_royal = False
        if sf_suit_best is not None:
            svals = set(by_suit[sf_suit_best])
            is_royal = {10, 11, 12, 13, 14}.issubset(svals)
        if is_royal:
            return ((ROYAL_FLUSH, ()), 'Quinte royale')
        return ((STRAIGHT_FLUSH, (sf_hi,)), f"Quinte flush (hauteur {CARD_LABELS_FR.get(sf_hi, str(sf_hi))})")

    # Carré
    four = [v for v, c in counts.items() if c == 4]
    if four:
        v4 = max(four)
        kicker = max(v for v in values_sorted if v != v4)
        name = f"Carré d'{CARD_LABELS_FR[v4]}" if v4 == 14 else f"Carré de {CARD_LABELS_FR[v4]}"
        return ((FOUR_OF_A_KIND, (v4, kicker)), name)

    # Full
    trips = sorted([v for v, c in counts.items() if c == 3], reverse=True)
    pairs = sorted([v for v, c in counts.items() if c == 2], reverse=True)
    if trips and (len(trips) >= 2 or pairs):
        t = trips[0]
        p = pairs[0] if pairs else trips[1]
        return ((FULL_HOUSE, (t, p)), f"Full ({CARD_LABELS_FR[t]} par {CARD_LABELS_FR[p]})")

    # Couleur
    flush_vals: List[int] = []
    for suit, vals in by_suit.items():
        if len(vals) >= 5:
            flush_vals = sorted(vals, reverse=True)[:5]
            break
    if flush_vals:
        name = f"Couleur ({', '.join(CARD_LABELS_FR[v] for v in flush_vals)})"
        return ((FLUSH, tuple(flush_vals)), name)

    # Suite (quinte)
    st_hi = straight_high(list(counts.keys()))
    if st_hi >= 5:
        return ((STRAIGHT, (st_hi,)), f"Suite (hauteur {CARD_LABELS_FR.get(st_hi, str(st_hi))})")

    # Brelan
    if trips:
        t = trips[0]
        kickers = [v for v in values_sorted if v != t][:2]
        return ((THREE_OF_A_KIND, (t, *kickers)), f"Brelan de {CARD_LABELS_FR[t]}")

    # Deux paires
    if len(pairs) >= 2:
        p1, p2 = pairs[:2]
        kicker = next((v for v in values_sorted if v not in (p1, p2)), 0)
        return ((TWO_PAIR, (p1, p2, kicker)), f"Deux paires ({CARD_LABELS_FR[p1]} et {CARD_LABELS_FR[p2]})")

    # Paire
    if len(pairs) == 1:
        p = pairs[0]
        kickers = [v for v in values_sorted if v != p][:3]
        return ((ONE_PAIR, (p, *kickers)), f"Paire de {CARD_LABELS_FR[p]}")

    # Carte haute
    top5 = sorted(values_sorted, reverse=True)[:5]
    return ((HIGH_CARD, tuple(top5)), f"Carte haute {CARD_LABELS_FR[top5[0]]}")


def evaluate_best(cards: List[Any]) -> Dict[str, Any]:
    """Wrapper: calcule et renvoie un dict {category, key, name}."""
    key, name = evaluate_7cards(cards)
    return {
        'category': key[0],
        'key': key,
        'name': name,
    }

