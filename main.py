"""
===============================================================================
Project   : Hibi_BuRe
Module    : main.py
Created   : 13.02.2026
Author    : Florian
Purpose   : main application entry point for the Hibi-BuBe Report Application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

import sys
import argparse
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from src.data.database_manager import DatabaseManager
from src.gui.main_window import MainWindow
from src.config.settings import set_cli_options, init_settings


def setup_logging(log_level: str, log_file: Path):
    """
    Configure logging for the application.

    :param log_level: Log level (DEBUG, INFO, WARNING, ERROR)
    :type log_level: str
    :param log_file: Path to log file
    :type log_file: Path
    """
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.ERROR)

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {log_level.upper()} level")
    logger.info(f"Log file: {log_file}")


def parse_arguments():
    """
    Parse command line arguments.

    :return: Parsed arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description='Hibi-BuBe Report Generator - Erweiterte Auswertungen für Hibiscus',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s                          # Standard (Jameica-Config aus ~/.jameica)
  %(prog)s --env                    # Nutze .env Datei (neben AppImage oder im Projekt)
  %(prog)s --d /custom/path         # Jameica-Config aus /custom/path
  %(prog)s --d /custom/path --env   # .env aus /custom/path
  %(prog)s --log-level debug        # Debug-Logging aktivieren
  %(prog)s --profile-dir ~/profiles # Alternatives Verzeichnis für Profile
        """
    )

    parser.add_argument(
        '--d',
        metavar='VERZEICHNIS',
        type=Path,
        help='Alternatives Verzeichnis für Jameica-Konfiguration (default: ~/.jameica)'
    )

    parser.add_argument(
        '--env',
        action='store_true',
        help='Verwende .env Datei statt Jameica-Konfiguration'
    )

    parser.add_argument(
        '--log-level',
        choices=['debug', 'info', 'warning', 'error'],
        default='error',
        help='Log-Level (default: error)'
    )

    parser.add_argument(
        '--profile-dir',
        metavar='VERZEICHNIS',
        type=Path,
        help='Alternatives Verzeichnis für Profile (default: ~/.jameica/hibi-bube/profiles)'
    )

    parser.add_argument(
        '--export-dir',
        metavar='VERZEICHNIS',
        type=Path,
        help='Alternatives Verzeichnis für Exporte (default: ~/.jameica/hibi-bube/exports)'
    )

    parser.add_argument(
        '--log-dir',
        metavar='VERZEICHNIS',
        type=Path,
        help='Alternatives Verzeichnis für Logs (default: ~/.jameica/hibi-bube/logs)'
    )

    return parser.parse_args()


def main():
    """
    Main application entry point for the Hibi-BuBe Report Application.

    This function initializes the application by performing the following steps:
    1. Parses command line arguments (--d, --env).
    2. Configures the settings based on CLI options.
    3. Displays startup information.
    4. Establishes a connection to the database.
    5. Loads all available categories from the database for use within the application.
    6. Initializes the PyQt6 application framework.
    7. Launches the main GUI window.
    8. Starts the application event loop.

    :returns: An integer representing the application's exit code. Returns 0 for
        successful execution and 1 in case of a failure during setup.
    """
    # Parse CLI arguments
    args = parse_arguments()

    # Set CLI options BEFORE any settings are loaded
    set_cli_options(
        config_dir=args.d,
        use_env=args.env,
        log_level=args.log_level,
        profile_dir=args.profile_dir,
        export_dir=args.export_dir,
        log_dir=args.log_dir
    )

    # Initialize settings (loads config based on CLI options)
    settings = init_settings()

    # Setup logging after settings are initialized
    setup_logging(settings.app.log_level, settings.app.log_file)

    print("=" * 60)
    print(" Hibi-BuBe Report-App")
    print("=" * 60)
    print()
    print(f"📝 Log-Level: {settings.app.log_level}")
    print(f"📂 Profile: {settings.app.profile_dir}")
    print(f"📂 Exporte: {settings.app.export_dir}")
    print(f"📂 Logs: {settings.app.log_file}")
    print()

    # Show configuration source
    config_path = args.d if args.d else Path.home() / ".jameica"
    
    if settings.db.source == 'jameica':
        print(f"📁 Konfiguration: Jameica ({config_path})")
    elif settings.db.source == 'env':
        print(f"📁 Konfiguration: .env Datei")
    else:
        print(f"📁 Konfiguration: Standard-Werte")
        
    # Prüfe ob Jameica-Modus aber keine Config gefunden
    if not args.env and settings.db.source == 'default':
        from PyQt6.QtWidgets import QMessageBox
        app_temp = QApplication(sys.argv)
        
        config_file_path = config_path / 'cfg/de.willuhn.jameica.hbci.rmi.HBCIDBService.properties'
        
        QMessageBox.critical(
            None,
            "Keine Jameica-Konfiguration gefunden",
            "<h3>MySQL-Konfiguration fehlt</h3>"
            "<p>Es wurde keine MySQL-Konfiguration in Jameica gefunden.</p>"
            "<p><b>Mögliche Lösungen:</b></p>"
            "<ul>"
            "<li>Stellen Sie sicher, dass Hibiscus mit MySQL konfiguriert ist</li>"
            "<li>Verwenden Sie eine .env Datei mit <code>--env</code></li>"
            "<li>Geben Sie ein alternatives Jameica-Verzeichnis mit <code>--d PFAD</code> an</li>"
            "</ul>"
            "<p><b>Erwartete Jameica-Konfigurationsdatei:</b><br>"
            f"<code>{config_file_path}</code></p>"
        )
        return 1

    print(f"🔗 Verbinde mit Datenbank: {settings.db.host}:{settings.db.port}/{settings.db.database}")

    # 1. Verbindung zur DB herstellen
    try:
        db = DatabaseManager()
        if not db.test_connection():
            print("❌ Datenbankverbindung fehlgeschlagen!")
            if settings.db.source == 'jameica':
                print("Bitte prüfen Sie die Jameica-Konfiguration!")
            elif settings.db.source == 'env':
                print("Bitte prüfen Sie die .env Datei!")
            else:
                print("Bitte konfigurieren Sie die Datenbankverbindung!")
            return 1
        print("✅ Datenbankverbindung erfolgreich")
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der DB-Verbindung: {e}")
        if settings.db.source == 'jameica':
            print("Bitte prüfen Sie die Jameica-Konfiguration!")
        elif settings.db.source == 'env':
            print("Bitte prüfen Sie die .env Datei!")
        else:
            print("Bitte konfigurieren Sie die Datenbankverbindung!")
        return 1

    # 2. Kategorien laden (Test)
    try:
        categories = db.categories.get_all()
        print(f"✅ {len(categories)} Kategorien geladen")
    except Exception as e:
        print(f"❌ Fehler beim Laden der Kategorien: {e}")
        return 1

    print()
    print("Starte GUI...")
    print()

    # 3. PyQt6 Application erstellen
    app = QApplication(sys.argv)
    app.setApplicationName("Hibi-BuBe Report Generator")
    app.setOrganizationName("Hibi-BuBe")

    # 4. MainWindow erstellen und anzeigen
    window = MainWindow(db)
    window.show()

    # 5. Event Loop starten
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
