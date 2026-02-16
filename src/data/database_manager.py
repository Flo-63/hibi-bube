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

    def __init__(self, connection_string: str = None):
        """
        Initializes the database connection and engine with connection pooling.

        This class handles the setup of a database connection using SQLAlchemy's
        connection pooling capabilities. It provides a configurable connection
        string and parameters for the connection pool such as size, overflow,
        and recycling strategy. Repositories for various database entities
        are also initialized.

        :param connection_string: Optional database connection string. If not provided,
            a default connection string is fetched from the application settings.
        :type connection_string: str
        """
        if connection_string:
            self.url = connection_string
        else:
            from src.config.settings import settings
            self.url = settings.db.connection_string

        # Optionaler Check: Falls settings leer sind, versuche Jameica-Auto-Detect
        if not self.url or "localhost" in self.url:  # Beispielhafter Check
            auto_url = self._detect_jameica_url()
            if auto_url:
                self.url = auto_url

        # Engine mit Connection Pooling
        self.engine = create_engine(
            self.url,
            poolclass=pool.QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Testet Verbindung vor Verwendung
            pool_recycle=3600  # Recycle Connections nach 1 Stunde
        )

        # Repositories initialisieren
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

    def _detect_jameica_url(self) -> str:
        """
        Detects the URL for the Jameica HBCI database configuration.

        This method attempts to locate and parse the configuration file for the Jameica
        HBCI plugin. If the necessary configuration exists and specifies a JDBC URL for
        a MySQL database, it converts the URL into the SQLAlchemy-compatible format.
        If any part of the parsing fails or the configuration file is not present,
        the method returns None.

        :return: The SQLAlchemy-compatible database URL or None if the configuration is
            incomplete, invalid, or missing.
        :rtype: str
        """
        import os
        from pathlib import Path

        config_path = Path.home() / ".jameica/cfg/de.willuhn.jameica.hbci.rmi.HBCIDBService.properties"
        if not config_path.exists():
            return None

        config = {}
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip().replace('\\:', ':')

            # Extrahiere Daten aus der JDBC-URL: jdbc:mysql://127.0.0.1:3306/hibiscus
            jdbc_url = config.get("database.driver.url", "")
            user = config.get("database.driver.username")
            password = config.get("database.driver.password")

            # Umwandeln in SQLAlchemy Format: mysql+pymysql://user:pass@host:port/dbname
            if "mysql" in jdbc_url:
                parts = jdbc_url.split("//")[1]
                host_port = parts.split("/")[0]
                db_name = parts.split("/")[1]
                return f"mysql+pymysql://{user}:{password}@{host_port}/{db_name}"
        except Exception as e:
            logger.error(f"Fehler beim Parsen der Jameica-Config: {e}")

        return None
