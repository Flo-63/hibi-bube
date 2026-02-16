"""
===============================================================================
Project   : Hibi-BuBe
Module    : settings.py
Created   : 13.02.26
Author    : florian
Purpose   : Config-Mananger - loads settings from .env file

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

import os
from pathlib import Path
import shutil
from typing import Optional
from dotenv import load_dotenv

# Projekt-Root-Verzeichnis
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Global CLI configuration (set by main.py)
_cli_config_dir: Optional[Path] = None
_cli_use_env: bool = False
_cli_env_loaded: bool = False
_cli_log_level: str = "error"
_cli_profile_dir: Optional[Path] = None
_cli_export_dir: Optional[Path] = None
_cli_log_dir: Optional[Path] = None


def set_cli_options(
    config_dir: Optional[Path] = None,
    use_env: bool = False,
    log_level: str = "error",
    profile_dir: Optional[Path] = None,
    export_dir: Optional[Path] = None,
    log_dir: Optional[Path] = None
):
    """
    Set CLI options for configuration loading.

    This function must be called from main.py before any other config loading.

    :param config_dir: Custom configuration directory (for --d option)
    :type config_dir: Optional[Path]
    :param use_env: Whether to use .env file (for --env flag)
    :type use_env: bool
    :param log_level: Log level (debug, info, warning, error)
    :type log_level: str
    :param profile_dir: Custom profile directory
    :type profile_dir: Optional[Path]
    :param export_dir: Custom export directory
    :type export_dir: Optional[Path]
    :param log_dir: Custom log directory
    :type log_dir: Optional[Path]
    """
    global _cli_config_dir, _cli_use_env, _cli_log_level, _cli_profile_dir, _cli_export_dir, _cli_log_dir
    _cli_config_dir = config_dir
    _cli_use_env = use_env
    _cli_log_level = log_level
    _cli_profile_dir = profile_dir
    _cli_export_dir = export_dir
    _cli_log_dir = log_dir


def get_config_dir() -> Path:
    """
    Get the configuration directory based on CLI options.

    :return: Path to configuration directory
    :rtype: Path
    """
    if _cli_config_dir:
        return _cli_config_dir
    return Path.home() / ".jameica"


def load_environment():
    """
    Loads the environment variables from a `.env` file.

    The function attempts to load the environment variables from a `.env` file
    located in a specific directory. It first checks if the application is running
    as an AppImage. If so, it loads the `.env` file located next to the AppImage file.
    If this file is not found or if the application is in development/debug mode,
    the function falls back to loading the `.env` file located in the project's root directory.

    :return: None
    """
    global _cli_env_loaded

    # Only load .env if --env flag is set
    if not _cli_use_env:
        _cli_env_loaded = False
        return

    env_loaded = False

    # If custom config dir is specified (--d), look for .env there
    if _cli_config_dir:
        env_file = _cli_config_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            env_loaded = True

    # If running in AppImage, look for .env next to AppImage file
    if not env_loaded:
        appimage_path = os.getenv("APPIMAGE")
        if appimage_path:
            external_env = Path(appimage_path).parent / ".env"
            if external_env.exists():
                load_dotenv(external_env)
                env_loaded = True

    # Fallback/Dev-Modus: Suche im Projekt-Root
    if not env_loaded:
        load_dotenv(PROJECT_ROOT / ".env")
        env_loaded = True

    _cli_env_loaded = env_loaded


def get_base_data_dir() -> Path:
    """
    Retrieve the base directory for data storage depending on the execution mode.

    This function determines the appropriate directory for storing user data
    based on whether the application is running in a production environment
    (AppImage) or a development environment. Returns ~/.jameica/hibi-bube/ as
    the standard location for profiles, exports, and logs.

    :return: The base directory for data storage
    :rtype: Path
    """
    return Path.home() / ".jameica" / "hibi-bube"


class DatabaseConfig:
    """
    Represents the configuration for connecting to a database.

    This class provides the necessary attributes and methods to define and
    access database connection settings, such as user credentials, host,
    port, and the database name. Configuration sources are prioritized:
    1. Jameica properties file (primary)
    2. Environment variables (when --env flag is set)
    3. Default values

    :ivar user: The username for the database connection
    :type user: str
    :ivar password: The password associated with the database user
    :type password: str
    :ivar host: The host address of the database
    :type host: str
    :ivar port: The port number for the database connection
    :type port: str
    :ivar database: The name of the target database
    :type database: str
    :ivar source: The configuration source used ('jameica', 'env', or 'default')
    :type source: str
    """

    def __init__(self):
        """
        Initializes the configuration for a database connection.

        Configuration priority:
        1. Jameica properties file (~/.jameica/cfg/... or custom --d path)
        2. Environment variables (only when --env flag is set)
        3. Default values

        The configuration source is tracked in the 'source' attribute.
        """
        from src.config.jameica_config_reader import JameicaConfigReader

        # Try Jameica configuration first (PRIMARY)
        jameica_config = None
        config_dir = get_config_dir()
        reader = JameicaConfigReader(config_dir)

        if reader.exists():
            jameica_config = reader.read_db_config()

        if jameica_config:
            # Use Jameica configuration
            self.user = jameica_config['user']
            self.password = jameica_config['password']
            self.host = jameica_config['host']
            self.port = jameica_config['port']
            self.database = jameica_config['database']
            self.source = 'jameica'
        elif _cli_use_env:
            # Use environment variables (only if --env flag is set)
            self.user = os.getenv("DB_USER", "hibiscus_user")
            self.password = os.getenv("DB_PASSWORD", "")
            self.host = os.getenv("DB_HOST", "localhost")
            self.port = os.getenv("DB_PORT", "3306")
            self.database = os.getenv("DB_NAME", "hibiscus")
            self.source = 'env'
        else:
            # Default values (fallback)
            self.user = "hibiscus_user"
            self.password = ""
            self.host = "localhost"
            self.port = "3306"
            self.database = "hibiscus"
            self.source = 'default'

    @property
    def connection_string(self) -> str:
        """
        Constructs and returns the connection string for a MySQL database using the
        provided user credentials, host, port, and database.

        The resulting connection string is compatible with the `mysql+pymysql` dialect.

        :return: The formatted connection string for the MySQL database.
        :rtype: str
        """
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def __repr__(self) -> str:
        """
        Provides a string representation of the `DatabaseConfig` instance, excluding sensitive
        information such as passwords.

        :return: A string containing the `user`, `host`, `port`, `database`, and `source`
            attributes of the `DatabaseConfig` instance.
        :rtype: str
        """
        # Passwort nicht anzeigen
        return f"DatabaseConfig(user={self.user}, host={self.host}, port={self.port}, db={self.database}, source={self.source})"


class AppConfig:
    """
    Manages application configuration and initializes directories.

    The AppConfig class is responsible for reading configuration values from
    environment variables, providing default values when necessary, and creating
    relevant directories if they do not exist. It also maintains information about
    the logging configuration, GUI settings, and paths for exports and templates.

    :ivar log_level: Logging level used in the application (default: ERROR).
    :type log_level: str
    :ivar log_file: Path to the log file where application logs are written.
    :type log_file: Path
    :ivar export_dir: Path to the directory where exports (PDF, XLS) are stored.
    :type export_dir: Path
    :ivar profile_dir: Path to the directory containing profile files (formerly templates).
    :type profile_dir: Path
    :ivar log_dir: Path to the directory where logs are stored.
    :type log_dir: Path
    :ivar window_width: Default width of the application window in pixels.
    :type window_width: int
    :ivar window_height: Default height of the application window in pixels.
    :type window_height: int
    :ivar theme: Name of the GUI theme (e.g., dark or light).
    :type theme: str
    """

    def __init__(self):
        """
        Initializes an instance of the configuration class, setting up logging, directories, and GUI-related attributes
        based on CLI options, environment variables, or default values. Ensures all necessary directories exist.

        Standard directories:
        - Profiles: ~/.jameica/hibi-bube/profiles/
        - Exports: ~/.jameica/hibi-bube/exports/
        - Logs: ~/.jameica/hibi-bube/logs/hibi-bube.log

        Attributes:
            log_level (str): The logging level of the application (ERROR by default, can be overridden via CLI)
            log_file (Path): The path to the application's log file
            export_dir (Path): Directory path for exports (PDFs, XLS)
            profile_dir (Path): Directory path for profiles (formerly templates)
            log_dir (Path): The directory in which the log file resides
            window_width (int): The width of the application's GUI window
            window_height (int): The height of the application's GUI window
            theme (str): The color theme of the application's GUI
        """
        base_dir = get_base_data_dir()

        # CLI options override defaults
        self.profile_dir = _cli_profile_dir if _cli_profile_dir else base_dir / "profiles"
        self.export_dir = _cli_export_dir if _cli_export_dir else base_dir / "exports"
        self.log_dir = _cli_log_dir if _cli_log_dir else base_dir / "logs"
        self.log_file = self.log_dir / "hibi-bube.log"

        # Log level: CLI > env > default (ERROR)
        self.log_level = _cli_log_level.upper() if _cli_log_level else os.getenv("LOG_LEVEL", "ERROR").upper()

        # GUI settings
        self.window_width = int(os.getenv("WINDOW_WIDTH", "1200"))
        self.window_height = int(os.getenv("WINDOW_HEIGHT", "800"))
        self.theme = os.getenv("THEME", "dark")

        self._ensure_directories()

    def _ensure_directories(self):
        """Erstellt Ordner und kopiert ggf. Standard-Profile."""
        for d in [self.export_dir, self.profile_dir, self.log_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Falls der User-Profile-Ordner leer ist, Standard-Templates aus dem Projekt extrahieren
        internal_templates = PROJECT_ROOT / "templates"
        if internal_templates.exists() and not any(self.profile_dir.iterdir()):
            for item in internal_templates.glob("*"):
                if item.is_file():
                    shutil.copy2(item, self.profile_dir)

    def __repr__(self) -> str:
        """
        Provides a string representation of the class instance for better readability and debugging purposes.

        :return: A string describing the instance with its attributes.
        :rtype: str
        """
        return (f"AppConfig(log_level={self.log_level}, "
                f"theme={self.theme}, "
                f"window_size={self.window_width}x{self.window_height})")


class Settings:
    """
    Encapsulates configuration settings for the application.

    This class is intended to manage and validate application-level settings
    such as database configuration and application-specific configurations.
    It ensures that critical settings are properly set before usage.

    :ivar db: Database-specific configuration settings.
    :type db: DatabaseConfig
    :ivar app: Application-specific configuration settings.
    :type app: AppConfig
    """

    def __init__(self):
        """
        Represents the core application configuration setup, encapsulating database
        and application-specific configuration details.

        :Attributes:
            db: DatabaseConfig
                Represents the database configuration of the application. This
                attribute allows the application to connect to and interact with its
                database layer.

            app: AppConfig
                Denotes the application-specific configuration, which includes
                settings related to the behavior and functionality of the core
                application.
        """
        self.db = DatabaseConfig()
        self.app = AppConfig()

    def validate(self) -> bool:
        """
        Validates the presence of necessary database credentials and ensures both the
        database password and user are properly set. This method raises an exception
        if either credential is missing.

        :raises ValueError: If the database password or user is not set.
        :return: A boolean value indicating successful validation.
        :rtype: bool
        """
        if not self.db.password:
            if self.db.source == 'jameica':
                raise ValueError("Jameica-Konfiguration unvollständig: DB_PASSWORD fehlt!")
            elif self.db.source == 'env':
                raise ValueError("DB_PASSWORD nicht in .env gesetzt!")
            else:
                raise ValueError("DB_PASSWORD nicht gesetzt!")

        if not self.db.user:
            if self.db.source == 'jameica':
                raise ValueError("Jameica-Konfiguration unvollständig: DB_USER fehlt!")
            elif self.db.source == 'env':
                raise ValueError("DB_USER nicht in .env gesetzt!")
            else:
                raise ValueError("DB_USER nicht gesetzt!")

        return True


# Singleton-Instanz (will be initialized after CLI options are set)
settings: Optional[Settings] = None


def init_settings():
    """
    Initialize the settings singleton after CLI options have been set.

    This function must be called from main.py after set_cli_options().

    :return: Initialized Settings instance
    :rtype: Settings
    """
    global settings
    # Load environment variables based on CLI options
    load_environment()
    # Initialize settings
    settings = Settings()
    return settings


if __name__ == "__main__":
    # Test der Konfiguration
    print("=== Hibi-BuBe Configuration ===")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"\nDatabase: {settings.db}")
    print(f"App: {settings.app}")

    try:
        settings.validate()
        print("\n✓ Konfiguration ist valide")
    except ValueError as e:
        print(f"\n✗ Konfigurationsfehler: {e}")
