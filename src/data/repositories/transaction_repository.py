"""
===============================================================================
Project   : Hibi-BuRe
Module    : transaction_repository.py
Created   : 13.02.26
Author    : florian
Purpose   : TransactionRepository - transactions data access object

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Optional
from datetime import date
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.engine import Engine
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from src.data.models.domain_models import Transaction, DateRange
from src.business.services.category_matcher import CategoryMatcher


class TransactionRepository:
    """
    Handles operations related to transactions, including fetching, filtering,
    and summarizing transaction data.

    This repository class interacts with a database to retrieve transactions based on
    various filters like date range, account IDs, categories, and more. Additionally,
    it provides features for applying virtual categories, retrieving data in a
    pandas DataFrame for reporting, and summarizing transaction data.

    :ivar engine: SQLAlchemy engine used for database connections and queries.
    :type engine: Engine
    :ivar category_matcher: Component for applying virtual categories to transactions.
    :type category_matcher: CategoryMatcher
    """

    def __init__(self, engine: Engine):
        """
        Initializes an instance of the class with the specified engine and prepares a category
        matcher for use.

        :param engine: Engine instance responsible for processing operations.
        :type engine: Engine
        """
        self.engine = engine
        self.category_matcher = CategoryMatcher(engine)

        # CACHE: Alle Transaktionen einmal laden und dann nur filtern!
        self._all_transactions_cache: Optional[List[Transaction]] = None
        self._cache_loaded = False

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Retrieve a transaction by its unique identifier.

        This method fetches a transaction record from the database using the provided
        transaction identifier. It performs a query to join the transaction data
        with its corresponding category details. If a matching record is found, it
        converts the data row to a Transaction object and returns it. Otherwise, it
        returns None.

        :param transaction_id: The unique identifier of the transaction to be retrieved.
        :type transaction_id: int
        :return: A Transaction object if the transaction exists, otherwise None.
        :rtype: Optional[Transaction]
        """
        query = """
        SELECT
            u.id,
            u.konto_id as account_id,
            u.umsatztyp_id as category_id,
            u.betrag as amount,
            u.datum as booking_date,
            u.valuta as value_date,
            u.zweck as purpose,
            u.zweck2 as purpose2,
            u.gegenkontonummer as counter_account_number,
            u.gegenkontoblz as counter_account_blz,
            u.gegenkonto_name as counter_account_name,
            t.name as category_name
        FROM umsatz u
        LEFT JOIN umsatztyp t ON u.umsatztyp_id = t.id
        WHERE u.id = :id
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"id": transaction_id})
            row = result.first()

            if row:
                return self._row_to_transaction(row)
            return None

    def _load_all_transactions_once(self) -> List[Transaction]:
        """
        Lädt ALLE Transaktionen EINMAL aus der DB, wendet Pattern-Matching an,
        und cached sie. Nachfolgende Aufrufe arbeiten nur noch mit dem Cache!

        :return: Liste aller Transaktionen (prozessiert und kategorisiert)
        """
        if self._cache_loaded and self._all_transactions_cache is not None:
            return self._all_transactions_cache


        # Nur zweck und zweck2 laden (weitere_verwendungszwecke existiert nicht)
        query = """
        SELECT
            u.id,
            u.konto_id as account_id,
            u.umsatztyp_id as category_id,
            u.betrag as amount,
            u.datum as booking_date,
            u.valuta as value_date,
            u.zweck as purpose,
            u.zweck2 as purpose2,
            u.empfaenger_konto as counter_account_number,
            u.empfaenger_blz as counter_account_blz,
            u.empfaenger_name as counter_account_name,
            u.empfaenger_name2 as counter_account_name2,
            u.art as transaction_type,
            t.name as category_name,
            k.bezeichnung as account_name,
            k.kategorie as account_kategorie
        FROM umsatz u
        LEFT JOIN umsatztyp t ON u.umsatztyp_id = t.id
        LEFT JOIN konto k ON u.konto_id = k.id
        ORDER BY u.datum ASC, u.id ASC
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            transactions = [self._row_to_transaction(row) for row in result]

            # Markiere welche Transaktionen ihre Kategorie aus der DB haben
            db_category_ids = {t.id for t in transactions if t.category_id is not None}

            # Pattern-Matching anwenden
            transactions = self._apply_virtual_categories(transactions)

            # flags=1 RAUSFILTERN (NUR DB-Kategorien)
            transactions = self._filter_excluded_categories_db_only(transactions, db_category_ids)

            # Cache setzen
            self._all_transactions_cache = transactions
            self._cache_loaded = True

            return transactions

    def get_by_date_range(
        self,
        date_range: DateRange,
        account_ids: Optional[List[int]] = None,
        category_ids: Optional[List[int]] = None
    ) -> List[Transaction]:
        """
        CACHE-BASIERT: Lädt Daten einmalig beim ersten Aufruf, danach nur Filterung!

        :param date_range: The date range within which transactions are fetched.
        :type date_range: DateRange
        :param account_ids: Optional list of account IDs. If None, no filtering by account.
                            Empty list means no results.
        :type account_ids: Optional[List[int]]
        :param category_ids: Optional list of category IDs for filtering after categorization.
        :type category_ids: Optional[List[int]]
        :return: A list of transactions matching the criteria.
        :rtype: List[Transaction]
        """
        # EINMAL laden (beim ersten Aufruf), danach nur aus Cache filtern!
        all_transactions = self._load_all_transactions_once()

        # Jetzt NUR NOCH FILTERN (keine DB-Zugriffe mehr!)
        transactions = all_transactions

        # Filter 1: Nach KONTO
        if account_ids is not None:
            if len(account_ids) == 0:
                return []
            transactions = [t for t in transactions if t.account_id in account_ids]

        # Filter 2: Nach DATUM (verwende ausgewähltes Datumsfeld)
        from src.data.models.domain_models import DateFieldType
        if date_range.date_field == DateFieldType.BOOKING_DATE:
            transactions = [
                t for t in transactions
                if date_range.start_date <= t.booking_date <= date_range.end_date
            ]
        else:  # VALUE_DATE
            transactions = [
                t for t in transactions
                if date_range.start_date <= t.value_date <= date_range.end_date
            ]

        # Filter 3: Nach KATEGORIEN (wenn ausgewählt)
        if category_ids is not None:
            transactions = self._filter_by_categories(transactions, category_ids)

        # Filter 4: Entferne ALLE Transaktionen mit flags=1 Kategorien
        # (sowohl DB-Kategorien als auch virtuelle Pattern-Kategorien)
        transactions = self._filter_excluded_categories(transactions)

        return transactions

    def get_by_filters(
        self,
        start_date: date,
        end_date: date,
        account_ids: Optional[List[int]] = None,
        category_ids: Optional[List[int]] = None
    ) -> List[Transaction]:
        """
        Fetches a filtered list of transactions based on the provided date range, account
        identifiers, and category identifiers. It utilizes a helper method to retrieve
        matching transactions within the specific date range alongside optional filters
        for accounts and categories.

        :param start_date: The start date of the range within which to filter transactions.
        :type start_date: date
        :param end_date: The end date of the range within which to filter transactions.
        :type end_date: date
        :param account_ids: A list of account IDs to limit the scope of filtered transactions
            to specific accounts. If None, transactions for all accounts are included.
        :type account_ids: Optional[List[int]]
        :param category_ids: A list of category IDs to restrict the filtered transactions
            to specific categories. If None, transactions across all categories are included.
        :type category_ids: Optional[List[int]]
        :return: A list of `Transaction` objects that match the specified filters.
        :rtype: List[Transaction]
        """
        date_range = DateRange(start_date, end_date)
        return self.get_by_date_range(date_range, account_ids, category_ids)

    def get_as_dataframe(
        self,
        date_range: DateRange,
        account_ids: Optional[List[int]] = None,
        category_ids: Optional[List[int]] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Converts a collection of financial transactions into a pandas DataFrame based on the provided
        date range, account IDs, category IDs, and optionally filtered by specific columns. This
        function retrieves transactions, organizes them into a structured format, and allows for
        customized output.

        :param date_range: A DateRange object specifying the start and end dates for filtering
                           transactions.
        :param account_ids: Optional list of integer account IDs to filter transactions by specific
                            accounts. Defaults to None, indicating no account filtering.
        :param category_ids: Optional list of integer category IDs to filter transactions by specific
                             categories. Defaults to None, indicating no category filtering.
        :param columns: Optional list of column names to include in the resulting DataFrame. If
                        specified, the resulting DataFrame will only include the provided columns,
                        along with the `id` column which is always retained. Defaults to None, returning
                        all available columns.
        :return: A pandas DataFrame containing the structured transaction data for the specified filters.
        :rtype: pd.DataFrame
        """
        transactions = self.get_by_date_range(date_range, account_ids, category_ids)

        if not transactions:
            return pd.DataFrame()

        # Konvertiere zu DataFrame
        data = []
        for trans in transactions:
            row = {
                'id': trans.id,
                'Datum': trans.valuta,
                'Betrag': float(trans.amount),
                'Kategorie': trans.category_name or 'ohne Zuordnung',
                'Verwendungszweck': trans.purpose,
                'Gegenkonto': trans.counter_account_name or '',
                'Kontonummer': trans.counter_account_number or '',
                'BLZ': trans.counter_account_blz or '',
                'Konto': trans.account_name or ''
            }
            data.append(row)

        df = pd.DataFrame(data)

        # Filter Spalten wenn angegeben
        if columns:
            # Behalte 'id' immer intern
            cols_to_keep = ['id'] + [col for col in columns if col in df.columns]
            df = df[cols_to_keep]

        return df

    def get_summary(
        self,
        date_range: DateRange,
        account_ids: Optional[List[int]] = None,
        category_ids: Optional[List[int]] = None
    ) -> dict:
        """
        Retrieve a summary of transaction details within a specified date range, filtered by optional
        account and category criteria. The summary includes the count, sum, average, minimum,
        and maximum transaction amounts.

        :param date_range: The range of dates for which transactions should be retrieved.
        :type date_range: DateRange
        :param account_ids: Optional list of account IDs to filter transactions. If None,
            transactions from all accounts are considered.
        :type account_ids: Optional[List[int]]
        :param category_ids: Optional list of category IDs to filter transactions. If None,
            transactions from all categories are considered.
        :type category_ids: Optional[List[int]]
        :return: A dictionary containing a summary of the transactions, including the count,
            sum, average, minimum, and maximum amounts.
        :rtype: dict
        """
        transactions = self.get_by_date_range(date_range, account_ids, category_ids)

        if not transactions:
            return {
                'count': 0,
                'sum': Decimal('0'),
                'avg': Decimal('0'),
                'min': Decimal('0'),
                'max': Decimal('0')
            }

        amounts = [t.amount for t in transactions]

        return {
            'count': len(transactions),
            'sum': sum(amounts),
            'avg': sum(amounts) / len(amounts),
            'min': min(amounts),
            'max': max(amounts)
        }

    def _row_to_transaction(self, row) -> Transaction:
        """
        Converts a database row object into a `Transaction` object.

        This method takes a row object with attributes corresponding to the `Transaction`
        model and constructs a new `Transaction` instance based on the data from the row.

        :param row: A row object containing transaction data with attributes such as
            `id`, `account_id`, `category_id`, `amount`, `valuta`, `purpose`,
            `counter_account_number`, `counter_account_blz`, `counter_account_name`,
            and optionally `category_name` and `account_name`.
        :type row: Any

        :return: A `Transaction` object created from the data in the given row.
        :rtype: Transaction
        """
        # WICHTIG: Hibiscus matcht gegen: empfaenger_name + empfaenger_name2 + zweck
        # NICHT gegen zweck2!
        purpose_orig = getattr(row, 'purpose', None)
        purpose2_orig = getattr(row, 'purpose2', None)
        counter_name = row.counter_account_name
        counter_name2 = getattr(row, 'counter_account_name2', None)

        # Kombiniere für Pattern-Matching: empfaenger_name + empfaenger_name2 + zweck
        match_text_parts = []
        if counter_name:
            match_text_parts.append(counter_name)
        if counter_name2:
            match_text_parts.append(counter_name2)
        if purpose_orig:
            match_text_parts.append(purpose_orig)

        combined_purpose = ' '.join(match_text_parts) if match_text_parts else ''

        # Datumsfelder: Mit Fallback für alte Queries die nur valuta haben
        booking_date = getattr(row, 'booking_date', None)
        value_date = getattr(row, 'value_date', None)

        # Fallback: Wenn neue Felder nicht vorhanden, nutze valuta für beide
        if booking_date is None and value_date is None:
            fallback_date = getattr(row, 'valuta', None)
            booking_date = fallback_date
            value_date = fallback_date
        elif booking_date is None:
            booking_date = value_date
        elif value_date is None:
            value_date = booking_date

        return Transaction(
            id=row.id,
            account_id=row.account_id,
            category_id=row.category_id,
            amount=Decimal(str(row.amount)),
            booking_date=booking_date,
            value_date=value_date,
            purpose=combined_purpose,  # Kombiniert für Pattern-Matching
            counter_account_number=row.counter_account_number,
            counter_account_blz=row.counter_account_blz,
            counter_account_name=row.counter_account_name,
            counter_account_name2=getattr(row, 'counter_account_name2', None),
            category_name=getattr(row, 'category_name', None),
            account_name=getattr(row, 'account_name', None),
            account_kategorie=getattr(row, 'account_kategorie', None),
            transaction_type=getattr(row, 'transaction_type', None),
            purpose_original=purpose_orig,  # Original zweck für Anzeige
            purpose2=purpose2_orig  # Original zweck2
        )

    def _apply_virtual_categories(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Applies virtual categories to transactions that do not have a category assigned.
        The function performs pattern matching on the transaction purposes to identify
        a suitable category and assign it.

        Transactions that remain uncategorized after pattern matching will have their
        category_name set to "ohne Zuordnung" for proper display.

        :param transactions: List of Transaction objects to process. Each Transaction
            should have attributes such as `category_id`, `category_name`, and `purpose`.
        :type transactions: List[Transaction]
        :return: Updated list of Transaction objects, where uncategorized transactions
            may now be assigned a virtual category and corresponding category name.
        :rtype: List[Transaction]
        """
        # Finde alle Buchungen ohne Kategorie
        uncategorized = [t for t in transactions if t.category_id is None]

        if not uncategorized:
            return transactions

        # Hole Category-Namen für gefundene IDs
        category_names = self._get_category_names_for_virtual()

        # Wende Pattern-Matching parallel an (mit Threading für Performance)
        # Nur Threading verwenden wenn genug Transaktionen vorhanden sind
        if len(uncategorized) > 50:
            # Bestimme Anzahl der Worker basierend auf CPU-Cores (max 4)
            max_workers = min(4, os.cpu_count() or 2)

            # Teile Transaktionen in Chunks
            chunk_size = max(50, len(uncategorized) // max_workers)

            def process_chunk(chunk: List[Transaction]) -> List[tuple]:
                """Verarbeite einen Chunk von Transaktionen."""
                results = []
                for trans in chunk:
                    matched_id = self.category_matcher.match_transaction(
                        trans.purpose,
                        trans.account_id,
                        float(trans.amount),
                        trans.account_kategorie
                    )
                    if matched_id:
                        results.append((trans, matched_id))
                return results

            # Erstelle Chunks
            chunks = [uncategorized[i:i + chunk_size] for i in range(0, len(uncategorized), chunk_size)]

            # Verarbeite Chunks parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_chunk, chunk) for chunk in chunks]

                # Sammle Ergebnisse
                for future in as_completed(futures):
                    results = future.result()
                    for trans, matched_id in results:
                        trans.category_id = matched_id
                        trans.category_name = category_names.get(matched_id, "Unbekannt")
        else:
            # Wenige Transaktionen: sequentiell verarbeiten
            for trans in uncategorized:
                matched_id = self.category_matcher.match_transaction(
                    trans.purpose,
                    trans.account_id,
                    float(trans.amount),
                    trans.account_kategorie
                )
                if matched_id:
                    trans.category_id = matched_id
                    trans.category_name = category_names.get(matched_id, "Unbekannt")



        return transactions

    def _get_category_names_for_virtual(self) -> dict:
        """
        Fetches category names for virtual entities from the database.

        This method executes a query to retrieve category IDs and their corresponding
        names from the "umsatztyp" table in the database. The data is returned as a
        dictionary with IDs as keys and names as values.

        :return: A dictionary mapping category IDs to category names.
        :rtype: dict
        """
        query = text("""
            SELECT id, name
            FROM umsatztyp
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query)
            return {row.id: row.name for row in result}

    def _ignore_excluded_categories(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Ignoriert Kategorien mit flags=1, indem category_id und category_name auf None
        gesetzt werden.

        Diese Methode wird NACH der Kategorisierung (fest + Pattern-Matching) angewendet.
        Transaktionen mit flags=1 Kategorien werden NICHT herausgefiltert, sondern ihre
        Kategorie wird auf None gesetzt. Sie erscheinen dann als "ohne Zuordnung".

        :param transactions: Liste aller Transaktionen
        :type transactions: List[Transaction]
        :return: Liste mit Transaktionen, bei denen flags=1 Kategorien ignoriert wurden
        :rtype: List[Transaction]
        """
        excluded_ids = self._get_excluded_category_ids()

        if not excluded_ids:
            return transactions

        # Setze category_id auf None für alle Transaktionen mit flags=1 Kategorien
        for trans in transactions:
            if trans.category_id and trans.category_id in excluded_ids:
                trans.category_id = None
                trans.category_name = None

        return transactions

    def _filter_excluded_categories_db_only(self, transactions: List[Transaction], db_category_ids: set) -> List[Transaction]:
        """
        Filtert Transaktionen mit flags=1 Kategorien heraus, ABER NUR wenn die Kategorie
        aus der DB stammt (nicht virtuell durch Pattern-Matching zugewiesen wurde).

        Hibiscus filtert flags=1 nur bei manuell zugewiesenen Kategorien aus der DB,
        NICHT bei virtuell durch Pattern-Matching zugewiesenen Kategorien!

        :param transactions: Liste aller Transaktionen
        :param db_category_ids: Set mit IDs der Transaktionen, die ihre Kategorie aus DB haben
        :return: Gefilterte Liste ohne ausgeschlossene Kategorien
        """
        excluded_ids = self._get_excluded_category_ids()

        if not excluded_ids:
            return transactions

        # Filtere nur Transaktionen, die:
        # 1. Eine Kategorie haben (category_id not None)
        # 2. Die Kategorie aus der DB haben (id in db_category_ids)
        # 3. Die Kategorie flags=1 hat (category_id in excluded_ids)
        result = []
        for t in transactions:
            if t.category_id is None:
                # Keine Kategorie → behalten
                result.append(t)
            elif t.id in db_category_ids and t.category_id in excluded_ids:
                # DB-Kategorie mit flags=1 → herausfiltern
                pass
            else:
                # Alle anderen → behalten (inkl. virtuelle Kategorien mit flags=1!)
                result.append(t)

        return result

    def _filter_excluded_categories(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Filtert Transaktionen mit Kategorien heraus, die von Auswertungen ausgeschlossen
        werden sollen (flags=1 in umsatztyp Tabelle).

        In Hibiscus können Kategorien als "nicht in Auswertungen berücksichtigen" markiert
        werden. Dies wird über das flags-Feld gesteuert (flags=1).

        Diese Methode wird NACH der Kategorisierung (fest + Pattern-Matching) angewendet.
        Alle Transaktionen mit flags=1 Kategorien werden herausgefiltert, egal ob die
        Kategorie aus der DB stammt oder durch Pattern-Matching zugewiesen wurde.

        Transaktionen ohne Kategorie (category_id = None) werden beibehalten.

        :param transactions: Liste aller Transaktionen
        :type transactions: List[Transaction]
        :return: Gefilterte Liste ohne ausgeschlossene Kategorien
        :rtype: List[Transaction]
        """
        # Hole IDs der ausgeschlossenen Kategorien
        excluded_ids = self._get_excluded_category_ids()

        if not excluded_ids:
            return transactions

        # Filtere ALLE Transaktionen mit flags=1 Kategorien heraus
        # Transaktionen ohne Kategorie (None) bleiben erhalten
        return [t for t in transactions if t.category_id is None or t.category_id not in excluded_ids]
    
    def _get_excluded_category_ids(self) -> set:
        """
        Holt die IDs aller Kategorien, die von Auswertungen ausgeschlossen werden sollen.
        
        :return: Set mit IDs der ausgeschlossenen Kategorien
        :rtype: set
        """
        query = text("""
            SELECT id
            FROM umsatztyp
            WHERE flags = 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return {row.id for row in result}

    def _filter_by_categories(self, transactions: List[Transaction], category_ids: List[int]) -> List[Transaction]:
        """
        Filters a list of transactions to include only those that match the given
        categories. Supports a special case where category ID -1 is used to represent
        transactions with no category.

        :param transactions: A list of transactions to be filtered.
        :param category_ids: A list of category IDs to filter by. The special
                             value -1 is used to filter transactions without a
                             category.
        :return: A filtered list of transactions that match the specified
                 category IDs.
        :rtype: List[Transaction]
        """
        if not category_ids:
            # Leere Liste = zeige nichts
            return []

        # Spezialfall: -1 bedeutet "ohne Kategorie"
        has_without = -1 in category_ids
        regular_ids = [cid for cid in category_ids if cid != -1]

        filtered = []
        for trans in transactions:
            if has_without and trans.category_id is None:
                # Transaktion ohne Kategorie und -1 ist in der Auswahl
                filtered.append(trans)
            elif trans.category_id in regular_ids:
                # Transaktion hat eine der ausgewählten Kategorien
                filtered.append(trans)

        return filtered


if __name__ == "__main__":
    # Test mit echter Datenbank
    from src.config.settings import settings
    from sqlalchemy import create_engine

    print("=== TransactionRepository Test ===\n")

    engine = create_engine(settings.db.connection_string)
    repo = TransactionRepository(engine)

    # Test: Zeitraum 2024
    date_range = DateRange.from_strings("2024-01-01", "2024-12-31")
    print(f"Zeitraum: {date_range}")

    # Hole Transaktionen
    transactions = repo.get_by_date_range(date_range)
    print(f"✓ {len(transactions)} Buchungen gefunden\n")

    if transactions:
        # Erste 3 Buchungen
        print("Erste 3 Buchungen:")
        for trans in transactions[:3]:
            print(f"  {trans.valuta}: {trans.amount_formatted} - {trans.category_name}")

        # Summary
        summary = repo.get_summary(date_range)
        print(f"\nZusammenfassung:")
        print(f"  Anzahl: {summary['count']}")
        print(f"  Summe: {summary['sum']:.2f} €")
        print(f"  Durchschnitt: {summary['avg']:.2f} €")

        # DataFrame
        print("\nDataFrame-Export:")
        df = repo.get_as_dataframe(date_range, columns=['Datum', 'Betrag', 'Kategorie'])
        print(df.head())
