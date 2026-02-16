"""
===============================================================================
Project   : Hibi-BuBu
Module    : category_matcher.py
Created   : 13.02.26
Author    : florian
Purpose   : category matcher service - virtual categorization based on patterns
Applies umsatztyp.pattern rules to transactions to enable automatic categorization
           like in Hibiscus.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass
class CategoryPattern:
    """
    Represents a category pattern with associated attributes and the functionality to match
    a given string against the pattern.

    This class is designed to facilitate categorization or filtering mechanisms by defining
    patterns that can either be regular expressions or plain text substrings. It includes
    attributes to identify and describe the pattern, and an optional category number.

    :ivar id: A unique identifier for the category pattern.
    :type id: int
    :ivar name: The name of the category associated with the pattern.
    :type name: str
    :ivar pattern: The string or regular expression defining the pattern to match.
    :type pattern: str
    :ivar is_regex: Indicates whether the pattern is a regular expression.
    :type is_regex: bool
    :ivar nummer: An optional string representing the category number (e.g., "1.2.3").
    :type nummer: Optional[str]
    :ivar konto_id: Konto-ID für die dieses Pattern gilt (None = alle Konten)
    :type konto_id: Optional[int]
    :ivar konto_kategorie: Kontogruppe für die dieses Pattern gilt (None = alle Konten)
    :type konto_kategorie: Optional[str]
    :ivar umsatztyp: Art des Umsatzes (0=Ausgabe, 1=Einnahme, 2=Egal)
    :type umsatztyp: Optional[int]
    """
    id: int
    name: str
    pattern: str
    is_regex: bool
    nummer: Optional[str] = None  # Kategorienummer (z.B. "1.2.3")
    konto_id: Optional[int] = None  # Konto-Einschränkung
    konto_kategorie: Optional[str] = None  # Kontogruppen-Einschränkung
    umsatztyp: Optional[int] = None  # 0=Ausgabe, 1=Einnahme, 2=Egal
    _compiled_regex: Optional[re.Pattern] = None  # Cached compiled regex pattern
    _has_lookaround: Optional[bool] = None  # Cached lookaround detection
    _has_anchor: Optional[bool] = None  # Cached anchor detection

    def _ensure_compiled(self):
        """Compile regex pattern on first use if this is a regex pattern."""
        if self.is_regex and self._compiled_regex is None:
            try:
                self._compiled_regex = re.compile(self.pattern)
                self._has_lookaround = bool(re.search(r'\(\?[=!<]', self.pattern))
                self._has_anchor = ('^' in self.pattern or '$' in self.pattern) and not self._has_lookaround
            except re.error:
                # Invalid regex - will be handled as plain text
                self._compiled_regex = None
                self._has_lookaround = False
                self._has_anchor = False

    def matches(self, combined_text: str) -> bool:
        """
        Matched das Pattern gegen den kombinierten Text.
        WICHTIG: Hibiscus kombiniert die Felder in ANDERER Reihenfolge oder testet separat!

        :param combined_text: Kombinierter Text aus zweck + zweck2 + counter_account_name
        :type combined_text: str
        :return: A boolean indicating whether the pattern matches the input string.
        :rtype: bool
        """
        if not combined_text or not self.pattern:
            return False

        # Normalisiere Leerzeichen: Multiple Spaces/Tabs/Newlines → Single Space
        # Dies hilft bei Texten wie "Abrechnung 30.12.2024siehe Anlage"
        normalized_text = ' '.join(combined_text.split())

        if self.is_regex:
            # Compile pattern on first use (lazy initialization)
            self._ensure_compiled()

            # If compilation failed, fall back to plain text
            if self._compiled_regex is None:
                return self._plain_text_match(self.pattern, normalized_text)

            # Regex-Matching with pre-compiled pattern
            try:
                if self._has_anchor:
                    # Teste gegen jedes Wort-Segment (durch Leerzeichen getrennt)
                    # Dies simuliert Hibiscus' Verhalten, jedes Feld einzeln zu testen
                    words = normalized_text.split()

                    # Teste verschiedene Kombinationen von aufeinanderfolgenden Wörtern
                    for length in range(len(words), 0, -1):
                        for start in range(len(words) - length + 1):
                            segment = ' '.join(words[start:start+length])
                            if self._compiled_regex.search(segment):
                                return True
                else:
                    # Teste gegen den normalisierten String
                    if self._compiled_regex.search(normalized_text):
                        return True

                    # FALLBACK: Teste Pattern auch in umgekehrter Reihenfolge
                    # (falls Hibiscus counter_account_name VOR zweck kombiniert)
                    # ABER NICHT bei Patterns mit negative/positive lookahead/lookbehind!
                    # Diese würden bei reversed text falsch matchen
                    if not self._has_lookaround:
                        parts = normalized_text.split()
                        reversed_text = ' '.join(reversed(parts))
                        if self._compiled_regex.search(reversed_text):
                            return True

                return False

            except re.error:
                # Ungültiger Regex - als Plain Text behandeln
                return self._plain_text_match(self.pattern, normalized_text)
        else:
            # Plain Text Substring-Suche mit flexiblem Leerzeichen-Matching
            return self._plain_text_match(self.pattern, normalized_text)

    def _plain_text_match(self, pattern: str, text: str) -> bool:
        """
        Plain-Text Matching mit flexiblem Leerzeichen-Handling.

        Hibiscus matcht "siehe Anlage" auch gegen "Abrechnung30.12.2024sieheAnlage",
        indem es Leerzeichen im Pattern flexibel behandelt.

        :param pattern: Das Suchmuster (z.B. "siehe Anlage")
        :param text: Der zu durchsuchende Text
        :return: True wenn gefunden
        """
        pattern_lower = pattern.lower()
        text_lower = text.lower()

        # Standard: Exaktes Substring-Matching
        if pattern_lower in text_lower:
            return True

        # FALLBACK: Ersetze Leerzeichen im Pattern durch \s* (beliebig viele Whitespace)
        # Dies matched "siehe Anlage" auch gegen "sieheAnlage" oder "siehe  Anlage"
        # WICHTIG: re.escape() escaped KEINE Leerzeichen! Die bleiben normal.
        # Also ersetze ich ' ' (normales Space) durch '\s*'
        pattern_regex = re.escape(pattern_lower).replace(' ', r'\s*')
        try:
            return bool(re.search(pattern_regex, text_lower))
        except re.error:
            pass

        return False


class CategoryMatcher:
    """
    Manages the matching of transactions to pre-defined categories based on patterns.

    The CategoryMatcher class is responsible for loading categorization rules (patterns)
    from a database and using these rules to determine the category of transactions.
    It supports matching individual transactions, bulk matching for multiple transactions,
    and retrieval of specific or all patterns.

    :ivar engine: The SQLAlchemy engine used for database access.
    :type engine: Engine
    """

    def __init__(self, engine: Engine):
        """
        Initializes a new instance of the class.

        :param engine: The engine instance to be used.

        :ivar engine: The engine instance provided during initialization.
        :type engine: Engine
        """
        self.engine = engine
        self._patterns: List[CategoryPattern] = []
        self._patterns_loaded = False

    def load_patterns(self) -> None:
        """
        Loads patterns from the database and processes them into a list of
        `CategoryPattern` objects. Patterns are fetched based on specific conditions
        where the `pattern` column is not null or empty.

        The query is executed on the database connected via the `engine` attribute
        and retrieves relevant fields for each pattern in ascending order of their IDs.
        The resulting patterns are stored in the internal data structure.

        :raises sqlalchemy.exc.SQLAlchemyError: If there is an issue connecting
            to or querying the database during execution.
        :return: None
        """
        # Lade ALLE Patterns (flags-Filterung machen wir in Python, falls SQL-Spalte fehlt)
        query = text("""
            SELECT
                id,
                name,
                pattern,
                isregex,
                nummer,
                umsatztyp,
                konto_id,
                konto_kategorie
            FROM umsatztyp
            WHERE pattern IS NOT NULL AND pattern != ''
            ORDER BY nummer ASC, id ASC
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query)
            self._patterns = []

            for row in result:
                pattern = CategoryPattern(
                    id=row.id,
                    name=row.name,
                    pattern=row.pattern,
                    is_regex=bool(row.isregex),
                    nummer=row.nummer,
                    konto_id=row.konto_id,
                    konto_kategorie=row.konto_kategorie,
                    umsatztyp=row.umsatztyp
                )
                self._patterns.append(pattern)

            # WICHTIG: flags=1 Patterns WERDEN geladen und gematch!
            # Die Filterung nach flags=1 passiert bei der ANZEIGE, nicht hier!

        self._patterns_loaded = True

    def match_transaction(self, zweck: str, account_id: Optional[int] = None, amount: Optional[float] = None, account_kategorie: Optional[str] = None) -> Optional[int]:
        """
        Matches a given transaction description (`zweck`) against preloaded patterns
        to identify and return the ID of the matching pattern. The patterns are
        evaluated in order of ascending priority (based on ID).

        :param zweck: The transaction description to be matched.
        :type zweck: str
        :param account_id: Optional account ID for pattern filtering
        :type account_id: Optional[int]
        :param amount: Optional transaction amount for umsatztyp filtering
        :type amount: Optional[float]
        :param account_kategorie: Optional account category for pattern filtering
        :type account_kategorie: Optional[str]
        :return: The ID of the matching pattern, or None if no match is found.
        :rtype: Optional[int]
        """
        if not self._patterns_loaded:
            self.load_patterns()

        if not zweck:
            return None

        # Durchlaufe alle Patterns in Reihenfolge (Priorität = nummer, dann id aufsteigend)
        for pattern in self._patterns:
            # Prüfe Konto-Einschränkung
            if pattern.konto_id is not None and account_id is not None:
                if pattern.konto_id != account_id:
                    # Pattern gilt nicht für dieses Konto
                    continue

            # Prüfe Kontogruppen-Einschränkung (konto_kategorie)
            if pattern.konto_kategorie is not None and account_kategorie is not None:
                if pattern.konto_kategorie != account_kategorie:
                    # Pattern gilt nicht für diese Kontogruppe
                    continue

            # Prüfe Art des Umsatzes (Einnahme/Ausgabe)
            if pattern.umsatztyp is not None and amount is not None:
                if pattern.umsatztyp == 1 and amount < 0:
                    # Pattern nur für Einnahmen, aber Transaktion ist Ausgabe
                    continue
                elif pattern.umsatztyp == 0 and amount > 0:
                    # Pattern nur für Ausgaben, aber Transaktion ist Einnahme
                    continue
                elif pattern.umsatztyp == 0 and amount == 0:
                    # Pattern nur für Ausgaben, aber Transaktion ist Null
                    continue
                # umsatztyp == 2 (Egal) -> keine Einschränkung

            # Pattern-Matching
            if pattern.matches(zweck):
                return pattern.id

        return None

    def match_transactions_bulk(self, transactions: List[Tuple[int, str]]) -> dict:
        """
        Matches multiple transactions to their respective categories in bulk based on predefined patterns.

        This function takes a list of transactions, where each transaction is a tuple containing
        a transaction ID and a descriptive string. It attempts to match each transaction to a
        specific category using predefined patterns, which must be loaded prior to executing
        the matching process. The function returns a dictionary where the keys are transaction IDs
        and the values are the matched category IDs.

        :param transactions: A list of tuples, where each tuple consists of an integer transaction
            ID and a string describing the transaction purpose (e.g., payment description).
        :type transactions: List[Tuple[int, str]]
        :return: A dictionary where the keys are transaction IDs and the values are the matched
            category IDs. If a transaction cannot be matched, it will not appear in the result.
        :rtype: dict
        """
        if not self._patterns_loaded:
            self.load_patterns()

        result = {}

        for tx_id, zweck in transactions:
            category_id = self.match_transaction(zweck)
            if category_id:
                result[tx_id] = category_id

        return result

    def get_pattern_by_id(self, category_id: int) -> Optional[CategoryPattern]:
        """
        Retrieves a pattern associated with the specified category ID.

        This method searches through the loaded patterns to find one that matches the
        provided category ID. If patterns are not yet loaded, it will trigger the
        process to load them first. If no matching pattern is found, it returns None.

        :param category_id: The unique identifier of the category for which the
            associated pattern is to be retrieved.
        :type category_id: int
        :return: The pattern associated with the given category ID, or None if no
            pattern is found.
        :rtype: Optional[CategoryPattern]
        """
        if not self._patterns_loaded:
            self.load_patterns()

        for pattern in self._patterns:
            if pattern.id == category_id:
                return pattern

        return None

    def get_all_patterns(self) -> List[CategoryPattern]:
        """
        Retrieve all category patterns.

        This method returns a copy of the loaded category patterns. If the patterns are
        not yet loaded, it invokes the `load_patterns` method to dynamically load them
        before returning the result. The patterns returned represent the current state
        of loaded category patterns at the time of the call.

        :return: A copy of the list of category patterns.
        :rtype: List[CategoryPattern]
        """
        if not self._patterns_loaded:
            self.load_patterns()

        return self._patterns.copy()


if __name__ == "__main__":
    # Test
    print("=== CategoryMatcher Test ===\n")

    # Simuliere Patterns
    test_patterns = [
        CategoryPattern(1, "Supermarkt", "REWE", False),
        CategoryPattern(2, "Discount", "^ALDI.*", True),
        CategoryPattern(3, "Tankstelle", "Shell|Aral|Jet", True),
    ]

    test_transactions = [
        "Einkauf bei REWE Markt",
        "ALDI SÜD Filiale 123",
        "Shell Station Hauptstraße",
        "Amazon Marketplace",
        "Überweisung an Max Mustermann"
    ]

    print("Test-Patterns:")
    for p in test_patterns:
        print(f"  [{p.id}] {p.name}: '{p.pattern}' (regex={p.is_regex})")

    print("\nTest-Transaktionen:")
    for i, tx in enumerate(test_transactions):
        print(f"  [{i}] {tx}")

        # Teste Matching
        for pattern in test_patterns:
            if pattern.matches(tx):
                print(f"      → Match: {pattern.name}")
                break
        else:
            print(f"      → Keine Kategorie")

    print("\n✓ Test abgeschlossen")
