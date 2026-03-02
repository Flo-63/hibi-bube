"""
===============================================================================
Project   : Hibi-BuBe
Module    : jameica_config_reader.py
Created   : 14.02.2026
Author    : Florian
Purpose   : Reads database configuration from Jameica properties file

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class JameicaConfigReader:
    """
    Reads database configuration from Jameica's HBCIDBService.properties file.

    This class parses the Jameica configuration file to extract database
    connection parameters such as JDBC URL, username, and password. It supports
    custom configuration directory paths for flexible deployment scenarios.

    :ivar config_dir: Path to the Jameica configuration directory
    :type config_dir: Path
    :ivar config_file: Path to the HBCIDBService.properties file
    :type config_file: Path
    """

    CONFIG_FILENAME = "cfg/de.willuhn.jameica.hbci.rmi.HBCIDBService.properties"

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the Jameica configuration reader.

        :param config_dir: Optional custom path to Jameica config directory.
            If not provided, checks ~/.jameica.properties for 'dir=' parameter,
            then falls back to ~/.jameica
        :type config_dir: Optional[Path]
        """
        self.config_dir = config_dir or self._get_jameica_workdir()
        self.config_file = self.config_dir / self.CONFIG_FILENAME

    def _get_jameica_workdir(self) -> Path:
        """
        Determine the actual Jameica working directory.

        Priority:
        1. ~/.jameica.properties (dir=...)
        2. Fallback to ~/.jameica

        :return: Path to Jameica working directory
        :rtype: Path
        """
        prop_file = Path.home() / ".jameica.properties"
        if prop_file.exists():
            try:
                with open(prop_file, 'r') as f:
                    for line in f:
                        if line.startswith("dir="):
                            dir_path = Path(line.strip().split("=", 1)[1])
                            logger.info(f"Using Jameica workdir from .jameica.properties: {dir_path}")
                            return dir_path
            except Exception as e:
                logger.warning(f"Could not read .jameica.properties: {e}")

        # Fallback
        default_path = Path.home() / ".jameica"
        logger.debug(f"Using default Jameica workdir: {default_path}")
        return default_path

    def exists(self) -> bool:
        """
        Check if the Jameica configuration file exists.

        :return: True if the configuration file exists, False otherwise
        :rtype: bool
        """
        return self.config_file.exists()

    def read_db_config(self) -> Optional[Dict[str, str]]:
        """
        Read and parse the Jameica database configuration.

        Extracts database connection parameters from the properties file,
        including host, port, database name, username, and password.

        :return: Dictionary containing database configuration parameters
            (host, port, database, user, password) or None if parsing fails
        :rtype: Optional[Dict[str, str]]
        """
        if not self.exists():
            logger.warning(f"Jameica config file not found: {self.config_file}")
            return None

        config = {}
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Unescape Java properties format (replace \: with :)
                        config[key.strip()] = value.strip().replace('\\:', ':')

            # Extract database parameters
            return self._parse_db_params(config)

        except Exception as e:
            logger.error(f"Error reading Jameica config: {e}")
            return None

    def _parse_db_params(self, config: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        Parse database parameters from the Jameica configuration.

        Converts JDBC URL format (jdbc:mysql://host:port/database or
        jdbc:mariadb://host:port/database) into individual components.

        :param config: Raw configuration dictionary from properties file
        :type config: Dict[str, str]
        :return: Parsed database parameters or None if parsing fails
        :rtype: Optional[Dict[str, str]]
        """
        try:
            # Get JDBC URL - try different property keys
            jdbc_url = (config.get("database.driver.mysql.jdbcurl", "") or
                       config.get("database.driver.url", ""))

            # Get username and password - try different property keys
            user = (config.get("database.driver.mysql.username", "") or
                   config.get("database.driver.username", ""))

            password = (config.get("database.driver.mysql.password", "") or
                       config.get("database.driver.password", ""))

            if not jdbc_url:
                logger.debug("No JDBC URL found in Jameica config (möglicherweise H2)")
                return None

            # Support both MySQL and MariaDB
            # Hinweis: H2 wird separat vom DatabaseManager behandelt
            if "mysql" not in jdbc_url.lower() and "mariadb" not in jdbc_url.lower():
                logger.debug(f"Non-MySQL database in JDBC URL (z.B. H2): {jdbc_url}")
                return None

            # Parse JDBC URL: jdbc:mysql://host:port/database
            # Remove jdbc:mysql:// prefix
            if "://" in jdbc_url:
                connection_part = jdbc_url.split("://", 1)[1]
            else:
                logger.error(f"Invalid JDBC URL format: {jdbc_url}")
                return None

            # Split host:port and database
            if "/" not in connection_part:
                logger.error(f"Invalid JDBC URL format (missing database): {jdbc_url}")
                return None

            host_port, database = connection_part.split("/", 1)

            # Remove query parameters if present
            if "?" in database:
                database = database.split("?")[0]

            # Split host and port
            if ":" in host_port:
                host, port = host_port.rsplit(":", 1)
            else:
                host = host_port
                port = "3306"  # Default MySQL port

            db_config = {
                "host": host,
                "port": port,
                "database": database,
                "user": user,
                "password": password
            }

            logger.info(f"Successfully parsed Jameica DB config: {host}:{port}/{database}")
            return db_config

        except Exception as e:
            logger.error(f"Error parsing database parameters: {e}")
            return None

    def get_connection_string(self) -> Optional[str]:
        """
        Get SQLAlchemy connection string from Jameica configuration.

        Reads the Jameica configuration and converts it to a format
        compatible with SQLAlchemy (mysql+pymysql://user:pass@host:port/db).

        :return: SQLAlchemy connection string or None if unavailable
        :rtype: Optional[str]
        """
        db_config = self.read_db_config()
        if not db_config:
            return None

        return (f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}")


if __name__ == "__main__":
    # Test the configuration reader
    print("=== Jameica Config Reader Test ===\n")

    reader = JameicaConfigReader()
    print(f"Config file: {reader.config_file}")
    print(f"Exists: {reader.exists()}\n")

    if reader.exists():
        db_config = reader.read_db_config()
        if db_config:
            print("Database Configuration:")
            print(f"  Host: {db_config['host']}")
            print(f"  Port: {db_config['port']}")
            print(f"  Database: {db_config['database']}")
            print(f"  User: {db_config['user']}")
            print(f"  Password: {'*' * len(db_config['password'])}")
            print(f"\nConnection String:")
            print(f"  {reader.get_connection_string()}")
        else:
            print("❌ Failed to parse database configuration")
    else:
        print("❌ Jameica configuration file not found")
