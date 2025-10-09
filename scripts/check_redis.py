#!/usr/bin/env python3
"""Petit script de vérification de connexion Redis.
- Lit REDIS_URL depuis l'environnement (format recommandé: rediss://user:pass@host:port/0)
- Fait un set/get pour vérifier la connectivité
"""
import os
import sys
from pathlib import Path

# Charger automatiquement le .env du projet (utile si lancé depuis PyCharm)
try:
    from dotenv import load_dotenv
    # 1) Essayer le .env courant
    loaded = load_dotenv()
    # 2) Sinon, viser explicitement la racine du projet (../.env depuis scripts/)
    if not loaded:
        project_root = Path(__file__).resolve().parents[1]
        dotenv_path = project_root / '.env'
        if dotenv_path.exists():
            load_dotenv(dotenv_path)
except Exception:
    # Ne pas bloquer si python-dotenv n'est pas dispo; on s'en remet aux variables d'env
    pass

try:
    import redis
except Exception as e:
    print(f"redis non installé: {e}")
    sys.exit(1)

url = os.environ.get('REDIS_URL')
if not url:
    print("REDIS_URL non défini. Exemple: rediss://default:<password>@<host>:<port>/0")
    sys.exit(2)


def try_connect(u: str) -> bool:
    r = redis.from_url(u, decode_responses=True)
    ok = r.set('poker:health', 'ok')
    if not ok:
        print("SET a retourné False")
        return False
    val = r.get('poker:health')
    print(f"Redis OK, valeur lue: {val}")
    return True

try:
    if try_connect(url):
        sys.exit(0)
    else:
        sys.exit(3)
except Exception as e:
    msg = str(e)
    if 'WRONG_VERSION_NUMBER' in msg and url.startswith('rediss://'):
        # Fallback en non‑TLS si le serveur n'attend pas TLS sur ce port
        alt = 'redis://' + url[len('rediss://'):]
        print("Avertissement: TLS a échoué (WRONG_VERSION_NUMBER). Tentative en non‑TLS…")
        try:
            if try_connect(alt):
                print("Suggestion: mettez à jour REDIS_URL en redis:// si votre instance n'exige pas TLS.")
                sys.exit(0)
        except Exception as e2:
            print(f"Echec fallback non‑TLS: {e2}")
    print(f"Erreur connexion Redis: {e}")
    sys.exit(4)
