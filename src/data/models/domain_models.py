"""
===============================================================================
Project   : Hibi-BuRe
Module    : domain_models.py
Created   : 13.02.26
Author    : florian
Purpose   : Domain Models - Classes to represent data entities

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Optional
from enum import Enum


class DateFieldType(Enum):
    """
    Enum für Datumsfeld-Auswahl bei Transaktionen.

    :cvar BOOKING_DATE: Buchungsdatum (u.datum)
    :cvar VALUE_DATE: Valuta/Wertstellung (u.valuta)
    """
    BOOKING_DATE = "booking_date"  # Buchungsdatum
    VALUE_DATE = "value_date"  # Valuta/Wertstellung


@dataclass
class Transaction:
    """
    Represents a financial transaction.

    This class is designed to model a basic financial transaction, including details such as
    the associated account, category, amount, date, and other optional metadata about the
    transaction. It can be used in financial applications for tracking expenses, incomes, or
    other account operations.

    :ivar id: Unique identifier for the transaction.
    :type id: int
    :ivar account_id: Identifier for the associated account.
    :type account_id: int
    :ivar category_id: Identifier for the transaction category, if applicable.
    :type category_id: Optional[int]
    :ivar amount: The amount of the transaction as a decimal value.
    :type amount: Decimal
    :ivar valuta: Booking date of the transaction.
    :type valuta: date
    :ivar purpose: Purpose or description of the transaction.
    :type purpose: str
    :ivar counter_account_number: Account number of the counterparty, if available.
    :type counter_account_number: Optional[str]
    :ivar counter_account_blz: Bank code (BLZ) of the counterparty, if available.
    :type counter_account_blz: Optional[str]
    :ivar counter_account_name: Name of the counterparty, if available.
    :type counter_account_name: Optional[str]
    :ivar category_name: Name of the transaction category, if available.
    :type category_name: Optional[str]
    :ivar account_name: Name of the associated account, if available.
    :type account_name: Optional[str]
    """
    id: int
    account_id: int
    category_id: Optional[int]
    amount: Decimal
    booking_date: date  # u.datum - Buchungsdatum
    value_date: date  # u.valuta - Wertstellung
    purpose: str  # Kombinierter Text für Pattern-Matching (empfaenger + zweck + zweck2)
    counter_account_number: Optional[str] = None
    counter_account_blz: Optional[str] = None
    counter_account_name: Optional[str] = None
    counter_account_name2: Optional[str] = None

    # Zusatzfelder (optional)
    category_name: Optional[str] = None
    account_name: Optional[str] = None
    account_kategorie: Optional[str] = None  # k.kategorie für Pattern-Matching
    transaction_type: Optional[str] = None  # u.art (ENTGELTABSCHLUSS, ÜBERTRAG, etc.)

    # Original Felder für Anzeige und Anchor-Pattern-Matching
    purpose_original: Optional[str] = None  # u.zweck - original zweck Feld
    purpose2: Optional[str] = None  # u.zweck2 - original zweck2 Feld

    # Legacy-Property für Rückwärtskompatibilität
    @property
    def valuta(self) -> date:
        """Alias für value_date (Rückwärtskompatibilität)"""
        return self.value_date

    def __post_init__(self):
        """Konvertiert Typen falls nötig"""
        if isinstance(self.amount, str):
            self.amount = Decimal(self.amount)
        elif isinstance(self.amount, (int, float)):
            self.amount = Decimal(str(self.amount))
        if isinstance(self.booking_date, str):
            from datetime import datetime
            self.booking_date = datetime.strptime(self.booking_date, '%Y-%m-%d').date()
        if isinstance(self.value_date, str):
            from datetime import datetime
            self.value_date = datetime.strptime(self.value_date, '%Y-%m-%d').date()

    @property
    def amount_formatted(self) -> str:
        """Formatierter Betrag mit Euro-Zeichen"""
        return f"{self.amount:.2f} €"


@dataclass
class Category:
    """
    Represents a category with a hierarchical name structure.

    WICHTIG: Hibiscus nutzt parent_id für Hierarchien, NICHT ":" im Namen!
    Die Hierarchie wird aus parent_id rekursiv aufgebaut.

    :ivar id: Unique identifier for the category.
    :type id: int
    :ivar name: The name of the category (ohne Hierarchie-Trenner!).
    :type name: str
    :ivar parent_id: ID der übergeordneten Kategorie (NULL für Root-Kategorien).
    :type parent_id: Optional[int]
    :ivar hierarchy: A list representing the hierarchical structure of the category, derived
        from its name. If not provided, it will be parsed from the name.
    :type hierarchy: List[str]
    """
    id: int
    name: str
    parent_id: Optional[int] = None
    hierarchy: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Parst die Hierarchie aus dem Namen"""
        if not self.hierarchy:
            self.hierarchy = self._parse_hierarchy()

    def _parse_hierarchy(self) -> List[str]:
        """
        Parst Kategorie-Hierarchie aus dem Namen

        Beispiele:
        - "Versicherungen" -> ["Versicherungen"]
        - "Versicherungen:KFZ" -> ["Versicherungen", "KFZ"]
        - "Versicherungen:KFZ:Allianz" -> ["Versicherungen", "KFZ", "Allianz"]
        """
        return self.name.split(":")

    @property
    def level(self) -> int:
        """Hierarchie-Ebene (0=Kategorie, 1=Subkategorie, 2=Gruppe)"""
        return len(self.hierarchy) - 1

    @property
    def main_category(self) -> str:
        """Hauptkategorie (erste Ebene)"""
        return self.hierarchy[0] if self.hierarchy else ""

    @property
    def subcategory(self) -> Optional[str]:
        """Subkategorie (zweite Ebene)"""
        return self.hierarchy[1] if len(self.hierarchy) > 1 else None

    @property
    def group(self) -> Optional[str]:
        """Gruppe (dritte Ebene)"""
        return self.hierarchy[2] if len(self.hierarchy) > 2 else None

    def matches_pattern(self, pattern: str) -> bool:
        """
        Prüft ob Kategorie zu einem Pattern passt

        Pattern-Beispiele:
        - "Versicherungen" -> matcht nur "Versicherungen"
        - "Versicherungen:*" -> matcht alle mit "Versicherungen:" Prefix
        - "*:KFZ" -> matcht alle mit ":KFZ" im Namen
        """
        if pattern.endswith(":*"):
            prefix = pattern[:-2]
            return self.name.startswith(prefix + ":")
        elif pattern.startswith("*:"):
            suffix = pattern[1:]
            return suffix in self.name
        else:
            return self.name == pattern


@dataclass
class Account:
    """
    Represents a financial account with relevant details.

    This class is used to encapsulate the attributes of a financial account,
    such as account ID, account number, name, and optionally, bank-specific
    details like bank code (BLZ), IBAN, and BIC. It provides a structured
    representation for account-related operations and data storage.

    :ivar id: Unique identifier for the account.
    :type id: int
    :ivar account_number: The account number associated with the account.
    :type account_number: str
    :ivar name: The name of the account holder or associated entity.
    :type name: str
    :ivar blz: Optional bank code (Bankleitzahl) associated with the account.
    :type blz: Optional[str]
    :ivar iban: Optional International Bank Account Number (IBAN).
    :type iban: Optional[str]
    :ivar bic: Optional Bank Identifier Code (BIC).
    :type bic: Optional[str]
    :ivar kategorie: Optional account category/group for pattern matching.
    :type kategorie: Optional[str]
    """
    id: int
    account_number: str
    name: str
    blz: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    kategorie: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Anzeigename für GUI (Kontonummer + Name)"""
        return f"{self.account_number} - {self.name}"


@dataclass
class DateRange:
    """
    Represents a range of dates with a start date and an end date.

    This class is used to encapsulate a range of dates, ensuring that the start date always
    precedes or equals the end date. It provides methods to create instances based on specific
    criteria, such as for the current year or the previous year, and supports string-based
    initialization.

    :ivar start_date: The starting date of the range.
    :type start_date: date
    :ivar end_date: The ending date of the range.
    :type end_date: date
    :ivar date_field: Which date field to use (booking_date or value_date).
    :type date_field: DateFieldType
    """
    start_date: date
    end_date: date
    date_field: DateFieldType = DateFieldType.BOOKING_DATE  # Default: Buchungsdatum

    def __post_init__(self):
        """Validierung"""
        if self.start_date > self.end_date:
            raise ValueError(f"start_date ({self.start_date}) muss vor end_date ({self.end_date}) liegen")

    @classmethod
    def from_strings(cls, start: str, end: str) -> 'DateRange':
        """Erstellt DateRange aus String-Datumsangaben (YYYY-MM-DD)"""
        from datetime import datetime
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        return cls(start_date, end_date)

    @classmethod
    def current_year(cls) -> 'DateRange':
        """Aktuelles Jahr"""
        from datetime import datetime
        year = datetime.now().year
        return cls(date(year, 1, 1), date(year, 12, 31))

    @classmethod
    def last_year(cls) -> 'DateRange':
        """Letztes Jahr"""
        from datetime import datetime
        year = datetime.now().year - 1
        return cls(date(year, 1, 1), date(year, 12, 31))

    def __str__(self) -> str:
        return f"{self.start_date} bis {self.end_date}"


if __name__ == "__main__":
    # Tests
    print("=== Domain Models Test ===\n")

    # Test Category
    cat1 = Category(1, "Versicherungen")
    print(f"Kategorie: {cat1.name}")
    print(f"  Level: {cat1.level}, Main: {cat1.main_category}")
    print(f"  Hierarchy: {cat1.hierarchy}\n")

    cat2 = Category(2, "Versicherungen:KFZ:Allianz")
    print(f"Kategorie: {cat2.name}")
    print(f"  Level: {cat2.level}")
    print(f"  Main: {cat2.main_category}, Sub: {cat2.subcategory}, Group: {cat2.group}")
    print(f"  Matches 'Versicherungen:*': {cat2.matches_pattern('Versicherungen:*')}")
    print(f"  Hierarchy: {cat2.hierarchy}\n")

    # Test Transaction
    trans = Transaction(
        id=1,
        account_id=1,
        category_id=2,
        amount="-123.45",
        valuta="2024-01-15",
        purpose="Test-Buchung",
        category_name="Versicherungen:KFZ:Allianz"
    )
    print(f"Transaction: {trans.amount_formatted} am {trans.valuta}")
    print(f"  Purpose: {trans.purpose}\n")

    # Test DateRange
    dr = DateRange.last_year()
    print(f"Letztes Jahr: {dr}")

    dr2 = DateRange.from_strings("2024-01-01", "2024-12-31")
    print(f"2024: {dr2}")
