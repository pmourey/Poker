#!/usr/bin/env python3
"""
Script de démarrage pour l'application de poker multi-joueur Flask
"""

import subprocess
import sys
import os


def install_requirements():
    """Installer les dépendances nécessaires"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dépendances installées avec succès")
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de l'installation des dépendances")
        return False
    return True


def main():
    print("🃏 Démarrage de l'application de Poker Multi-joueur 🃏")
    print("=" * 50)

    # Vérifier si on est dans le bon répertoire
    if not os.path.exists('app.py'):
        print("❌ Erreur: app.py non trouvé. Assurez-vous d'être dans le bon répertoire.")
        return

    # Installer les dépendances
    if not install_requirements():
        return

    # Charger les variables d'environnement depuis un fichier .env s'il est présent
    try:
        from dotenv import load_dotenv
        load_dotenv()  # charge .env à la racine du projet
        print("📦 Variables d'environnement chargées depuis .env (si présent)")
    except Exception as e:
        # Ne pas bloquer si python-dotenv n'est pas dispo, mais l'installation ci-dessus devrait l'ajouter
        print(f"ℹ️ Impossible de charger .env automatiquement: {e}")

    # Paramètres d'écoute
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    print(f"\n🚀 Démarrage du serveur Flask...")
    print(f"📱 Ouvrez votre navigateur sur: http://{host if host not in ('0.0.0.0', '::') else 'localhost'}:{port}")
    print("🔄 Pour arrêter le serveur, utilisez Ctrl+C\n")

    try:
        # Démarrer l'application Flask
        from app import app, socketio
        socketio.run(app, debug=True, allow_unsafe_werkzeug=True, host=host, port=port)
    except KeyboardInterrupt:
        print("\n👋 Serveur arrêté par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")


if __name__ == '__main__':
    main()
