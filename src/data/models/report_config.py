"""
===============================================================================
Project   : Hibi-BuRe
Module    : report_config.py
Created   : 13.02.26
Author    : florian
Purpose   : ReportConfig - Model for report configuration

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date

from src.data.models.domain_models import DateRange


@dataclass
class ReportConfig:
    """
    Representation of a configuration for generating reports.

    Provides a structured format for defining report settings, such as selecting
    accounts, categories, date ranges, sorting, grouping, and display options.
    The class offers support for validation, serialization, and deserialization.

    :ivar name: The name of the report.
    :type name: str
    :ivar account_ids: List of account IDs included in the report.
    :type account_ids: List[int]
    :ivar category_ids: List of category IDs included in the report.
    :type category_ids: List[int]
    :ivar date_range: The date range for the report.
    :type date_range: Optional[DateRange]
    :ivar fields: Fields to be included in the report.
    :type fields: List[str]
    :ivar grouping: Levels of grouping for the report.
    :type grouping: List[str]
    :ivar sort_field: The field used for sorting the report.
    :type sort_field: str
    :ivar sort_order: Sorting order, either 'asc' or 'desc'.
    :type sort_order: str
    :ivar show_subtotals: Whether to display subtotals in the report.
    :type show_subtotals: bool
    :ivar show_grand_total: Whether to display the grand total in the report.
    :type show_grand_total: bool
    :ivar show_count: Whether to display the count of items in the report.
    :type show_count: bool
    :ivar show_debit_credit: Whether to show debit/credit summaries in the footer.
    :type show_debit_credit: bool
    :ivar column_order: Logical indices of columns to determine their order in the layout.
    :type column_order: List[int]
    :ivar column_widths: Column widths in pixels for profile storage.
    :type column_widths: List[int]
    """

    # === Metadaten ===
    name: str = "Neuer Bericht"  # Name des Berichts

    # === Auswahl ===
    account_ids: List[int] = field(default_factory=list)
    category_ids: List[int] = field(default_factory=list)
    date_range: Optional[DateRange] = None

    # === Felder ===
    fields: List[str] = field(default_factory=lambda: ["Datum", "Betrag", "Kategorie"])

    # === Gruppierung ===
    grouping: List[str] = field(default_factory=lambda: ["Kategorie", "Subkategorie"])
    # Mögliche Werte: "Kategorie", "Subkategorie", "Gruppe"

    # === Sortierung ===
    sort_field: str = "Datum"  # "Datum", "Betrag", "Kategorie"
    sort_order: str = "asc"  # "asc" oder "desc"

    # === Anzeige-Optionen ===
    show_subtotals: bool = True
    show_grand_total: bool = True
    show_count: bool = True
    show_debit_credit: bool = False  # Soll/Haben-Summen im Footer

    # === Spalten-Layout (für Profil-Speicherung) ===
    column_order: List[int] = field(default_factory=list)  # Logische Indices der Spalten
    column_widths: List[int] = field(default_factory=list)  # Breiten in Pixeln

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validates the attributes of the current instance against specific business rules
        to ensure that the data configuration is correct.

        :return: A tuple containing a boolean and an optional string. The boolean indicates
            whether the validation passed (`True` for success, `False` for failure). The
            optional string contains an error message if validation fails and is `None` otherwise.
        :rtype: tuple[bool, Optional[str]]
        """
        # Mindestens ein Feld
        if not self.fields:
            return False, "Mindestens ein Feld muss ausgewählt sein"

        # Zeitraum muss gesetzt sein
        if not self.date_range:
            return False, "Zeitraum muss ausgewählt sein"

        # Sortier-Feld muss in ausgewählten Feldern sein (falls verwendet)
        if self.sort_field and self.sort_field not in self.fields:
            # Ist OK, wird intern verwendet
            pass

        # Gruppierung: Max. 3 Ebenen
        if len(self.grouping) > 3:
            return False, "Maximal 3 Gruppierungs-Ebenen erlaubt"

        return True, None

    def to_dict(self) -> dict:
        """
        Converts the object instance into a dictionary representation.

        This method generates a dictionary that captures all the key attributes of
        the object. Attributes that are objects or have nested structures are transformed
        into suitable representations (e.g., ISO format for datetime objects). If specific
        attributes are not present or their value is None, they are represented as such
        in the output dictionary.

        :return: Dictionary containing the serialized representation of the
                 object's attributes.
        :rtype: dict
        """
        return {
            "name": self.name,
            "account_ids": self.account_ids,
            "category_ids": self.category_ids,
            "date_range": {
                "start_date": self.date_range.start_date.isoformat() if self.date_range else None,
                "end_date": self.date_range.end_date.isoformat() if self.date_range else None
            } if self.date_range else None,
            "fields": self.fields,
            "grouping": self.grouping,
            "sort_field": self.sort_field,
            "sort_order": self.sort_order,
            "show_subtotals": self.show_subtotals,
            "show_grand_total": self.show_grand_total,
            "show_count": self.show_count,
            "show_debit_credit": self.show_debit_credit,
            "column_order": self.column_order,
            "column_widths": self.column_widths
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ReportConfig':
        """
        Creates a new instance of the ReportConfig class from a dictionary containing configuration data.
        This method is particularly useful for deserializing report configurations stored as dictionaries
        (e.g., from a database or configuration file) into a fully initialized ReportConfig object.

        :param data: A dictionary containing the configuration data. The keys and values must
                     match the structure required to initialize a ReportConfig object.
                     The expected keys include:
                     - "name" (str): The name of the report.
                     - "account_ids" (list[int]): List of account IDs to include in the report.
                     - "category_ids" (list[int]): List of category IDs to include in the report.
                     - "date_range" (dict): A dictionary containing "start_date" (str, ISO 8601 format)
                       and "end_date" (str, ISO 8601 format) for the reporting time period.
                     - "fields" (list[str]): List of field names to include as columns in the report.
                     - "grouping" (list[str]): List of fields by which the data should be grouped.
                     - "sort_field" (str): The field by which the report data should be sorted.
                     - "sort_order" (str): The sort order ('asc' or 'desc').
                     - "show_subtotals" (bool): Indicator whether subtotals should be shown in the report.
                     - "show_grand_total" (bool): Indicator whether the grand total should be shown.
                     - "show_count" (bool): Indicator whether the count of items should be displayed.
                     - "show_debit_credit" (bool): Indicator to show debit and credit columns separately.
                     - "column_order" (list[str]): Order of columns to display in the report.
                     - "column_widths" (list[int]): List of column widths for the report display.

        :return: A new instance of the ReportConfig class containing the settings defined in the input dictionary.
        :rtype: ReportConfig
        """
        # DateRange rekonstruieren
        date_range = None
        if data.get("date_range"):
            dr = data["date_range"]
            if dr.get("start_date") and dr.get("end_date"):
                from datetime import date as date_cls
                date_range = DateRange(
                    start_date=date_cls.fromisoformat(dr["start_date"]),
                    end_date=date_cls.fromisoformat(dr["end_date"])
                )

        return cls(
            name=data.get("name", "Neuer Bericht"),
            account_ids=data.get("account_ids", []),
            category_ids=data.get("category_ids", []),
            date_range=date_range,
            fields=data.get("fields", ["Datum", "Betrag", "Kategorie"]),
            grouping=data.get("grouping", ["Kategorie", "Subkategorie"]),
            sort_field=data.get("sort_field", "Datum"),
            sort_order=data.get("sort_order", "asc"),
            show_subtotals=data.get("show_subtotals", True),
            show_grand_total=data.get("show_grand_total", True),
            show_count=data.get("show_count", True),
            show_debit_credit=data.get("show_debit_credit", False),
            column_order=data.get("column_order", []),
            column_widths=data.get("column_widths", [])
        )

    def __repr__(self) -> str:
        """
        Provide a string representation of the ReportConfig object, including
        the count of account IDs, category IDs, fields, and the values of the
        date range and grouping attributes. This is primarily used to display
        the object in a human-readable format for debugging or logging purposes.

        :return: A string describing the details of the `ReportConfig` object.
        :rtype: str
        """
        return (
            f"ReportConfig("
            f"accounts={len(self.account_ids)}, "
            f"categories={len(self.category_ids)}, "
            f"date_range={self.date_range}, "
            f"fields={len(self.fields)}, "
            f"grouping={self.grouping})"
        )


if __name__ == "__main__":
    # Test
    print("=== ReportConfig Test ===\n")

    # Erstelle Config
    config = ReportConfig(
        account_ids=[1, 2],
        category_ids=[10, 20, 30],
        date_range=DateRange.last_year(),
        fields=["Datum", "Betrag", "Kategorie"],
        grouping=["Kategorie", "Subkategorie"]
    )

    print(f"Config: {config}")

    # Validierung
    is_valid, error = config.validate()
    print(f"\nValidierung: {is_valid}")
    if error:
        print(f"Fehler: {error}")

    # Serialisierung
    print("\nSerialisierung:")
    data = config.to_dict()
    print(data)

    # Deserialisierung
    print("\nDeserialisierung:")
    config2 = ReportConfig.from_dict(data)
    print(config2)

    print("\n✓ Roundtrip erfolgreich:", config.to_dict() == config2.to_dict())
