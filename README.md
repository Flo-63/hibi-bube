# Hibi-BuBe Report-App

Buchungsreports für jameica-hibiscus.

## Features

### ✅ Datenzugriff und Filterung
- **Automatische Übernahme** der Hibiscus-Konfiguration (DB Zugriff)
- **Mehrfach-Kontenauswahl** mit "Alle auswählen/abwählen"
- **Kontengruppen-Filter** - Filterung nach flags=1 (Kontengruppen)
- **Hierarchische Kategorien** - Struktur von Hibiscus-Kategorien wird erkannt
- **Kategorie-Filter** mit "Keine"-Button für unkategorisierte Buchungen
- **Dynamische Kategoriezuordnung** - Regelbasierte automatische Kategoriezuweisung mit Pattern-Matching wie in Hibiscus
- **Flexible Zeitraumauswahl** (vordefiniert + benutzerdefiniert)
- **Datumsfeld-Auswahl** (Buchungsdatum vs. Valuta)

### ✅ Ansicht und Gruppierung
- **Hierarchische Tabellenansicht** mit erweiterbaren Gruppen
- **Mehrstufige Gruppierung** (Kategorie → Subkategorie)
- **Flexible Feldauswahl** (Datum, Betrag, Kategorie, Verwendungszweck, etc.)
- **Sortierung** nach Datum, Betrag oder Kategorie (auf-/absteigend)
- **Summen-Rows** - Zwischensummen + Gesamtsumme
- **Soll/Haben-Anzeige** (optional wählbar)

### ✅ Benutzeroberfläche
- **Modern UI** mit PyQt6
- **Dark/Light Mode** vollständig unterstützt 
- **Tab-basierte Konfiguration** für übersichtliche Bedienung
- **Spalten anpassbar** - Breite und Reihenfolge speicherbar
- **Expand/Collapse Buttons** für schnelle Navigation in hierarchischer Ansicht
- **Suchfeld** für schnelle Buchungssuche (Text-Matching in den angezeigten Feldern der gefilterten Buchungen)

### ✅ Export und Druck
- **PDF-Export** mit Formatierung und Report-Namen als Dateivorschlag
- **Excel-Export** (.xlsx) mit Summen, Styling und Report-Namen als Dateivorschlag
- **Druckfunktion** mit Vorschau
- **Spalteneinstellungen aus Preview** werden in Export übernommen
- **Konfigurierbare Export-Verzeichnisse** mit Persistenz

### ✅ Profil-Verwaltung
- **Speichern/Laden** von Report-Konfigurationen
- **Profil-Dropdown** für schnellen Zugriff
- **JSON-basierte Speicherung** für Portabilität

## Screenshots

### Hauptfenster

(Noch zu erstellen)
## Installation

### Voraussetzungen

- **Python 3.10** oder höher
- Zugriff auf eine **Hibiscus MySQL/MariaDB-Datenbank**

### Setup

1. **Repository klonen / Verzeichnis öffnen**
   ```bash
   mkdir -p ~/Projects/Hibi-BuBe
   cd ~/Projects/Hibi-BuBe
   ```

2. **Virtuelle Umgebung erstellen**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # oder: venv\Scripts\activate  # Windows
   ```

3. **Dependencies installieren**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfiguration**
   - Falls jameica/Hibiscus isntalliert ist, wird die Konfiguration automatisch erkannt.
   - Alternativ kann die eine manuelle Konfiguration erstellt und mit --env genutzt werden:
   - Erstelle eine Datei .env und passe Datenbankzugangsdaten an:
   ```bash
   nano .env  # oder ein anderer Editor
   ```

   Wichtige Einstellungen in `.env`:
   ```env
   DB_USER=hibiscus_user
   DB_PASSWORD=dein_passwort
   DB_HOST=<db_host>
   DB_PORT=<db_port>
   DB_NAME=hibiscus

   # Optional: Theme-Einstellung
   APP_THEME=dark  # oder "light"
   ```

5. **Anwendung starten**
   ```bash
   python main.py
   ```
6. ** Command Line Parameter:**
```
  -h, --help               Zeigt den Hilfe-Text an
  --d VERZEICHNIS          Alternatives Verzeichnis für Jameica-Konfiguration (default: ~/.jameica)
  --env                    Verwende .env Datei statt Jameica-Konfiguration
  --log-level {debug,info,warning,error}
                           Log-Level (default: error)
  --profile-dir VERZEICHNIS
                           Alternatives Verzeichnis für Profile (default: ~/.jameica/hibi-bube/profiles)
  --export-dir VERZEICHNIS
                           Alternatives Verzeichnis für Exporte (default: ~/.jameica/hibi-bube/exports)
  --log-dir VERZEICHNIS
                           Alternatives Verzeichnis für Logs (default: ~/.jameica/hibi-bube/logs)
```
## Verwendung

### Grundlegender Workflow

1. **Konten auswählen** (Tab "Konten")
   - Wähle ein oder mehrere Konten aus
   - Nutze auch den Button "Kontengruppen", wenn du in Hbiscus Kontengruppen angelegt hast.

2. **Kategorien filtern** (Tab "Kategorien")
   - Wähle gewünschte Kategorien/Subkategorien
   - Option "Ohne Kategorie" für unkategorisierte Buchungen
 
3. **Zeitraum festlegen** (Tab "Zeitraum")
   - Vordefinierte Perioden (Aktuelles Jahr, Letztes Jahr, etc.)
   - Oder benutzerdefinierter Zeitraum

4. **Felder konfigurieren** (Tab "Felder")
   - Wähle anzuzeigende Spalten
 
5. **Gruppierung einstellen** (Tab "Anzeige")
   - Gruppierung nach Kategorie/Subkategorie
   - Sortierung festlegen
   - Soll/Haben-Summen optional

6. **Vorschau laden**
   - Klicke "⟳ Aktualisieren" in der Vorschau
   - Navigiere durch hierarchische Ansicht
   - Spalten verschieben und Breite anpassen

7. **Exportieren**
   - "🖨 Drucken / Export" → PDF, Excel oder Druck

### Profile verwenden

**Profil speichern:**
1. Konfiguriere deinen Report wie gewünscht
2. Gib einen Namen im "Name:"-Feld ein
3. Klicke "💾 Speichern"

**Profil laden:**
- **Via Dropdown:** Wähle Profil aus dem "Profil:"-Dropdown
- **Via Menü:** Datei → Template laden


## Projektstruktur

```
hibi-bube/
├── src/
│   ├── config/              # Konfigurationsmanagement
│   │   ├── settings.py      # Pydantic Settings
│   │   └── database.py      # DB-Konfiguration
│   ├── data/                # Datenbankzugriff
│   │   ├── database_manager.py
│   │   ├── repositories/    # Repository-Pattern
│   │   │   ├── category_repository.py
│   │   │   ├── transaction_repository.py
│   │   │   └── account_repository.py
│   │   └── models/          # Domain Models
│   │       ├── domain_models.py
│   │       └── report_config.py
│   ├── business/            # Business Logic
│   │   └── services/
│   │       ├── hierarchy_builder.py
│   │       ├── aggregation_service.py
│   │       └── profile_manager.py
│   ├── gui/                 # GUI-Komponenten (PyQt6)
│   │   ├── main_window.py
│   │   ├── widgets/         # UI Widgets
│   │   └── dialogs/         # Dialoge
│   └── utils/               # Hilfsfunktionen
├── main.py                  # Einstiegspunkt
├── requirements.txt         # Python Dependencies
├── .env                     # Konfiguration (nicht in Git!)
└── .env.example             # Konfigurationsvorlage
```

## Entwicklungsstand

**Status:** ✅ **Version 0.8 - Beta - Produktionsreif**

Alle geplanten Kern-Features sind implementiert und optimiert:
- ✅ Phase 0: Projekt-Setup
- ✅ Phase 1: Datenzugriff und Business Logic
- ✅ Phase 2: GUI mit PyQt6
- ✅ Phase 3: Export und Profil-Verwaltung
- ✅ Performance-Optimierungen (Regex-Caching, Threading)
- ✅ UX-Verbesserungen (Suchfeld, Expand/Collapse, Wartecursor)
- ✅ Dark Mode komplett für alle Dialoge

## Verwendete Technologien

- **GUI:** PyQt6 - Moderne, plattformübergreifende Desktop-Anwendung
- **Datenbank:** SQLAlchemy + PyMySQL - ORM und Datenbankzugriff
- **Export:** QPrinter (PDF), openpyxl (Excel)
- **Konfiguration:** python-dotenv, pydantic
- **Architektur:** Repository-Pattern, Service-Layer

## Technische Highlights

- **Repository-Pattern** für saubere Datenzugriffe
- **Pydantic** für Datenvalidierung und Settings
- **QTreeView** für hierarchische Darstellung
- **Virtuelle Kategorisierung** mit Regex/Plain-Text-Matching und Caching
- **Profile-System** mit JSON-Serialisierung
- **Dark/Light Mode** vollständig themed (inkl. FileDialog, MessageBox, Print Preview)
- **Performance-Optimierung** durch Regex-Caching und Threading
- **Lazy Pattern Compilation** für optimierte Startup-Zeit

## Bekannte Limitierungen

- **Direkter CSV-Export** nicht implementiert (XLSX-Export stattdessen)
- **Profil-Verwaltungs-UI** - Löschen/Umbenennen nur über Dateisystem
- **Filter-Suche** in Kategorie/Konto-Listen nicht vorhanden (nur in Buchungen)

## Ideen für Zukünftige Erweiterungen

- Diagramme/Charts (matplotlib/plotly)
- Budgetvergleich (Soll/Ist)
- Mehrsprachigkeit (i18n)

## Lizenz

[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)

## Support

Bei Fragen oder Problemen erstellen Sie bitte ein Issue im Repository.

(c) 2026 Florian Mösch
