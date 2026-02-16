"""
===============================================================================
Project   : Hibi-BuRe
Module    : category_selection_widget.py
Created   : 13.02.26
Author    : florian
Purpose   : CategorySelectionWidget - Selection widget for categories

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Set
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTreeWidget, QTreeWidgetItem, QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.data.models.domain_models import Category


class CategorySelectionWidget(QWidget):
    """
    A widget for hierarchical category selection and management.

    This class provides a user interface to select categories from a hierarchical
    structure. Users can select all, deselect all, filter categories via a search
    field, and interact with the category tree.

    The widget supports emitting a signal when the selection changes and allows
    programmatic setting of the selection. The hierarchical structure supports
    main categories, subcategories, and group levels.

    :ivar categories: A list of category objects provided to construct the widget's
        hierarchical structure.
    :type categories: List[Category]
    :ivar category_lookup: A mapping of category IDs to their corresponding category
        objects for quick lookups.
    :type category_lookup: dict[int, Category]
    :ivar tree_items: A mapping of category IDs to the corresponding
        QTreeWidgetItem instances in the category tree.
    :type tree_items: dict[int, QTreeWidgetItem]
    :ivar selection_changed: A signal emitted when the category selection changes.
        Emits the list of selected category IDs.
    :type selection_changed: pyqtSignal[list[int]]
    """

    # Signal wenn Auswahl sich ändert
    selection_changed = pyqtSignal(list)  # List[int] - category_ids

    def __init__(self, categories: List[Category], parent=None):
        """
        Initializes the object and sets up the category management system along with
        the user interface for interacting with the categories. The class allows for
        representation of categories in a tree structure, with quick mapping between
        category IDs and their tree items.

        :param categories: A list of Category objects representing the categories to
                           be managed in the tree.
        :param parent: An optional parent object for this instance.
        :type categories: List[Category]
        """
        super().__init__(parent)

        self.categories = categories
        self.category_lookup = {cat.id: cat for cat in categories}
        self.tree_items = {}  # category_id -> QTreeWidgetItem

        self._setup_ui()
        self._build_tree()

    def _setup_ui(self):
        """
        Initializes and sets up the user interface components within the view.

        The method organizes the UI layout into a vertical layout container and adds the necessary
        elements such as a header with buttons, a search field, and a tree widget. It manages the
        configuration of each component and establishes signal-slot connections for UI events.

        :return: None
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header mit Buttons
        header = QHBoxLayout()

        title = QLabel("Kategorien")
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        # Alle / Keine Buttons
        select_all_btn = QPushButton("Alle")
        select_all_btn.setMaximumWidth(60)
        select_all_btn.clicked.connect(self.select_all)
        header.addWidget(select_all_btn)

        select_none_btn = QPushButton("Keine")
        select_none_btn.setMaximumWidth(60)
        select_none_btn.clicked.connect(self.select_none)
        header.addWidget(select_none_btn)

        layout.addLayout(header)

        # Suchfeld
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Suche...")
        self.search_field.textChanged.connect(self._on_search)
        layout.addWidget(self.search_field)

        # TreeWidget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)

    def _build_tree(self):
        """
        Constructs and populates a tree structure in a QTreeWidget to represent categorized items. The tree
        includes hierarchical relationships among categories, such as main categories, subcategories,
        and groups. Special handling is applied for items without a specific category.

        This method organizes the input data into a nested tree representation, with support for visually
        presenting parent-child relationships, handling root categories and sub-items, and tracking
        their corresponding IDs.

        :raises KeyError: If a parent category required for a subcategory or group is not found in
            the `tree_items` dictionary.

        :raises ValueError: If certain attributes required for hierarchy building, such as `level`
            or `subcategory`, are missing or invalid in the provided category data.

        """
        self.tree.clear()
        self.tree_items.clear()

        # Spezial-Item für "ohne Kategorie" (ID = -1)
        without_item = QTreeWidgetItem(["(ohne Kategorie)"])
        without_item.setFlags(without_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        without_item.setCheckState(0, Qt.CheckState.Checked)  # Initial aktiviert
        without_item.setData(0, Qt.ItemDataRole.UserRole, -1)  # Spezielle ID für "ohne"
        self.tree.addTopLevelItem(without_item)
        self.tree_items[-1] = without_item

        # NEUE LOGIK: Nutze parent_id für beliebig tiefe Hierarchien
        # Erstelle Dict für schnellen Zugriff
        cat_by_id = {cat.id: cat for cat in self.categories}

        # Finde alle Root-Kategorien (ohne parent_id)
        root_cats = [cat for cat in self.categories if cat.parent_id is None]

        # Rekursive Funktion zum Aufbauen des Baums
        def add_category_recursive(cat, parent_item=None):
            # Erstelle Tree-Item für diese Kategorie
            tree_item = self._create_tree_item(cat)

            # Füge zum Tree hinzu
            if parent_item is None:
                # Root-Level
                self.tree.addTopLevelItem(tree_item)
            else:
                # Kind einer anderen Kategorie
                parent_item.addChild(tree_item)

            # Speichere für späteren Zugriff
            self.tree_items[cat.id] = tree_item

            # Finde alle Kinder dieser Kategorie
            children = [c for c in self.categories if c.parent_id == cat.id]

            # Rekursiv alle Kinder hinzufügen
            for child in sorted(children, key=lambda c: c.name):
                add_category_recursive(child, tree_item)

        # Baue Baum auf, beginnend mit allen Root-Kategorien
        for root_cat in sorted(root_cats, key=lambda c: c.name):
            add_category_recursive(root_cat)

        # Expandiere alle Root-Items
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setExpanded(True)

    def _create_tree_item(self, category: Category) -> QTreeWidgetItem:
        """
        Creates a QTreeWidgetItem for the given category.

        The method generates a tree item based on the provided category, displaying
        only the last part of the hierarchy name, or the full name if the hierarchy
        is empty. The tree item is configured to be user-checkable, and its check
        state is initially set to unchecked. The item's user role data is associated
        with the category's ID.

        :param category: Category object used to populate the tree item.
        :type category: Category
        :return: A QTreeWidgetItem configured with the category's information.
        :rtype: QTreeWidgetItem
        """
        # Zeige nur den letzten Teil des Namens
        display_name = category.hierarchy[-1] if category.hierarchy else category.name

        item = QTreeWidgetItem([display_name])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)  # Initial aktiviert
        item.setData(0, Qt.ItemDataRole.UserRole, category.id)

        return item

    def get_selected_category_ids(self) -> List[int]:
        """
        Retrieves a list of category IDs for items that are checked in a tree widget.

        This method traverses a QTreeWidget to collect IDs of items that are checked. Each item's
        ID is retrieved using the `Qt.ItemDataRole.UserRole` role. The method inspects top-level
        items and their descendants recursively to gather all checked items.

        :return: A list of integers representing the IDs of checked categories.
        :rtype: List[int]
        """
        selected = []

        def collect_checked(item: QTreeWidgetItem):
            if item.checkState(0) == Qt.CheckState.Checked:
                cat_id = item.data(0, Qt.ItemDataRole.UserRole)
                if cat_id:
                    selected.append(cat_id)

            for i in range(item.childCount()):
                collect_checked(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            collect_checked(self.tree.topLevelItem(i))

        return selected

    def select_all(self):
        """
        Marks all items and their children in a tree widget as checked.

        This method iterates through all top-level items in the tree widget and marks them,
        along with all their child items, as checked. It uses the recursive helper function
        `check_all` to traverse through each item's children and update their check state.

        :param self: The instance of the class that contains the tree widget.
        :return: None
        """
        def check_all(item: QTreeWidgetItem):
            item.setCheckState(0, Qt.CheckState.Checked)
            for i in range(item.childCount()):
                check_all(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            check_all(self.tree.topLevelItem(i))

    def select_none(self):
        """
        Deselects all items in the tree by setting their check state to unchecked.

        This method recursively navigates through all top-level items and their
        children in the tree structure, ensuring that every item is deselected
        by applying the unchecked state.

        :param self: Refers to the instance of the class where the method is being used.
        """
        def uncheck_all(item: QTreeWidgetItem):
            item.setCheckState(0, Qt.CheckState.Unchecked)
            for i in range(item.childCount()):
                uncheck_all(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            uncheck_all(self.tree.topLevelItem(i))

    def set_selected_category_ids(self, category_ids: List[int]):
        """
        Sets the check state of tree view items based on the provided list of category IDs. This function
        iterates through all top-level items and their children in the tree and adjusts their check state
        to match whether their associated category IDs are present in the provided list.

        :param category_ids: A list of integers representing category IDs to be marked as checked.
        :type category_ids: List[int]
        :return: None
        """
        selected_set = set(category_ids)

        def set_check(item: QTreeWidgetItem):
            cat_id = item.data(0, Qt.ItemDataRole.UserRole)
            if cat_id in selected_set:
                item.setCheckState(0, Qt.CheckState.Checked)
            else:
                item.setCheckState(0, Qt.CheckState.Unchecked)

            for i in range(item.childCount()):
                set_check(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            set_check(self.tree.topLevelItem(i))

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """
        Handles changes to the check state of a tree widget item, propagating the
        state to child items and emitting a selection changed signal.

        :param item: The tree widget item whose state has been changed.
        :type item: QTreeWidgetItem
        :param column: The column index where the state change occurred.
        :type column: int
        """
        if column == 0:
            # WICHTIG: Blockiere Signale während wir Kinder ändern
            # sonst wird für jedes Kind ein selection_changed Signal gefeuert!
            self.tree.blockSignals(True)

            # Propagiere zu Kindern
            check_state = item.checkState(0)
            self._set_children_check_state(item, check_state)

            # Signale wieder aktivieren
            self.tree.blockSignals(False)

            # Emit signal NUR EINMAL am Ende
            selected_ids = self.get_selected_category_ids()
            self.selection_changed.emit(selected_ids)

    def _set_children_check_state(self, item: QTreeWidgetItem, state: Qt.CheckState):
        """
        Recursively sets the check state of all child items of the given tree widget item.

        This function traverses through all child nodes in a tree structure, starting from
        the specified parent item, and sets their check state to the given state. It ensures
        that all children of the parent item recursively inherit the specified check state.

        :param item: The parent tree widget item whose children will have their check state set.
            It represents a node in the tree structure.
        :type item: QTreeWidgetItem
        :param state: The check state to be applied to all child items of the given parent item.
            Represents the desired check state, e.g., ``Qt.CheckState.Unchecked``,
            ``Qt.CheckState.PartiallyChecked``, or ``Qt.CheckState.Checked``.
        :type state: Qt.CheckState
        """
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._set_children_check_state(child, state)

    def _on_search(self, text: str):
        """
        Filters and updates the visibility and expansion state of items in a tree
        widget based on a case-insensitive search query. If a tree item or any of
        its children matches the search query, the item is made visible and
        expanded.

        :param text: The search query used to filter items in the tree widget.
        :type text: str
        """
        search_text = text.lower().strip()

        def filter_item(item: QTreeWidgetItem) -> bool:
            """Prüft ob Item oder Kinder matchen"""
            # Prüfe Item selbst
            item_text = item.text(0).lower()
            matches = search_text in item_text

            # Prüfe Kinder rekursiv
            child_matches = False
            for i in range(item.childCount()):
                if filter_item(item.child(i)):
                    child_matches = True

            # Zeige Item wenn es oder seine Kinder matchen
            item.setHidden(not (matches or child_matches))

            # Expandiere wenn Kinder matchen
            if child_matches and search_text:
                item.setExpanded(True)

            return matches or child_matches

        # Wende Filter an
        for i in range(self.tree.topLevelItemCount()):
            filter_item(self.tree.topLevelItem(i))


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from src.data.database_manager import DatabaseManager

    app = QApplication(sys.argv)

    # Lade echte Kategorien
    db = DatabaseManager()
    categories = db.categories.get_all()

    print(f"Geladene Kategorien: {len(categories)}")

    # Erstelle Widget
    widget = QWidget()
    layout = QVBoxLayout(widget)

    cat_widget = CategorySelectionWidget(categories)
    cat_widget.selection_changed.connect(
        lambda ids: print(f"Ausgewählt: {len(ids)} Kategorien")
    )
    layout.addWidget(cat_widget)

    widget.resize(400, 600)
    widget.show()

    sys.exit(app.exec())
