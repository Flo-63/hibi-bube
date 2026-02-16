"""
===============================================================================
Project   : Hibi-BuRe
Module    : account_selection_widget.py
Created   : 13.02.26
Author    : florian
Purpose   : Account selection widget with toggle between accounts and account categories

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Callable, Optional, Set, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QScrollArea, QPushButton, QFrame, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.data.models.domain_models import Account


class AccountSelectionWidget(QWidget):
    """
    Widget to manage account selection with toggle between accounts and account categories.

    The AccountSelectionWidget class provides a UI component for selecting accounts
    through checkboxes. Users can toggle between account-based and category-based selection,
    select all accounts, deselect all, or select specific accounts programmatically.
    The widget emits a signal when the selection changes, providing the selected account IDs.

    :ivar accounts: A list of accounts to display checkboxes for.
    :type accounts: List[Account]
    :ivar checkboxes: A mapping of account IDs or category names to corresponding QCheckBox instances.
    :type checkboxes: dict
    :ivar mode: Current selection mode ("accounts" or "categories")
    :type mode: str
    """

    # Signal wenn Auswahl sich ändert
    selection_changed = pyqtSignal(list)  # List[int] - account_ids

    def __init__(self, accounts: List[Account], parent=None):
        """
        Initializes the object with a list of accounts and an optional parent widget.

        This constructor sets up the user interface components necessary to manage
        accounts and initializes attributes to maintain the state of checkboxes
        associated with each account or category.

        :param accounts: A list of `Account` objects representing the accounts to be
            managed.
        :param parent: An optional parent widget in the widget hierarchy.
        """
        super().__init__(parent)

        self.accounts = accounts
        self.checkboxes = {}  # account_id/category -> QCheckBox
        self.mode = "accounts"  # "accounts" or "categories"

        # Extract unique categories and build category->accounts mapping
        self.categories = self._get_unique_categories()
        self.has_categories = len(self.categories) > 0
        self.category_to_accounts: Dict[str, List[int]] = self._build_category_mapping()

        self._setup_ui()

    def _get_unique_categories(self) -> List[str]:
        """
        Extract unique account categories from accounts list.

        :return: Sorted list of unique category names
        """
        categories = set()
        for account in self.accounts:
            if account.kategorie:
                categories.add(account.kategorie)
        return sorted(list(categories))

    def _build_category_mapping(self) -> Dict[str, List[int]]:
        """
        Build mapping from category name to list of account IDs.

        :return: Dictionary mapping category names to account ID lists
        """
        mapping = {}
        for account in self.accounts:
            if account.kategorie:
                if account.kategorie not in mapping:
                    mapping[account.kategorie] = []
                mapping[account.kategorie].append(account.id)
            else:
                # Accounts without category go into "Ohne Kategorie"
                if "Ohne Kategorie" not in mapping:
                    mapping["Ohne Kategorie"] = []
                mapping["Ohne Kategorie"].append(account.id)
        return mapping

    def _setup_ui(self):
        """
        Set up the UI components for the widget, including toggle buttons,
        header buttons for selection, and a scrollable area for checkboxes.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toggle buttons: Konten / Kontengruppen
        toggle_layout = QHBoxLayout()

        self.accounts_btn = QPushButton("Konten")
        self.accounts_btn.setCheckable(True)
        self.accounts_btn.setChecked(True)
        self.accounts_btn.clicked.connect(lambda: self._switch_mode("accounts"))
        toggle_layout.addWidget(self.accounts_btn)

        self.categories_btn = QPushButton("Kontengruppen")
        self.categories_btn.setCheckable(True)
        self.categories_btn.setEnabled(self.has_categories)
        self.categories_btn.clicked.connect(lambda: self._switch_mode("categories"))
        toggle_layout.addWidget(self.categories_btn)

        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)

        # Header mit Buttons
        header = QHBoxLayout()

        header.addStretch()

        # Alle auswählen / Keine Button
        select_all_btn = QPushButton("Alle")
        select_all_btn.setMaximumWidth(60)
        select_all_btn.clicked.connect(self.select_all)
        header.addWidget(select_all_btn)

        select_none_btn = QPushButton("Keine")
        select_none_btn.setMaximumWidth(60)
        select_none_btn.clicked.connect(self.select_none)
        header.addWidget(select_none_btn)

        layout.addLayout(header)

        # Scroll Area für Checkboxen
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(150)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Container für Checkboxen (wird dynamisch gefüllt)
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(5)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Initial: Zeige Konten-Ansicht
        self._populate_accounts_view()

    def _switch_mode(self, mode: str):
        """
        Switch between accounts and categories view.

        :param mode: "accounts" or "categories"
        """
        if mode == self.mode:
            return

        self.mode = mode

        # Update button states
        self.accounts_btn.setChecked(mode == "accounts")
        self.categories_btn.setChecked(mode == "categories")

        # Clear current checkboxes
        self.checkboxes.clear()
        while self.container_layout.count():
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Populate new view
        if mode == "accounts":
            self._populate_accounts_view()
        else:
            self._populate_categories_view()

        # Emit selection changed
        self._on_selection_changed()

    def _populate_accounts_view(self):
        """Populate container with account checkboxes."""
        for account in self.accounts:
            cb = QCheckBox(account.display_name)
            cb.stateChanged.connect(self._on_selection_changed)
            self.container_layout.addWidget(cb)
            self.checkboxes[account.id] = cb

        self.container_layout.addStretch()

    def _populate_categories_view(self):
        """Populate container with category checkboxes."""
        for category in sorted(self.category_to_accounts.keys()):
            account_count = len(self.category_to_accounts[category])
            label = f"{category} ({account_count} Konten)"
            cb = QCheckBox(label)
            cb.stateChanged.connect(self._on_selection_changed)
            self.container_layout.addWidget(cb)
            self.checkboxes[category] = cb

        self.container_layout.addStretch()

    def get_selected_account_ids(self) -> List[int]:
        """
        Gets the IDs of the selected accounts based on current mode.

        In accounts mode: Returns IDs of checked accounts.
        In categories mode: Returns IDs of all accounts in checked categories.

        :return: A list of integers representing the IDs of selected accounts.
        :rtype: List[int]
        """
        if self.mode == "accounts":
            return [
                acc_id
                for acc_id, cb in self.checkboxes.items()
                if cb.isChecked()
            ]
        else:  # categories mode
            selected_ids = []
            for category, cb in self.checkboxes.items():
                if cb.isChecked():
                    selected_ids.extend(self.category_to_accounts.get(category, []))
            return selected_ids

    def select_all(self):
        """
        Selects all checkboxes managed by the current instance.
        """
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def select_none(self):
        """
        Deselects all checkboxes managed by the current object.
        """
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def set_selected_account_ids(self, account_ids: List[int]):
        """
        Sets selected account IDs by checking the corresponding checkboxes.
        Works in both accounts and categories mode.

        :param account_ids: A list of integers representing the account IDs
            that should be selected.
        :return: None
        """
        if self.mode == "accounts":
            for acc_id, cb in self.checkboxes.items():
                cb.setChecked(acc_id in account_ids)
        else:  # categories mode
            # Check category if ALL its accounts are in account_ids
            account_ids_set = set(account_ids)
            for category, cb in self.checkboxes.items():
                category_accounts = set(self.category_to_accounts.get(category, []))
                # Check if all accounts in this category are selected
                cb.setChecked(category_accounts.issubset(account_ids_set))

    def _on_selection_changed(self):
        """
        Handles the change in selection by emitting a signal with the list of
        selected account IDs.
        """
        selected_ids = self.get_selected_account_ids()
        self.selection_changed.emit(selected_ids)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from src.data.database_manager import DatabaseManager

    app = QApplication(sys.argv)

    # Lade echte Konten
    db = DatabaseManager()
    accounts = db.accounts.get_all()

    # Erstelle Widget
    widget = QWidget()
    layout = QVBoxLayout(widget)

    acc_widget = AccountSelectionWidget(accounts)
    acc_widget.selection_changed.connect(
        lambda ids: print(f"Ausgewählt: {ids}")
    )
    layout.addWidget(acc_widget)

    widget.show()
    sys.exit(app.exec())
