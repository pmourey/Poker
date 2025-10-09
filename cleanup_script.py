#!/usr/bin/env python3
"""
Script de nettoyage complet pour supprimer toutes les données locales
qui pourraient contenir les anciens noms automatiques de joueurs.
"""

import os
import shutil
import json
import sqlite3
import glob
from pathlib import Path

class PokerCleanup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.cleanup_log = []

    def log(self, message):
        """Ajouter un message au log de nettoyage"""
        print(f"🧹 {message}")
        self.cleanup_log.append(message)

    def clean_cache_files(self):
        """Supprimer tous les fichiers de cache Python"""
        self.log("Nettoyage des fichiers de cache Python...")

        # Supprimer __pycache__
        pycache_dirs = glob.glob(str(self.project_root / "**" / "__pycache__"), recursive=True)
        for cache_dir in pycache_dirs:
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                self.log(f"Supprimé: {cache_dir}")

        # Supprimer les fichiers .pyc
        pyc_files = glob.glob(str(self.project_root / "**" / "*.pyc"), recursive=True)
        for pyc_file in pyc_files:
            if os.path.exists(pyc_file):
                os.remove(pyc_file)
                self.log(f"Supprimé: {pyc_file}")

    def clean_session_data(self):
        """Supprimer les données de session Flask"""
        self.log("Nettoyage des données de session Flask...")

        # Fichiers de session Flask (si présents)
        session_patterns = [
            "flask_session*",
            "session*",
            "*.session",
            "sessions/*"
        ]

        for pattern in session_patterns:
            files = glob.glob(str(self.project_root / pattern))
            for file_path in files:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    self.log(f"Supprimé fichier de session: {file_path}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    self.log(f"Supprimé dossier de session: {file_path}")

    def clean_database_files(self):
        """Supprimer les fichiers de base de données locaux"""
        self.log("Nettoyage des bases de données locales...")

        db_patterns = [
            "*.db",
            "*.sqlite",
            "*.sqlite3",
            "database/*",
            "data/*.db*"
        ]

        for pattern in db_patterns:
            files = glob.glob(str(self.project_root / pattern))
            for file_path in files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.log(f"Supprimé base de données: {file_path}")

    def clean_json_data_files(self):
        """Supprimer les fichiers JSON contenant des données de jeu"""
        self.log("Nettoyage des fichiers JSON de données...")

        json_patterns = [
            "games_data.json",
            "players_data.json",
            "game_state*.json",
            "poker_data*.json",
            "data/*.json",
            "saves/*.json"
        ]

        for pattern in json_patterns:
            files = glob.glob(str(self.project_root / pattern))
            for file_path in files:
                if os.path.exists(file_path):
                    # Vérifier si le fichier contient des anciens noms automatiques
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'Joueur' in content and any(f'Joueur{i}' in content for i in range(1, 100)):
                                os.remove(file_path)
                                self.log(f"Supprimé fichier JSON avec anciens noms: {file_path}")
                    except Exception as e:
                        # Si on ne peut pas lire le fichier, le supprimer par sécurité
                        os.remove(file_path)
                        self.log(f"Supprimé fichier JSON non lisible: {file_path}")

    def clean_log_files(self):
        """Supprimer les fichiers de logs"""
        self.log("Nettoyage des fichiers de logs...")

        log_patterns = [
            "*.log",
            "logs/*",
            "poker.log*",
            "flask.log*",
            "debug.log*"
        ]

        for pattern in log_patterns:
            files = glob.glob(str(self.project_root / pattern))
            for file_path in files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.log(f"Supprimé fichier de log: {file_path}")

    def clean_temp_files(self):
        """Supprimer les fichiers temporaires"""
        self.log("Nettoyage des fichiers temporaires...")

        temp_patterns = [
            "*.tmp",
            "*.temp",
            "temp/*",
            "tmp/*",
            ".DS_Store",
            "Thumbs.db",
            "*.bak",
            "*.backup"
        ]

        for pattern in temp_patterns:
            files = glob.glob(str(self.project_root / pattern))
            for file_path in files:
                if os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        self.log(f"Supprimé fichier temporaire: {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        self.log(f"Supprimé dossier temporaire: {file_path}")

    def clean_browser_cache(self):
        """Nettoyer les données de cache du navigateur (côté serveur)"""
        self.log("Nettoyage des données de cache navigateur...")

        # Supprimer les fichiers de cache statiques si présents
        static_cache_patterns = [
            "static/cache/*",
            "templates/.cache/*",
            ".webassets-cache/*"
        ]

        for pattern in static_cache_patterns:
            files = glob.glob(str(self.project_root / pattern))
            for file_path in files:
                if os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    self.log(f"Supprimé cache navigateur: {file_path}")

    def clean_venv_if_requested(self, clean_venv=False):
        """Nettoyer l'environnement virtuel si demandé"""
        if clean_venv:
            self.log("Nettoyage de l'environnement virtuel...")
            venv_dirs = [".venv", "venv", "env"]

            for venv_dir in venv_dirs:
                venv_path = self.project_root / venv_dir
                if venv_path.exists():
                    shutil.rmtree(venv_path)
                    self.log(f"Supprimé environnement virtuel: {venv_path}")

    def reset_game_state_in_code(self):
        """Réinitialiser les variables globales dans le code (si possible)"""
        self.log("Vérification du code pour réinitialisation des variables globales...")

        try:
            # Importer l'application pour réinitialiser les variables globales
            import sys
            app_path = str(self.project_root)
            if app_path not in sys.path:
                sys.path.insert(0, app_path)

            # Réinitialiser les variables globales si l'app est importable
            try:
                import app
                if hasattr(app, 'games'):
                    app.games.clear()
                    self.log("Variables globales de jeu réinitialisées")
                if hasattr(app, 'player_game_mapping'):
                    app.player_game_mapping.clear()
                    self.log("Mapping joueur-partie réinitialisé")
            except ImportError:
                self.log("Impossible d'importer l'application (normal si dépendances manquantes)")

        except Exception as e:
            self.log(f"Erreur lors de la réinitialisation du code: {e}")

    def create_gitignore_for_data(self):
        """Créer/mettre à jour .gitignore pour ignorer les fichiers de données"""
        self.log("Mise à jour du .gitignore...")

        gitignore_path = self.project_root / ".gitignore"

        data_patterns = [
            "# Données de jeu locales",
            "*.db",
            "*.sqlite*",
            "games_data.json",
            "players_data.json",
            "game_state*.json",
            "poker_data*.json",
            "",
            "# Cache et temporaires",
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            "*.tmp",
            "*.temp",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# Logs",
            "*.log",
            "logs/",
            "",
            "# Sessions Flask",
            "flask_session*",
            "session*",
            "*.session",
            "",
            "# Environnement virtuel",
            ".venv/",
            "venv/",
            "env/",
        ]

        existing_content = ""
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

        # Ajouter seulement les patterns qui ne sont pas déjà présents
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            f.write("\n# Ajouté par le script de nettoyage\n")
            for pattern in data_patterns:
                if pattern not in existing_content:
                    f.write(f"{pattern}\n")

        self.log("Fichier .gitignore mis à jour")

    def run_complete_cleanup(self, clean_venv=False):
        """Exécuter un nettoyage complet"""
        print("🧹 DÉBUT DU NETTOYAGE COMPLET 🧹")
        print("=" * 50)

        # Exécuter tous les nettoyages
        self.clean_cache_files()
        self.clean_session_data()
        self.clean_database_files()
        self.clean_json_data_files()
        self.clean_log_files()
        self.clean_temp_files()
        self.clean_browser_cache()
        self.clean_venv_if_requested(clean_venv)
        self.reset_game_state_in_code()
        self.create_gitignore_for_data()

        print("\n" + "=" * 50)
        print("✅ NETTOYAGE TERMINÉ")
        print(f"📋 {len(self.cleanup_log)} actions effectuées")

        # Afficher un résumé
        print("\n📊 RÉSUMÉ DU NETTOYAGE:")
        for action in self.cleanup_log:
            print(f"  • {action}")

        print("\n🎯 RECOMMANDATIONS POST-NETTOYAGE:")
        print("  1. Redémarrez votre serveur de développement")
        print("  2. Videz le cache de votre navigateur (Ctrl+F5)")
        print("  3. Vérifiez que les nouvelles protections fonctionnent")
        print("  4. Les anciens noms automatiques ne devraient plus apparaître")

def main():
    """Fonction principale avec interface interactive"""
    cleanup = PokerCleanup()

    print("🃏 SCRIPT DE NETTOYAGE COMPLET - POKER APP 🃏")
    print("=" * 50)
    print("Ce script va supprimer toutes les données locales qui")
    print("pourraient contenir des anciens noms automatiques.")
    print()

    # Demander confirmation
    response = input("Voulez-vous continuer ? (o/N): ").lower().strip()
    if response not in ['o', 'oui', 'y', 'yes']:
        print("❌ Nettoyage annulé")
        return

    # Demander si on veut nettoyer l'environnement virtuel
    clean_venv = False
    venv_response = input("\nVoulez-vous aussi supprimer l'environnement virtuel (.venv) ? (o/N): ").lower().strip()
    if venv_response in ['o', 'oui', 'y', 'yes']:
        clean_venv = True
        print("⚠️  L'environnement virtuel sera supprimé. Vous devrez le recréer.")

    print()

    # Exécuter le nettoyage
    cleanup.run_complete_cleanup(clean_venv)

    print("\n🎉 Nettoyage terminé avec succès !")
    if clean_venv:
        print("\n📝 N'oubliez pas de recréer votre environnement virtuel:")
        print("   python -m venv .venv")
        print("   source .venv/bin/activate  # sur macOS/Linux")
        print("   pip install -r requirements.txt")

if __name__ == '__main__':
    main()
