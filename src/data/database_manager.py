"""
===============================================================================
Project   : Hibi-BuRe
Module    : database_manager.py
Created   : 13.02.26
Author    : florian
Purpose   : DatabaseManager manages database connections and provides repositories for data access.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from sqlalchemy import create_engine, text, pool
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import pandas as pd
import logging

from src.data.h2_adapter import H2EngineAdapter
from src.data.repositories.category_repository import CategoryRepository
from src.data.repositories.transaction_repository import TransactionRepository
from src.data.repositories.account_repository import AccountRepository

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Handles database connection pooling and repository access.

    DatabaseManager is responsible for managing the database connection,
    initializing repository objects for various entities, and providing
    methods to test and close the database connection. It also includes
    legacy methods for compatibility with older interfaces.

    :ivar url: Database connection string used to establish the connection.
    :type url: str
    :ivar engine: SQLAlchemy engine with connection pooling configured.
    :type engine: sqlalchemy.engine.Engine
    """

    def __init__(self, connection_string: str = None, h2_password: str = None):
        """
        Initializes the database connection and engine with connection pooling.

        This class handles the setup of a database connection using SQLAlchemy's
        connection pooling capabilities or a custom H2 bridge adapter. It provides
        a configurable connection string and parameters for the connection pool
        such as size, overflow, and recycling strategy. Repositories for various
        database entities are also initialized.

        :param connection_string: Optional database connection string. If not provided,
            a default connection string is fetched from the application settings.
        :type connection_string: str
        :param h2_password: Optional password for encrypted H2 databases (Jameica master password)
        :type h2_password: str
        """
        self.url = None
        self.engine = None
        self.h2_password = h2_password

        # 1. Versuch: Jameica-Auto-Detect (versucht ZUERST direkt die Config zu lesen)
        # Dies erkennt sowohl MySQL als auch H2 und gibt direkt die passende Engine zurück
        self.engine = self._create_engine_from_jameica()

        # 2. Fallback: Nutze expliziten Connection-String oder Settings
        if self.engine is None:
            if connection_string:
                self.url = connection_string
            else:
                from src.config.settings import settings
                self.url = settings.db.connection_string

            if not self.url:
                raise ValueError("Keine Datenbank-Konfiguration gefunden und Jameica Auto-Detect schlug fehl.")

            # Engine mit Connection Pooling für reguläre SQL-Verbindungen (MySQL)
            self.engine = create_engine(
                self.url,
                poolclass=pool.QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Testet Verbindung vor Verwendung
                pool_recycle=3600  # Recycle Connections nach 1 Stunde
            )

        # Repositories initialisieren (Lazy Loading)
        self._category_repo = None
        self._transaction_repo = None
        self._account_repo = None

    @property
    def categories(self) -> CategoryRepository:
        """
        Provides access to the category repository, ensuring the repository object
        is lazily initialized only when accessed for the first time.

        :rtype: CategoryRepository
        :return: An instance of `CategoryRepository` tied to the current database
            engine, enabling the management and querying of category-related data.
        """
        if self._category_repo is None:
            self._category_repo = CategoryRepository(self.engine)
        return self._category_repo

    @property
    def transactions(self) -> TransactionRepository:
        """
        Provides access to the transaction repository by initializing it if it does
        not yet exist. This ensures a single instance of `TransactionRepository`
        is created and reused for interacting with transactions.

        :return: Returns the initialized or previously prepared `TransactionRepository`
            instance.
        :rtype: TransactionRepository
        """
        if self._transaction_repo is None:
            self._transaction_repo = TransactionRepository(self.engine)
        return self._transaction_repo

    @property
    def accounts(self) -> AccountRepository:
        """
        Provides access to the AccountRepository. Creates an instance of
        AccountRepository if it does not already exist.

        :return: An instance of AccountRepository associated with the current engine.
        :rtype: AccountRepository
        """
        if self._account_repo is None:
            self._account_repo = AccountRepository(self.engine)
        return self._account_repo

    def test_connection(self) -> bool:
        """
        Tests the database connection by attempting to execute a simple query. This function
        verifies whether the database engine is operational by connecting to the database
        and testing its response to a basic query. Logs success or error messages accordingly.

        :return: True if the connection test is successful, False otherwise.
        :rtype: bool
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Datenbankverbindung erfolgreich getestet")
            return True
        except OperationalError as e:
            logger.error(f"Datenbankverbindung fehlgeschlagen: {e}")
            return False
        except SQLAlchemyError as e:
            logger.error(f"Datenbankfehler beim Verbindungstest: {e}")
            return False

    def close(self):
        """
        Closes the database connections.

        This method disposes of the database engine connection if it has been
        initialized, ensuring proper resource cleanup. It also logs the action
        to assist in tracking the application's connection-handling.

        :return: None
        """
        if self.engine:
            self.engine.dispose()
            logger.info("Datenbankverbindungen geschlossen")

    def _create_engine_from_jameica(self):
        """
        Detects the Jameica HBCI database configuration and creates the appropriate engine.

        Reads the configuration file for the Jameica HBCI plugin.
        - If MySQL is configured, it returns a standard SQLAlchemy engine.
        - If H2 is configured, it returns our custom H2EngineAdapter.

        :return: SQLAlchemy Engine OR H2EngineAdapter, or None on failure.
        """
        import os
        from pathlib import Path
        from sqlalchemy import create_engine, pool
        from src.config.settings import get_config_dir

        # WICHTIG: Hier importieren wir unseren neuen Adapter (aus Schritt 2)
        try:
            from src.data.h2_adapter import H2EngineAdapter
        except ImportError:
            H2EngineAdapter = None

        # Use get_config_dir() to respect CLI options and .jameica.properties
        config_dir = get_config_dir()
        config_path = config_dir / "cfg/de.willuhn.jameica.hbci.rmi.HBCIDBService.properties"
        if not config_path.exists():
            return None

        config = {}
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip().replace('\\:', ':')

            # Versuche verschiedene Property-Keys für JDBC URL und Passwort
            jdbc_url = (config.get("database.driver.mysql.jdbcurl", "") or
                       config.get("database.driver.url", ""))
            password = (config.get("database.driver.mysql.password", "") or
                       config.get("database.driver.password", ""))

            # H2-Spezialfall: Wenn kein jdbc_url aber H2-Properties vorhanden
            has_h2_encryption = any(k.startswith("database.driver.h2.encryption") for k in config.keys())
            if not jdbc_url and has_h2_encryption:
                # Standard H2-Pfad in Jameica (prüfe verschiedene mögliche Speicherorte)
                possible_db_paths = [
                    config_dir / "hibiscus/h2db/hibiscus",  # Neuer Standard-Pfad
                    config_dir / "hibiscus/hibiscus",       # Alter Standard-Pfad
                ]

                db_path = None
                for path in possible_db_paths:
                    if (Path(str(path) + ".mv.db")).exists():
                        db_path = path
                        break

                if not db_path:
                    # Fallback auf neuen Standard
                    db_path = possible_db_paths[0]

                jdbc_url = f"jdbc:h2:{db_path}"
                # Verschlüsseltes Passwort für H2
                password = config.get("database.driver.h2.encryption.encryptedpassword", "")
                logger.info(f"H2-Konfiguration ohne explizite URL gefunden. Nutze Pfad: {jdbc_url}")

            # --- FALL 1: MySQL/MariaDB (Engine mit Connection-Pooling) ---
            if "mysql" in jdbc_url.lower() or "mariadb" in jdbc_url.lower():
                user = (config.get("database.driver.mysql.username", "") or
                       config.get("database.driver.username", ""))
                parts = jdbc_url.split("//")[1]
                host_port = parts.split("/")[0]
                db_part = parts.split("/")[1]
                # Entferne Query-Parameter (alles nach ?)
                db_name = db_part.split("?")[0] if "?" in db_part else db_part

                conn_str = f"mysql+pymysql://{user}:{password}@{host_port}/{db_name}"

                # Hier werden die Pool-Settings übergeben
                return create_engine(
                    conn_str,
                    poolclass=pool.QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )

            # --- FALL 2: H2 (Custom Adapter) ---
            elif "jdbc:h2:" in jdbc_url:
                if not H2EngineAdapter:
                    logger.error("H2 konfiguriert, aber H2EngineAdapter fehlt im Code.")
                    return None

                # Pfad bereinigen (schneidet alles nach dem eigentlichen Pfad ab)
                raw_path = jdbc_url.split("jdbc:h2:")[1].split(";")[0]

                # Expandiere ~ zu Home-Verzeichnis
                if raw_path.startswith("~"):
                    raw_path = str(Path.home() / raw_path[2:])

                # Jameica H2 Jar suchen (verschiedene mögliche Speicherorte)
                # WICHTIG: Nutze h2-1.4.199-fork.jar
                # Grund: DB-Dateien sind im alten Format, h2-2.3.232.jar kann diese nicht öffnen
                possible_jar_paths = [
                    Path.home() / "Apps/jameica/lib/h2/migration-h2/enabled/h2-1.4.199-fork.jar",
                    Path.home() / ".jameica/lib/h2/migration-h2/enabled/h2-1.4.199-fork.jar",
                    Path.home() / "Apps/jameica/lib/h2/migration-h2/enabled/h2-2.3.232.jar",
                    Path.home() / ".jameica/lib/h2/migration-h2/enabled/h2-2.3.232.jar",
                    Path.home() / ".jameica/lib/h2/h2.jar",
                    Path.home() / ".jameica/plugins/hibiscus/lib/h2.jar",
                    Path("/usr/share/jameica/lib/h2/h2.jar"),
                    Path("/opt/jameica/lib/h2.jar"),
                ]

                jar_path = None
                for path in possible_jar_paths:
                    if path.exists():
                        jar_path = str(path)
                        break

                if not jar_path:
                    logger.error(
                        f"H2 JAR-Datei nicht gefunden. Geprüfte Pfade:\n" +
                        "\n".join(f"  - {p}" for p in possible_jar_paths) +
                        "\n\nBitte installiere die H2-Datenbank oder platziere h2.jar " +
                        "in einem der oben genannten Verzeichnisse."
                    )
                    return None

                # Zeige Password-Dialog an
                logger.info("Kein H2-Master-Passwort vorhanden. Zeige Password-Dialog an.")
                _, file_password = self._show_password_dialog()

                if not file_password:
                    logger.error("H2-Verbindung abgebrochen: Kein Datei-Passwort eingegeben.")
                    return None

                logger.info(f"H2 Datenbank erkannt. Nutze H2EngineAdapter mit JAR: {jar_path}")
                return H2EngineAdapter(
                    db_path=raw_path,
                    jar_path=jar_path,
                    file_password=file_password
                )

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Engine aus Jameica-Config: {e}")

        return None

    def _show_password_dialog(self):
        """
        Zeigt einen Dialog zur Eingabe der H2-Passwörter an.

        :return: Tuple of (master_password, file_password)
        :rtype: tuple[str, str]
        """
        try:
            from PyQt6.QtWidgets import QApplication
            from src.gui.dialogs.password_dialog import PasswordDialog

            # Stelle sicher, dass eine QApplication-Instanz existiert
            app = QApplication.instance()
            if app is None:
                logger.warning("Keine QApplication-Instanz vorhanden. Kann Password-Dialog nicht anzeigen.")
                return None, None

            dialog = PasswordDialog()
            if dialog.exec():
                return dialog.get_passwords()
            else:
                return None, None
        except Exception as e:
            logger.error(f"Fehler beim Anzeigen des Password-Dialogs: {e}")
            return None, None