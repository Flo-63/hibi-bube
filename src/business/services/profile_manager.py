"""
===============================================================================
Project   : Hibi-BuBe
Module    : profile_manager.py
Created   : 13.02.26
Author    : florian
Purpose   : Profilmanager - manages report profiles (stored as JSON)

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

import json
import os
from pathlib import Path
from typing import List, Optional
from src.data.models.report_config import ReportConfig


class ProfileManager:
    """
    Manages the handling of report profiles, including saving, loading, listing, deleting,
    and checking the existence of profiles. The class works with profiles stored as JSON
    files within a specific directory. Profiles are identified by filenames derived from
    safe versions of their names.

    This class facilitates the storage and retrieval of report configurations, ensuring
    that profiles are safe and easily manageable within a pre-defined directory structure.

    :ivar profiles_dir: Directory where the profiles are stored. Defaults to
                        `~/.jameica/hibi-bube/profiles` (from settings) if no directory
                        is specified during initialization.
    :type profiles_dir: Path
    """

    def __init__(self, profiles_dir: Optional[str] = None):
        """
        Initializes the configuration for profile directory handling. This will either use the provided
        `profiles_dir` or fall back to the configured profile directory from settings
        (~/.jameica/hibi-bube/profiles by default). It ensures that the directory exists by creating
        it if it's not already present.

        :param profiles_dir: Optional path to the directory where profiles are stored. If not provided,
            uses the directory from settings.
        :type profiles_dir: Optional[str]
        """
        if profiles_dir:
            self.profiles_dir = Path(profiles_dir)
        else:
            # Verwende Profil-Verzeichnis aus Settings
            from src.config.settings import settings
            if settings:
                self.profiles_dir = settings.app.profile_dir
            else:
                # Fallback wenn Settings nicht initialisiert
                self.profiles_dir = Path.home() / ".jameica" / "hibi-bube" / "profiles"

        # Verzeichnis erstellen falls nicht vorhanden
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(self, config: ReportConfig) -> str:
        """
        Saves a report configuration into a JSON file within the profiles directory. The file
        name is derived from the report's name, and the configuration data is converted to a
        JSON-compatible dictionary before saving.

        :param config: An instance of ReportConfig containing the report data and metadata
            to be saved.
        :type config: ReportConfig
        :return: The file path of the saved report configuration as a string.
        :rtype: str
        """
        # Dateiname aus Report-Name ableiten
        safe_name = self._make_safe_filename(config.name)
        filepath = self.profiles_dir / f"{safe_name}.json"

        # Zu JSON konvertieren
        data = config.to_dict()

        # Speichern
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def load_profile(self, filename: str) -> ReportConfig:
        """
        Loads a profile configuration from a JSON file and converts it into a
        ReportConfig object.

        :param filename: The name of the profile file to be loaded. If the
            provided filename does not have a .json extension, it will automatically
            append it.
        :type filename: str
        :return: The loaded ReportConfig object created from the profile file.
        :rtype: ReportConfig
        :raises FileNotFoundError: If the specified profile file does not exist in the
            profiles directory.
        """
        # Füge .json hinzu falls nötig
        if not filename.endswith('.json'):
            filename = f"{filename}.json"

        filepath = self.profiles_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Profil nicht gefunden: {filepath}")

        # Laden
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Zu ReportConfig konvertieren
        return ReportConfig.from_dict(data)

    def list_profiles(self) -> List[dict]:
        """
        Lists all profiles by reading JSON files from the specified profiles directory. Each profile is
        represented as a dictionary containing its name, filename, and full path. The profiles are sorted
        alphabetically by their name. Faulty or unreadable files are skipped during processing.

        :return: A list of dictionaries with details about each profile.
        :rtype: List[dict]
        """
        profiles = []

        for filepath in self.profiles_dir.glob("*.json"):
            try:
                # Lade Profil um Namen zu bekommen
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                profiles.append({
                    'name': data.get('name', filepath.stem),
                    'filename': filepath.name,
                    'path': str(filepath)
                })
            except:
                # Überspringe fehlerhafte Dateien
                continue

        # Sortiere nach Name
        profiles.sort(key=lambda p: p['name'])

        return profiles

    def delete_profile(self, filename: str) -> bool:
        """
        Deletes a profile file from the profiles directory. If the filename does not
        end with ".json", it appends this extension automatically before attempting
        to delete the file.

        :param filename: Name of the profile file to delete. The provided name will
            automatically have ".json" appended to it if not already present.
        :type filename: str
        :return: True if the file was successfully deleted, False if the file
            does not exist.
        :rtype: bool
        """
        # Füge .json hinzu falls nötig
        if not filename.endswith('.json'):
            filename = f"{filename}.json"

        filepath = self.profiles_dir / filename

        if filepath.exists():
            filepath.unlink()
            return True

        return False

    def profile_exists(self, name: str) -> bool:
        """
        Check if a profile with the given name exists in the profiles directory.

        This method verifies the existence of a profile file associated with
        the provided name. It uses a safe filename transformation to ensure that
        the name is suitable for use in file paths.

        :param name: The name of the profile to check for existence.
        :type name: str
        :return: True if the profile exists, False otherwise.
        :rtype: bool
        """
        safe_name = self._make_safe_filename(name)
        filepath = self.profiles_dir / f"{safe_name}.json"
        return filepath.exists()

    def _make_safe_filename(self, name: str) -> str:
        """
        Generates a safe filename by replacing invalid characters and applying certain constraints.
        This method processes the input string to meet common filename safety requirements. It
        replaces invalid characters, substitutes spaces with underscores, and ensures that the
        resulting filename does not exceed a maximum length of 100 characters.

        :param name: The original name string to be converted into a safe filename.
        :type name: str
        :return: A safe filename string after processing.
        :rtype: str
        """
        # Ersetze ungültige Zeichen
        safe = name.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe = safe.replace('*', '_').replace('?', '_').replace('"', '_')
        safe = safe.replace('<', '_').replace('>', '_').replace('|', '_')

        # Leerzeichen durch Unterstriche
        safe = safe.replace(' ', '_')

        # Maximal 100 Zeichen
        if len(safe) > 100:
            safe = safe[:100]

        return safe


if __name__ == "__main__":
    # Test
    print("=== ProfileManager Test ===\n")

    from src.data.models.domain_models import DateRange

    # Erstelle Manager
    manager = ProfileManager()
    print(f"Profile-Verzeichnis: {manager.profiles_dir}\n")

    # Erstelle Test-Config
    config = ReportConfig(
        name="Test-Bericht März 2024",
        account_ids=[1, 2],
        category_ids=[10, 20],
        date_range=DateRange.this_month(),
        fields=["Datum", "Betrag", "Kategorie", "Verwendungszweck"],
        grouping=["Kategorie"],
        show_count=True
    )

    # Speichern
    print("Speichere Profil...")
    filepath = manager.save_profile(config)
    print(f"✓ Gespeichert: {filepath}\n")

    # Liste Profile
    print("Verfügbare Profile:")
    profiles = manager.list_profiles()
    for p in profiles:
        print(f"  - {p['name']} ({p['filename']})")
    print()

    # Laden
    print("Lade Profil...")
    loaded_config = manager.load_profile("Test-Bericht_März_2024")
    print(f"✓ Geladen: {loaded_config.name}")
    print(f"  Felder: {loaded_config.fields}")
    print(f"  Konten: {loaded_config.account_ids}")
    print()

    # Existenz prüfen
    exists = manager.profile_exists("Test-Bericht März 2024")
    print(f"Profil existiert: {exists}")
