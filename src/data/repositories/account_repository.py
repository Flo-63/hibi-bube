"""
===============================================================================
Project   : Hibi-BuRe
Module    : account_repository.py
Created   : 13.02.26
Author    : florian
Purpose   : AccountRepository - Data Access Object for accounts

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.data.models.domain_models import Account


class AccountRepository:
    """
    Manages and retrieves account-related data from the database.

    The class provides methods to interact with the account storage, including retrieving all accounts, fetching
    accounts by ID or multiple IDs, and searching accounts using a specified search term. The returned data is
    transformed into `Account` objects for usability.

    :ivar engine: Database engine used for executing queries and managing connections.
    :type engine: Engine
    """

    def __init__(self, engine: Engine):
        """
        Represents the initialization of a component or system with an engine instance.

        This constructor is responsible for setting up the primary engine attribute
        for the object. The provided engine instance is expected to conform to the
        interface or type defined. This serves as a foundational component for
        further operations or functionality dependent on the engine.

        :param engine: The primary engine instance to be used.
        :type engine: Engine
        """
        self.engine = engine

    def get_all(self) -> List[Account]:
        """
        Retrieves all accounts from the database with their details ordered
        by their name in ascending order.

        This method fetches account records from the `konto` table, and each
        record is transformed into an Account object before being returned
        as part of a list.

        :param self: The instance of the class that contains the database engine
                     and the method to transform database rows into account objects.

        :returns: A list of Account objects containing account details such as
                  account number, name, bank code, IBAN, and BIC.
        :rtype: List[Account]
        """
        query = """
        SELECT
            id,
            kontonummer as account_number,
            bezeichnung as name,
            blz,
            iban,
            bic,
            kategorie
        FROM konto
        ORDER BY bezeichnung ASC
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [self._row_to_account(row) for row in result]

    def get_by_id(self, account_id: int) -> Optional[Account]:
        """
        Retrieves an account by its unique identifier from the database. If the account
        exists, it is returned as an Account instance; otherwise, None is returned.

        :param account_id: The unique identifier of the account to be retrieved.
        :type account_id: int
        :return: An Account instance if the account exists; otherwise, None.
        :rtype: Optional[Account]
        """
        query = """
        SELECT
            id,
            kontonummer as account_number,
            bezeichnung as name,
            blz,
            iban,
            bic,
            kategorie
        FROM konto
        WHERE id = :id
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"id": account_id})
            row = result.first()

            if row:
                return self._row_to_account(row)
            return None

    def get_by_ids(self, account_ids: List[int]) -> List[Account]:
        """Retrieve a list of Account objects based on their unique IDs.

        This method takes a list of account IDs, performs a query against the
        database to retrieve the corresponding accounts, and returns them
        as a list of Account objects. The results are ordered by account name
        (alphabetically).

        :param account_ids: A list of integers representing the IDs of the
                            accounts to retrieve.
        :return: A list of Account objects corresponding to the provided
                 account IDs. If no IDs are provided, an empty list is
                 returned.
        :rtype: List[Account]
        """
        if not account_ids:
            return []

        placeholders = ','.join([f':id{i}' for i in range(len(account_ids))])
        query = f"""
        SELECT
            id,
            kontonummer as account_number,
            bezeichnung as name,
            blz,
            iban,
            bic,
            kategorie
        FROM konto
        WHERE id IN ({placeholders})
        ORDER BY bezeichnung ASC
        """

        params = {f'id{i}': acc_id for i, acc_id in enumerate(account_ids)}

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [self._row_to_account(row) for row in result]

    def search(self, search_term: str) -> List[Account]:
        """
        Searches for accounts in the database that match the given search term. The search
        operation is case-insensitive and matches substrings within the account name,
        account number, or IBAN. Results are ordered alphabetically by the account name.

        :param search_term: A string representing the search criterion. Substrings of the
            account name, account number, and IBAN will be matched against this value.
        :type search_term: str
        :return: A list of `Account` objects that match the search term.
        :rtype: List[Account]
        """
        query = """
        SELECT
            id,
            kontonummer as account_number,
            bezeichnung as name,
            blz,
            iban,
            bic,
            kategorie
        FROM konto
        WHERE LOWER(bezeichnung) LIKE :search_term
           OR LOWER(kontonummer) LIKE :search_term
           OR LOWER(iban) LIKE :search_term
        ORDER BY bezeichnung ASC
        """

        search_pattern = f"%{search_term.lower()}%"

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"search_term": search_pattern})
            return [self._row_to_account(row) for row in result]

    def _row_to_account(self, row) -> Account:
        """
        Converts a database row object to an Account object.

        This function takes a database row object and maps its attributes to construct
        and return an Account instance. Attributes of the row object that are `None`
        default to appropriate empty or fallback values.

        :param row: A database row object containing fields for creating an Account.
        :type row: Any
        :return: An Account instance created with values from the provided row object.
        :rtype: Account
        """
        # WICHTIG: H2 ignoriert SQL AS Aliase, nutze Original-Spaltennamen
        # Versuche zuerst Aliase (SQLAlchemy), dann Original-Namen (H2)
        return Account(
            id=row.id,
            account_number=getattr(row, 'account_number', None) or getattr(row, 'kontonummer', '') or '',
            name=getattr(row, 'name', None) or getattr(row, 'bezeichnung', '') or '',
            blz=row.blz,
            iban=row.iban,
            bic=row.bic,
            kategorie=row.kategorie
        )


if __name__ == "__main__":
    # Test mit echter Datenbank
    from src.config.settings import settings
    from sqlalchemy import create_engine

    print("=== AccountRepository Test ===\n")

    engine = create_engine(settings.db.connection_string)
    repo = AccountRepository(engine)

    # Alle Konten
    accounts = repo.get_all()
    print(f"✓ {len(accounts)} Konten gefunden\n")

    if accounts:
        print("Konten:")
        for acc in accounts:
            print(f"  [{acc.id}] {acc.display_name}")
            if acc.iban:
                print(f"      IBAN: {acc.iban}")
