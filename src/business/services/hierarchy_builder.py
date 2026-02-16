"""
===============================================================================
Project   : Hibi-BuBe
Module    : hierarchy_builder.py
Created   : 13.02.26
Author    : florian
Purpose   : HierarchyBuilder - builds hierarchical trees from categories

Compiles a list of categories into a tree structure.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from decimal import Decimal

from src.data.models.domain_models import Category, Transaction


@dataclass
class CategoryNode:
    """
    Represents a hierarchical node in a category tree structure.

    This class is used to model hierarchical relationships between different
    categories, allowing the user to organize and analyze data in a structured
    way. It includes methods for managing child nodes, traversing the tree,
    and retrieving path-related information. Each node can store associated
    category IDs, transaction IDs, and computed values like the total amount
    and the number of transactions.

    It facilitates recursive operations to retrieve descendants, path components,
    and more while maintaining parent-child relationships.

    :ivar name: Name of the category or node.
    :type name: str
    :ivar level: The hierarchical level of the node. Values are:
                 0 for categories, 1 for subcategories, and 2 for groups.
    :type level: int
    :ivar full_path: The complete path to this node (e.g., "Versicherungen:KFZ:Allianz").
    :type full_path: str
    :ivar category_ids: List of category IDs associated with this node.
    :type category_ids: List[int]
    :ivar transaction_ids: List of transaction IDs associated with this node.
    :type transaction_ids: List[int]
    :ivar children: Dictionary mapping child node names to their corresponding
                    `CategoryNode` objects.
    :type children: Dict[str, CategoryNode]
    :ivar parent: The parent of the current node. Defaults to None if it is
                  the root node.
    :type parent: Optional[CategoryNode]
    :ivar total_amount: The total amount computed for this node. This is a
                        calculated value and is filled later.
    :type total_amount: Decimal
    :ivar transaction_count: The number of transactions computed for this node.
                             This is a calculated value and is filled later.
    :type transaction_count: int
    """
    name: str
    level: int  # 0=Kategorie, 1=Subkategorie, 2=Gruppe
    full_path: str  # Kompletter Pfad (z.B. "Versicherungen:KFZ:Allianz")
    category_ids: List[int] = field(default_factory=list)  # IDs der Kategorien die zu diesem Knoten gehören
    transaction_ids: List[int] = field(default_factory=list)  # IDs der zugeordneten Transaktionen
    children: Dict[str, 'CategoryNode'] = field(default_factory=dict)
    parent: Optional['CategoryNode'] = None

    # Berechnete Werte (werden später gefüllt)
    total_amount: Decimal = Decimal('0')
    transaction_count: int = 0

    def add_child(self, child: 'CategoryNode'):
        """
        Adds a child node to the current node.

        This method sets the parent of the provided child node to the current node
        and adds the child to the current node's children dictionary using the child's
        name as the key.

        :param child: The child node to be added.
        :type child: CategoryNode

        :return: None
        """
        child.parent = self
        self.children[child.name] = child

    def get_child(self, name: str) -> Optional['CategoryNode']:
        """
        Retrieves a child node from the children dictionary by its name.

        :param name: The name of the child node to retrieve.
        :type name: str
        :return: The child node associated with the provided name, or None if no
            child node with the given name exists.
        :rtype: Optional[CategoryNode]
        """
        return self.children.get(name)

    def has_children(self) -> bool:
        """
        Determines if the current instance has child elements.

        This method checks if the `children` attribute contains any elements and
        returns a boolean value indicating the presence of children.

        :return: True if there are child elements, otherwise False.
        :rtype: bool
        """
        return len(self.children) > 0

    def get_all_descendants(self) -> List['CategoryNode']:
        """
        Recursively retrieves all descendant nodes of the current node, including
        direct children and nested descendants.

        :return: A list of all descendant nodes.
        :rtype: List[CategoryNode]
        """
        descendants = []
        for child in self.children.values():
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants

    def get_path_parts(self) -> List[str]:
        """
        Splits the full path into its individual components separated by colons.

        This method processes the `full_path` string attribute by splitting it on colon
        (`:`) characters. The resulting parts, represented as a list of strings, are
        returned to the caller.

        :return: A list of strings representing individual components of the `full_path` attribute.
        :rtype: List[str]
        """
        return self.full_path.split(':')

    def __repr__(self) -> str:
        """
        Provides a string representation of a CategoryNode instance. This representation
        includes the name of the node, its level, and the number of children associated
        with it.

        :return: A string describing the CategoryNode with its name, level, and
            number of children.
        :rtype: str
        """
        return f"CategoryNode({self.name}, level={self.level}, children={len(self.children)})"


@dataclass
class CategoryTree:
    """
    Represents a tree structure for organizing categories.

    The CategoryTree class provides functionality to manage a hierarchical
    structure of categories, allowing nodes to be added, retrieved, and
    processed. It supports root-level nodes and traversal of the hierarchy
    via paths. This class is particularly useful for applications involving
    structured category management, such as taxonomies or organizational
    charts.

    :ivar root_nodes: Dictionary of root nodes where keys are node names
        and values are instances of CategoryNode.
    :type root_nodes: Dict[str, CategoryNode]
    """
    root_nodes: Dict[str, CategoryNode] = field(default_factory=dict)

    def add_root(self, node: CategoryNode):
        """
        Adds a root node to the collection of root nodes.

        This method associates a new `CategoryNode` instance with its
        name as the key in the root node collection. The added node
        must be unique in the context of the collection.

        :param node: The `CategoryNode` instance to be added as a root node.
        :type node: CategoryNode
        """
        self.root_nodes[node.name] = node

    def get_root(self, name: str) -> Optional[CategoryNode]:
        """
        Retrieves the root node of a category by its name.

        Given the name of a category, this method fetches the corresponding root
        node from the collection of root nodes if it exists. If no root node
        matches the provided name, the method returns None.

        :param name: The name of the category whose root node is to be retrieved.
        :type name: str

        :return: The root node of the specified category, or None if no matching
            root node is found.
        :rtype: Optional[CategoryNode]
        """
        return self.root_nodes.get(name)

    def get_all_nodes(self) -> List[CategoryNode]:
        """
        Retrieve all nodes, including root nodes and their descendants.

        This method aggregates all root nodes and their respective descendants into
        a single list and returns it.

        :return: A list of all CategoryNode objects, including root nodes and their
            descendants.
        :rtype: List[CategoryNode]
        """
        all_nodes = list(self.root_nodes.values())
        for root in self.root_nodes.values():
            all_nodes.extend(root.get_all_descendants())
        return all_nodes

    def find_node_by_path(self, path: str) -> Optional[CategoryNode]:
        """
        Finds a node in a hierarchical structure based on a colon-separated path.

        This method navigates through a tree-like structure using the provided path,
        which consists of node names separated by colons (e.g., "root:child:subchild").
        It starts at the root node and traverses downwards by matching each part
        of the path to the corresponding child node.

        :param path: A colon-separated string representing the path to the node.
        :type path: str
        :return: The `CategoryNode` object corresponding to the given path if found,
            otherwise `None`.
        :rtype: Optional[CategoryNode]
        """
        parts = path.split(':')

        # Finde Root
        if not parts or parts[0] not in self.root_nodes:
            return None

        current = self.root_nodes[parts[0]]

        # Navigiere durch Baum
        for part in parts[1:]:
            current = current.get_child(part)
            if current is None:
                return None

        return current

    def __repr__(self) -> str:
        """
        Returns a string representation of the CategoryTree object.

        The string representation includes the count of root nodes as well as the total
        number of nodes in the category tree. This is intended for developers to get a
        quick overview of the tree structure when inspecting objects.

        :return: A string summarizing the number of root nodes and total nodes in the
            category tree.
        :rtype: str
        """
        return f"CategoryTree(roots={len(self.root_nodes)}, total_nodes={len(self.get_all_nodes())})"


class HierarchyBuilder:
    """
    Provides methods to construct and manipulate a hierarchical structure of categories and transactions.

    This class is designed to parse category names into hierarchical components, build hierarchical trees of categories,
    assign transactions to the appropriate nodes in the tree, calculate aggregate values for each node, and filter the
    tree based on specific patterns. The primary use case is for managing hierarchical data such as categories, subcategories,
    and transactional data within those categories.

    :ivar attribute1: Specify and describe relevant attributes required for the hierarchical builder, if any.
    :type attribute1: type
    :ivar attribute2: Specify and describe additional attributes if applicable.
    :type attribute2: type
    """

    def parse_category(self, name: str) -> List[str]:
        """
        Parses a category string and splits it into its components.

        This method takes a category string, splits it by the delimiter ':',
        and returns the resulting components as a list. If the input string
        is empty or None, it returns an empty list.

        :param name: A category string to be parsed, where parts are separated
                     by the ':' delimiter.
        :type name: str
        :return: A list of category components parsed from the input string.
        :rtype: List[str]
        """
        return name.split(':') if name else []

    def build_tree(self, categories: List[Category]) -> CategoryTree:
        """
        Builds a category tree from a given list of categories.

        This method organizes the provided list of categories into a hierarchical
        structure based on their levels. Categories with a lower level are inserted
        before categories with a higher level to maintain proper hierarchical order.

        :param categories: List of categories to be organized into a tree.
        :type categories: List[Category]
        :return: The constructed category tree.
        :rtype: CategoryTree
        """
        tree = CategoryTree()

        # Sortiere Kategorien nach Hierarchie-Level (flach → tief)
        sorted_cats = sorted(categories, key=lambda c: c.level)

        for cat in sorted_cats:
            self._add_category_to_tree(tree, cat)

        return tree

    def _add_category_to_tree(self, tree: CategoryTree, category: Category):
        """
        Adds a category to a hierarchical tree structure by traversing or creating its
        path based on the given category hierarchy.

        :param tree: The CategoryTree instance where the category should be added.
        :param category: The Category object containing the hierarchy and ID to be
            inserted into the tree.
        :return: None
        """
        parts = category.hierarchy

        if not parts:
            return

        # Root-Ebene
        root_name = parts[0]
        if root_name not in tree.root_nodes:
            root_node = CategoryNode(
                name=root_name,
                level=0,
                full_path=root_name
            )
            tree.add_root(root_node)

        current = tree.root_nodes[root_name]

        # Wenn nur Root-Level, füge Category-ID hinzu
        if len(parts) == 1:
            current.category_ids.append(category.id)
            return

        # Navigiere/erstelle durch Hierarchie
        current_path = root_name
        for i, part in enumerate(parts[1:], start=1):
            current_path = f"{current_path}:{part}"

            # Prüfe ob Kind existiert
            if part not in current.children:
                child = CategoryNode(
                    name=part,
                    level=i,
                    full_path=current_path
                )
                current.add_child(child)

            current = current.children[part]

        # Füge Category-ID zum finalen Knoten hinzu
        current.category_ids.append(category.id)

    def assign_transactions(
        self,
        tree: CategoryTree,
        transactions: List[Transaction],
        categories: List[Category]
    ) -> CategoryTree:
        """
        Assigns transactions to their respective categories within a given category tree. If some transactions do not belong
        to any category, they are associated with a special "(ohne Kategorie)" node in the tree.

        :param tree: A CategoryTree object that represents the hierarchical structure of categories.
        :param transactions: A list of Transaction objects that need to be assigned to the appropriate categories in the tree.
        :param categories: A list of Category objects, each representing a category identified by a unique category identifier.
        :return: The updated CategoryTree object with transactions assigned to their respective nodes.
        """
        # Erstelle Lookup: category_id -> Category
        cat_lookup = {cat.id: cat for cat in categories}

        # Erstelle "ohne Zuordnung" Knoten IMMER
        # (wird benötigt für Transaktionen ohne Kategorie ODER mit ungültiger Kategorie)
        uncategorized_node = CategoryNode(
            name="ohne Zuordnung",
            level=0,
            full_path="ohne Zuordnung",
            category_ids=[-1],  # Spezielle ID
            transaction_ids=[],
            children={}
        )
        tree.add_root(uncategorized_node)

        # Weise jede Transaction zu
        ohne_zuordnung_node = tree.find_node_by_path("ohne Zuordnung")
        uncategorized_trans_ids = []

        # Debug: Wie viele Transaktionen haben eine Kategorie?
        for trans in transactions:
            if trans.category_id and trans.category_id in cat_lookup:
                cat = cat_lookup[trans.category_id]
                # Nutze die vollständige Hierarchie (aus parent_id rekursiv aufgebaut)
                full_path = ':'.join(cat.hierarchy) if cat.hierarchy else cat.name
                node = tree.find_node_by_path(full_path)

                if node:
                    node.transaction_ids.append(trans.id)
                else:
                    # Kategorie existiert in DB, aber nicht im Tree (sollte nicht passieren)
                    # Füge zur "ohne Zuordnung" hinzu
                    if ohne_zuordnung_node:
                        ohne_zuordnung_node.transaction_ids.append(trans.id)
                        uncategorized_trans_ids.append(trans.id)
            else:
                # Transaktion ohne Kategorie ODER Kategorie nicht in cat_lookup
                # (z.B. virtuelle Kategorie die herausgefiltert wurde)
                if ohne_zuordnung_node:
                    ohne_zuordnung_node.transaction_ids.append(trans.id)
                    uncategorized_trans_ids.append(trans.id)

        return tree

    def calculate_aggregates(
        self,
        tree: CategoryTree,
        transactions: List[Transaction]
    ) -> CategoryTree:
        """
        Calculates aggregate financial data within a category tree structure based on
        transactions. Updates each category node with computed total amounts and transaction
        counts by traversing the tree in a post-order manner. Direct transactions and child
        node aggregates are included in the calculations.

        :param tree: A tree structure representing categories and their hierarchical
            relationships. Each node represents a category, which may have child nodes
            and associated transactions.
        :type tree: CategoryTree

        :param transactions: A list of financial transaction records. Each transaction
            is associated with an identifier that may be linked to one or more category
            nodes in the tree.
        :type transactions: List[Transaction]

        :return: The updated category tree with aggregated totals and transaction counts
            computed for each node.
        :rtype: CategoryTree
        """
        # Erstelle Lookup: transaction_id -> Transaction
        trans_lookup = {trans.id: trans for trans in transactions}

        # Berechne von unten nach oben (Post-Order Traversal)
        def calculate_node(node: CategoryNode):
            # Direkte Transaktionen des Knotens
            node.total_amount = sum(
                trans_lookup[tid].amount
                for tid in node.transaction_ids
                if tid in trans_lookup
            )
            node.transaction_count = len(node.transaction_ids)

            # Addiere Werte der Kinder
            for child in node.children.values():
                calculate_node(child)
                node.total_amount += child.total_amount
                node.transaction_count += child.transaction_count

        # Starte bei jedem Root
        for root in tree.root_nodes.values():
            calculate_node(root)

        return tree

    def get_children(self, tree: CategoryTree, parent_path: str) -> List[CategoryNode]:
        """
        Retrieve the child nodes of a specified parent node within a category tree.

        This method searches the given category tree for a node at the specified
        parent path. If the node is found, it returns a list of its children. If
        no node is found at the specified path, an empty list is returned.

        :param tree: The category tree to search within.
        :type tree: CategoryTree
        :param parent_path: The path of the parent node whose child nodes are to
            be retrieved.
        :type parent_path: str
        :return: A list of child nodes for the specified parent node. Returns
            an empty list if no parent node is found at the given path.
        :rtype: List[CategoryNode]
        """
        node = tree.find_node_by_path(parent_path)
        if node:
            return list(node.children.values())
        return []

    def get_parent(self, node: CategoryNode) -> Optional[CategoryNode]:
        """
        Retrieves the parent node of the specified category node.

        :param node: The category node whose parent is to be retrieved.
        :type node: CategoryNode
        :return: The parent node of the specified category node, or None if the node
            has no parent.
        :rtype: Optional[CategoryNode]
        """
        return node.parent

    def filter_tree_by_pattern(
        self,
        tree: CategoryTree,
        pattern: str
    ) -> CategoryTree:
        """
        Filters the input category tree to retain only the nodes that match the given
        pattern. The implementation currently simplifies the filtering by copying
        only the matching nodes.

        :param tree: The category tree to be filtered.
        :type tree: CategoryTree
        :param pattern: The pattern used to filter the tree. Only nodes matching the
            pattern are retained in the filtered result.
        :type pattern: str
        :return: A new category tree containing only the nodes that match the given
            pattern. The returned tree may not preserve the original hierarchy.
        :rtype: CategoryTree
        """
        filtered = CategoryTree()

        # Implementierung vereinfacht: Kopiere nur matching Nodes
        for node in tree.get_all_nodes():
            if self._matches_pattern(node.full_path, pattern):
                # TODO: Komplexere Filterung mit Erhalt der Hierarchie
                pass

        return filtered

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Checks if a given path matches a specified pattern.

        This utility function validates whether the given path conforms to the
        provided pattern based on specific matching rules. Patterns ending with `:*`
        indicate prefix matching, those starting with `*:` indicate suffix matching,
        and all other patterns indicate exact matches.

        :param path: The string path to be matched.
        :param pattern: The string pattern used for matching.
        :return: A boolean value indicating whether the path matches the pattern.
        """
        if pattern.endswith(':*'):
            prefix = pattern[:-2]
            return path.startswith(prefix + ':') or path == prefix
        elif pattern.startswith('*:'):
            suffix = pattern[1:]
            return suffix in path
        else:
            return path == pattern


if __name__ == "__main__":
    # Test
    from src.data.models.domain_models import Category

    print("=== HierarchyBuilder Test ===\n")

    builder = HierarchyBuilder()

    # Test Kategorien
    test_categories = [
        Category(1, "Versicherungen"),
        Category(2, "Versicherungen:KFZ"),
        Category(3, "Versicherungen:KFZ:Allianz"),
        Category(4, "Versicherungen:KFZ:Ergo"),
        Category(5, "Versicherungen:Hausrat"),
        Category(6, "Lebensmittel"),
    ]

    print("1. Baum aufbauen...")
    tree = builder.build_tree(test_categories)
    print(f"   ✓ {tree}")

    print("\n2. Root-Knoten:")
    for root_name, root in tree.root_nodes.items():
        print(f"   - {root_name} ({len(root.children)} Kinder)")

    print("\n3. Alle Knoten:")
    for node in tree.get_all_nodes():
        indent = "  " * node.level
        print(f"   {indent}├─ {node.name} (Level {node.level}, IDs: {node.category_ids})")

    print("\n4. Navigation:")
    node = tree.find_node_by_path("Versicherungen:KFZ:Allianz")
    if node:
        print(f"   Gefunden: {node.full_path}")
        print(f"   Parent: {node.parent.name if node.parent else 'None'}")

    children = builder.get_children(tree, "Versicherungen:KFZ")
    print(f"\n5. Kinder von 'Versicherungen:KFZ': {[c.name for c in children]}")
