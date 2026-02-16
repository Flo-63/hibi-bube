"""
===============================================================================
Project   : Hibi-BuRe
Module    : category_repository.py
Created   : 13.02.26
Author    : florian
Purpose   : CategoryRepository - Data Access Object for categories

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.data.models.domain_models import Category


class CategoryRepository:
    """
    Provides functionality for retrieving and managing categories from a database.

    This class is responsible for fetching, searching, and structuring categories
    from a database. It interacts with the database using an Engine object to
    execute SQL queries and transform the results into Category objects,
    or related structures like dictionaries or hierarchical representations.

    :ivar engine: The database engine used for executing SQL queries.
    :type engine: Engine
    """

    def __init__(self, engine: Engine):
        """
        Initializes the object with a specified engine instance.

        :param engine: An instance of the Engine class to be assigned
            to the object.
        :type engine: Engine
        """
        self.engine = engine

    def build_hierarchy_path(self, category_id: int, all_categories: Optional[List[Category]] = None) -> List[str]:
        """
        Baut den vollständigen Hierarchie-Pfad für eine Kategorie auf.
        Nutzt parent_id rekursiv um den Pfad von Root bis zur Kategorie zu erstellen.

        Beispiel: Für "Test8" mit parent-chain Test1->Test2->...->Test8
        ergibt das: ["Test1", "Test2", "Test3", "Test4", "Test5", "Test6", "Test7", "Test8"]

        :param category_id: Die ID der Kategorie
        :param all_categories: Optional: Alle Kategorien als Liste (für Performance)
        :return: Liste der Kategorie-Namen von Root bis zur Ziel-Kategorie
        """
        if all_categories is None:
            all_categories = self.get_all()

        # Erstelle Lookup-Dict für schnellen Zugriff
        cat_dict = {cat.id: cat for cat in all_categories}

        # Rekursiv den Pfad aufbauen
        def build_path(cat_id: int) -> List[str]:
            if cat_id not in cat_dict:
                return []

            cat = cat_dict[cat_id]

            # Wenn keine Parent-ID: Das ist die Root-Kategorie
            if cat.parent_id is None:
                return [cat.name]

            # Sonst: Parent-Pfad + eigener Name
            parent_path = build_path(cat.parent_id)
            return parent_path + [cat.name]

        return build_path(category_id)

    def get_all(self) -> List[Category]:
        """
        Retrieves all Category records from the database ordered by name in ascending
        order. Lädt parent_id und berechnet Hierarchie für jede Kategorie.

        :raises sqlalchemy.exc.SQLAlchemyError: If there is an issue with the database
            connection or query execution.
        :return: A list of Category objects representing all records in the database.
        :rtype: List[Category]
        """
        query = "SELECT id, name, parent_id FROM umsatztyp ORDER BY name ASC"

        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            categories = [Category(id=row.id, name=row.name, parent_id=row.parent_id) for row in result]

        # Berechne Hierarchie für jede Kategorie
        for cat in categories:
            cat.hierarchy = self.build_hierarchy_path(cat.id, categories)

        return categories

    def get_all_as_dict(self) -> Dict[int, str]:
        """
        Retrieves all categories and represents them as a dictionary where the
        keys are category IDs and the values are category names.

        :returns: A dictionary mapping category IDs to their corresponding names.
        :rtype: Dict[int, str]
        """
        categories = self.get_all()
        return {cat.id: cat.name for cat in categories}

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """
        Retrieve a specific category by its unique identifier.

        This function queries the database for a category record that matches the provided
        category identifier. If the category exists, it returns an instance of the `Category`
        object containing the corresponding data; otherwise, it returns `None`.

        :param category_id: The unique identifier of the category to be retrieved.
        :type category_id: int
        :return: A `Category` object if the provided identifier matches an existing category,
            otherwise `None`.
        :rtype: Optional[Category]
        """
        query = "SELECT id, name, parent_id FROM umsatztyp WHERE id = :id"

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"id": category_id})
            row = result.first()

            if row:
                return Category(id=row.id, name=row.name, parent_id=row.parent_id)
            return None

    def get_by_ids(self, category_ids: List[int]) -> List[Category]:
        """
        Retrieves a list of categories based on their IDs.

        This method queries a database table to fetch category details, including `id`
        and `name`, for the specified list of category IDs. If the input list of IDs
        is empty, an empty list is immediately returned. The query is executed using
        a dynamically generated placeholder list for prepared statements to prevent
        SQL injection.

        :param category_ids: A list of integers representing the IDs of the categories
            to be retrieved. Pass an empty list to return an empty result.
        :type category_ids: List[int]
        :return: A list of `Category` objects corresponding to the provided IDs. If no
            IDs match or the input list is empty, an empty list is returned.
        :rtype: List[Category]
        """
        if not category_ids:
            return []

        # Erstelle Platzhalter für IN-Clause
        placeholders = ','.join([f':id{i}' for i in range(len(category_ids))])
        query = f"SELECT id, name, parent_id FROM umsatztyp WHERE id IN ({placeholders})"

        # Erstelle Parameter-Dictionary
        params = {f'id{i}': cat_id for i, cat_id in enumerate(category_ids)}

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [Category(id=row.id, name=row.name, parent_id=row.parent_id) for row in result]

    def get_by_pattern(self, pattern: str) -> List[Category]:
        """
        Filters and retrieves categories that match the given pattern.

        This method retrieves all available categories and returns a filtered list of
        categories whose attributes match the specified pattern.

        :param pattern: The pattern to match against category attributes.
        :type pattern: str
        :return: A list of categories that match the given pattern.
        :rtype: List[Category]
        """
        all_categories = self.get_all()
        return [cat for cat in all_categories if cat.matches_pattern(pattern)]

    def get_main_categories(self) -> List[str]:
        """
        Retrieves and returns a sorted list of unique main categories derived
        from all available categories.

        This function processes a list of categories obtained from
        the `get_all` method. It extracts the unique main categories
        from the dataset and returns them in a sorted order.

        :return: A sorted list of unique main categories.
        :rtype: List[str]
        """
        all_categories = self.get_all()
        main_cats = {cat.main_category for cat in all_categories}
        return sorted(main_cats)

    def get_subcategories(self, main_category: str) -> List[str]:
        """
        Retrieves a list of subcategories associated with a specified main category.

        This method fetches a collection of all categories, filters them based on
        the provided main category, and returns a sorted list of unique subcategories
        that belong to it.

        :param main_category: The main category for which subcategories are to be retrieved.
        :type main_category: str
        :return: A sorted list of subcategories belonging to the specified main category.
        :rtype: List[str]
        """
        all_categories = self.get_all()
        subcats = {
            cat.subcategory
            for cat in all_categories
            if cat.main_category == main_category and cat.subcategory
        }
        return sorted(subcats)

    def get_hierarchy_tree(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Builds and returns a hierarchical tree structure representing categories and
        their relationships, including main categories, subcategories, and groups.

        The hierarchy tree is constructed as a nested dictionary. The outermost
        dictionary represents main categories as keys. Each main category maps to a
        dictionary of subcategories. The subcategory dictionary maps subcategories to
        lists of groups under them.

        :return: A dictionary representing the hierarchy tree, where keys are main
            categories, values are dictionaries of subcategories, and subcategories map
            to lists of groups.
        :rtype: Dict[str, Dict[str, List[str]]]
        """
        all_categories = self.get_all()
        tree = {}

        for cat in all_categories:
            main = cat.main_category
            if main not in tree:
                tree[main] = {}

            if cat.subcategory:
                sub = cat.subcategory
                if sub not in tree[main]:
                    tree[main][sub] = []

                if cat.group:
                    tree[main][sub].append(cat.group)

        return tree

    def search(self, search_term: str) -> List[Category]:
        """
        Searches for categories in the database whose names match the given search term.

        This method performs a case-insensitive search on the `name` field of the
        `umsatztyp` table. The results are ordered alphabetically by the `name` of
        the categories before being returned as a list of `Category` objects.

        :param search_term: The string to search for, which will be matched against
            the category names in a case-insensitive manner.
        :type search_term: str
        :return: A list of `Category` objects whose names match the given search term.
        :rtype: List[Category]
        """
        query = """
        SELECT id, name
        FROM umsatztyp
        WHERE LOWER(name) LIKE :search_term
        ORDER BY name ASC
        """

        search_pattern = f"%{search_term.lower()}%"

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"search_term": search_pattern})
            return [Category(id=row.id, name=row.name) for row in result]


if __name__ == "__main__":
    # Test mit echter Datenbank
    from src.config.settings import settings
    from sqlalchemy import create_engine

    print("=== CategoryRepository Test ===\n")

    engine = create_engine(settings.db.connection_string)
    repo = CategoryRepository(engine)

    # Test: Alle Kategorien
    all_cats = repo.get_all()
    print(f"✓ {len(all_cats)} Kategorien geladen")

    # Test: Hierarchie-Baum
    tree = repo.get_hierarchy_tree()
    print(f"✓ {len(tree)} Hauptkategorien gefunden\n")

    # Beispiel-Ausgabe
    print("Erste 5 Kategorien:")
    for cat in all_cats[:5]:
        print(f"  [{cat.id}] {cat.name} (Level {cat.level})")

    print("\nHauptkategorien:")
    main_cats = repo.get_main_categories()
    for main in main_cats[:5]:
        subcats = repo.get_subcategories(main)
        print(f"  {main} ({len(subcats)} Subkategorien)")

    # Test: Suche
    print("\nSuche 'Versicherung':")
    results = repo.search("versicherung")
    for cat in results[:3]:
        print(f"  {cat.name}")
