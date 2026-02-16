"""
===============================================================================
Project   : Hibi-BuRe
Module    : preview_widget.py
Created   : 13.02.26
Author    : florian
Purpose   : PreviewWidget - Shows report preview with hierarchical grouping

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Optional, Dict
from decimal import Decimal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QHeaderView,
    QLabel, QPushButton, QHBoxLayout, QApplication, QLineEdit
)
from PyQt6.QtCore import Qt, QAbstractItemModel, QModelIndex, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QFont, QBrush, QColor, QPalette

from src.data.models.report_config import ReportConfig
from src.data.models.domain_models import Transaction
from src.business.services.hierarchy_builder import HierarchyBuilder, CategoryTree, CategoryNode


class PreviewWidget(QWidget):
    """
    PreviewWidget is a QWidget subclass used for managing and displaying transaction
    data in a categorized format with lazy loading and column settings persistence.

    This class provides functionality to:
    - Handle lazy loading of data when a certain threshold is reached.
    - Save and restore column settings, including order, widths, and header names.
    - Export current headers.
    - Manage visual headers and logical column indices for transactions.
    - Define a customizable user interface (UI) for better interaction.

    Signals:
    - refresh_requested: Emitted when the preview needs to be refreshed.

    Constants:
    - LAZY_LOAD_THRESHOLD: Defines the threshold for enabling lazy loading.
    - LAZY_LOAD_CHUNK_SIZE: Specifies the number of rows to load per chunk.

    :ivar config: Stores the report configuration, defining attributes and behavior of the
        preview widget.
    :type config: Optional[ReportConfig]
    :ivar transactions: A list of transactions to be displayed in the widget.
    :type transactions: List[Transaction]
    :ivar tree: Represents the category tree used for grouping transactions.
    :type tree: Optional[CategoryTree]
    """

    # Signal wenn Preview aktualisiert werden soll
    refresh_requested = pyqtSignal()

    # Lazy Loading Konstanten
    LAZY_LOAD_THRESHOLD = 1000  # Ab dieser Anzahl wird lazy geladen
    LAZY_LOAD_CHUNK_SIZE = 100  # Anzahl Zeilen pro Chunk

    def __init__(self, parent=None):
        """A class designed to manage and display report data with hierarchical categorization and persistent column attributes.

        This class provides mechanisms for configuration management, transaction handling, and UI setup to build
        a report view. It includes features such as lazy loading of transactions, as well as the ability to save and restore
        column preferences, maintaining users' customizable settings.

        :param parent: The parent widget or container, if applicable.

        :ivar config: Configuration data used for the report.
        :ivar transactions: A list containing transaction data items.
        :ivar tree: An optional categorization tree structure for the report.
        """
        super().__init__(parent)

        self.config: Optional[ReportConfig] = None
        self.transactions: List[Transaction] = []
        self.tree: Optional[CategoryTree] = None

        # Lazy Loading State
        self._is_lazy_loading = False
        self._loaded_transaction_count = 0
        self._total_transaction_count = 0

        # Persistente Spalteneinstellungen (wird bei jedem Rebuild gespeichert)
        self._saved_column_order: List[int] = []
        self._saved_column_widths: List[int] = []
        self._saved_header_names: List[str] = []

        # Aktuelle Header-Reihenfolge (für Row-Erstellung)
        self._current_headers: List[str] = []

        self._setup_ui()

    def _save_column_settings(self):
        """
        Saves the settings of the columns in the current model's tree view. This includes
        capture of column names, their order, and widths. These settings can later be
        used for restoring the view state.

        :raises AttributeError: When attempting to access model-specific attributes that do
            not exist on the object.
        """
        if not hasattr(self, 'model') or not self.model or self.model.columnCount() == 0:
            return

        header = self.tree_view.header()

        # Speichere Header-Namen
        self._saved_header_names = []
        for col in range(self.model.columnCount()):
            header_item = self.model.horizontalHeaderItem(col)
            if header_item:
                self._saved_header_names.append(header_item.text())

        # Speichere Spaltenreihenfolge (visual -> logical mapping)
        self._saved_column_order = []
        for visual_idx in range(header.count()):
            logical_idx = header.logicalIndex(visual_idx)
            self._saved_column_order.append(logical_idx)

        # Speichere Spaltenbreiten (in logischer Reihenfolge)
        self._saved_column_widths = []
        for logical_idx in range(header.count()):
            visual_idx = header.visualIndex(logical_idx)
            self._saved_column_widths.append(header.sectionSize(visual_idx))

    def _restore_column_settings(self, new_headers: List[str]):
        """
        Restores the column settings such as order and width using provided headers. Settings are restored based on
        previously saved header names, column order, and widths. This function adjusts the visual and logical order
        of the headers, aligns the column settings with the saved configuration, and resizes the columns accordingly.

        :param new_headers: List of new header names provided in the current configuration.
        :type new_headers: List[str]
        :return: None
        """
        if not self._saved_header_names or not self._saved_column_order:
            return

        header = self.tree_view.header()

        # Erstelle Mapping: header_name -> saved_index
        saved_name_to_idx = {name: idx for idx, name in enumerate(self._saved_header_names)}

        # Erstelle neues Mapping für die aktuelle Reihenfolge
        # Finde für jeden neuen Header den entsprechenden alten Index
        new_order = []
        for new_idx, new_name in enumerate(new_headers):
            if new_name in saved_name_to_idx:
                # Header existierte vorher - finde seine Position in saved_column_order
                old_logical_idx = saved_name_to_idx[new_name]
                # Finde visuelle Position in saved_column_order
                if old_logical_idx < len(self._saved_column_order):
                    visual_position = self._saved_column_order.index(old_logical_idx) if old_logical_idx in self._saved_column_order else new_idx
                    new_order.append((visual_position, new_idx))
                else:
                    new_order.append((new_idx, new_idx))
            else:
                # Neuer Header - ans Ende
                new_order.append((len(new_headers) + new_idx, new_idx))

        # Sortiere nach visueller Position
        new_order.sort(key=lambda x: x[0])

        # Wende Reihenfolge an
        for target_visual_idx, logical_idx in enumerate(new_order):
            current_visual_idx = header.visualIndex(logical_idx[1])
            if current_visual_idx != target_visual_idx:
                header.moveSection(current_visual_idx, target_visual_idx)

        # Stelle Spaltenbreiten wieder her
        for new_idx, new_name in enumerate(new_headers):
            if new_name in saved_name_to_idx:
                old_logical_idx = saved_name_to_idx[new_name]
                if old_logical_idx < len(self._saved_column_widths):
                    width = self._saved_column_widths[old_logical_idx]
                    header.resizeSection(new_idx, width)

    def get_headers(self) -> List[str]:
        """
        Retrieves a list of column headers from the model based on the current configuration.

        This method iterates through the columns of the model and collects the text of each
        horizontal header. It selectively includes or excludes specific headers based on
        field configurations defined in the associated `config` object. For example, the
        header "Kategorie" will be excluded if it is not present in `config.fields`.

        :return: A list of strings representing the headers from the model.
        :rtype: List[str]
        """
        headers = []
        for col in range(self.model.columnCount()):
            header_text = self.model.horizontalHeaderItem(col).text()

            # Kategorie nur exportieren wenn sie in config.fields ist
            if header_text == "Kategorie" and "Kategorie" not in self.config.fields:
                continue

            headers.append(header_text)
        return headers

    def get_column_order(self) -> List[int]:
        """
        Calculate and return the order of columns in a tree view based on their visual indices
        in the header. This method takes into account certain configurations and adjustments
        such as skipping a specific column ('Kategorie') if it is not included in the
        configuration fields.

        :returns: A list of integers representing the logical indices of the columns in the
            visual order. If a previously saved column order exists, it returns a copy of it.
        :rtype: List[int]
        """
        # Verwende gespeicherte Werte wenn vorhanden
        if self._saved_column_order:
            return self._saved_column_order.copy()

        header = self.tree_view.header()
        visual_to_logical = []

        # Finde Index der Kategorie-Spalte (falls vorhanden und nicht in fields)
        kategorie_logical_idx = -1
        if "Kategorie" not in self.config.fields:
            for col in range(self.model.columnCount()):
                if self.model.horizontalHeaderItem(col).text() == "Kategorie":
                    kategorie_logical_idx = col
                    break

        offset = 0
        for visual_index in range(header.count()):
            logical_index = header.logicalIndex(visual_index)

            # Überspringe Kategorie wenn nicht gewählt
            if logical_index == kategorie_logical_idx:
                offset += 1
                continue

            # Passe Index an (nach Entfernung der Kategorie-Spalte)
            adjusted_index = logical_index - offset
            visual_to_logical.append(adjusted_index)

        return visual_to_logical

    def get_column_widths(self) -> List[int]:
        """
        Calculate and return the column widths for a tree view based on its header and
        configuration. The method retrieves the current widths of columns in the tree
        view, skipping any excluded columns such as "Kategorie," if specified in the
        configuration.

        :returns: A list of integer values representing the width of each column.
        :rtype: List[int]
        """
        # Verwende gespeicherte Werte wenn vorhanden
        if self._saved_column_widths:
            return self._saved_column_widths.copy()

        header = self.tree_view.header()
        widths = []

        # Finde Index der Kategorie-Spalte (falls vorhanden und nicht in fields)
        kategorie_logical_idx = -1
        if "Kategorie" not in self.config.fields:
            for col in range(self.model.columnCount()):
                if self.model.horizontalHeaderItem(col).text() == "Kategorie":
                    kategorie_logical_idx = col
                    break

        for visual_index in range(header.count()):
            logical_index = header.logicalIndex(visual_index)

            # Überspringe Kategorie wenn nicht gewählt
            if logical_index == kategorie_logical_idx:
                continue

            widths.append(header.sectionSize(visual_index))

        return widths

    def _setup_ui(self):
        """
        Configures the user interface layout and initializes all widgets and their
        properties for the UI component managing transaction entries.

        This method sets up a vertical layout that includes a header layout
        with title and utility buttons, a tree view for displaying hierarchical
        data in an organized manner, and a hidden button for lazy loading
        additional data. Each widget is fully configured with attributes
        such as styles, sizes, interactivity settings, connections to event
        handlers, and other properties required for its functionality.

        Attributes
        ----------
        title_label : QLabel
            Displays the title of the header with a bold font.
        info_label : QLabel
            Provides additional status or informational messages in the header.
        expand_all_btn : QPushButton
            Button for expanding all collapsing nodes in the tree view.
        collapse_all_btn : QPushButton
            Button for collapsing all expanding nodes in the tree view.
        tree_view : QTreeView
            Displays hierarchical data with customizable headers and sections.
        model : QStandardItemModel
            Data model defining the structure of the hierarchical data in the tree view.
        load_more_btn : QPushButton
            Visible when data can be lazily loaded. Hidden by default.

        Raises
        ------
        None

        :return: None
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # === HEADER ===
        header = QHBoxLayout()

        self.title_label = QLabel("Buchungen")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(self.title_label)

        header.addStretch()

        self.info_label = QLabel("Keine Daten")
        self.info_label.setStyleSheet("color: gray; font-size: 11px;")
        header.addWidget(self.info_label)

        # Expand/Collapse Buttons
        self.expand_all_btn = QPushButton("▼ Alle ausklappen")
        self.expand_all_btn.setMaximumWidth(140)
        self.expand_all_btn.clicked.connect(self._on_expand_all)
        header.addWidget(self.expand_all_btn)

        self.collapse_all_btn = QPushButton("▶ Alle einklappen")
        self.collapse_all_btn.setMaximumWidth(140)
        self.collapse_all_btn.clicked.connect(self._on_collapse_all)
        header.addWidget(self.collapse_all_btn)

        # Refresh Button
        refresh_btn = QPushButton("⟳ Aktualisieren")
        refresh_btn.setMaximumWidth(120)
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # === SEARCH FIELD ===
        search_layout = QHBoxLayout()
        search_label = QLabel("Suche:")
        search_layout.addWidget(search_label)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Suche in allen angezeigten ?Feldern...")
        self.search_field.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_field)

        layout.addLayout(search_layout)

        # === TREE VIEW ===
        self.tree_view = QTreeView()
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.tree_view.setSortingEnabled(False)
        self.tree_view.setUniformRowHeights(False)

        # Expand/Collapse Dreiecke konfigurieren
        self.tree_view.setRootIsDecorated(True)  # Zeige Expand-Dreiecke
        self.tree_view.setIndentation(15)  # Minimale Einrückung nur für Dreiecke
        self.tree_view.setItemsExpandable(True)

        # Model
        self.model = QStandardItemModel()
        self.model.setColumnCount(2)
        self.tree_view.setModel(self.model)

        # Initial-Header mit korrektem Alignment
        kategorie_item = QStandardItem("Kategorie")
        betrag_item = QStandardItem("Betrag")
        betrag_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.model.setHorizontalHeaderItem(0, kategorie_item)
        self.model.setHorizontalHeaderItem(1, betrag_item)

        # Header
        self.tree_view.setHeaderHidden(False)  # Explizit sichtbar machen
        self.tree_view.header().setStretchLastSection(False)
        self.tree_view.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tree_view.header().setVisible(True)  # Sicherstellen dass Header sichtbar ist
        self.tree_view.header().setMinimumHeight(25)  # Mindesthöhe für Header
        self.tree_view.header().setDefaultSectionSize(150)  # Default Breite

        # Spalten verschiebbar machen
        self.tree_view.header().setSectionsMovable(True)
        self.tree_view.header().setDragEnabled(True)
        self.tree_view.header().setDragDropMode(QHeaderView.DragDropMode.InternalMove)

        # WICHTIG: Bei Gruppierung muss Kategorie-Spalte IMMER visuell an Position 0 sein
        # da QTreeView die Expand-Dreiecke immer in der ersten visuellen Spalte anzeigt
        self.tree_view.header().sectionMoved.connect(self._on_header_section_moved)

        # CSS für bessere Sichtbarkeit
        self.tree_view.setStyleSheet("""
            QTreeView {
                outline: 0;
            }
        """)

        layout.addWidget(self.tree_view)

        # === LAZY LOAD BUTTON (versteckt by default) ===
        self.load_more_btn = QPushButton("⬇ Weitere laden...")
        self.load_more_btn.setMaximumWidth(200)
        self.load_more_btn.clicked.connect(self._load_more_transactions)
        self.load_more_btn.setVisible(False)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.load_more_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def set_data(self, config: ReportConfig, transactions: List[Transaction], tree: Optional[CategoryTree] = None):
        """
        Sets the data for the report, including the configuration, transactions, and optional category
        tree. Handles lazy loading if the number of transactions exceeds a specific threshold. Updates
        the UI accordingly and rebuilds the model.

        :param config: The configuration settings for the report.
        :type config: ReportConfig
        :param transactions: The list of transactions to be displayed in the report.
        :type transactions: List[Transaction]
        :param tree: The optional category tree associated with the report. If none is provided, it is
             treated as `None`.
        :type tree: Optional[CategoryTree]
        :return: None
        """
        self.config = config
        self.transactions = transactions
        self.tree = tree

        # Lazy Loading prüfen
        self._total_transaction_count = len(transactions)
        self._is_lazy_loading = self._total_transaction_count > self.LAZY_LOAD_THRESHOLD

        if self._is_lazy_loading:
            # Nur ersten Chunk laden
            self._loaded_transaction_count = min(self.LAZY_LOAD_CHUNK_SIZE, self._total_transaction_count)
            self.info_label.setText(f"{self._loaded_transaction_count} / {self._total_transaction_count} Buchungen geladen")
            self.load_more_btn.setVisible(True)
            self.load_more_btn.setText(f"⬇ Weitere {self.LAZY_LOAD_CHUNK_SIZE} laden...")
        else:
            # Alle laden
            self._loaded_transaction_count = self._total_transaction_count
            self.info_label.setText(f"{self._total_transaction_count} Buchungen")
            self.load_more_btn.setVisible(False)

        # Model neu aufbauen
        self._build_model()

    def _load_more_transactions(self):
        """
        Handles lazy loading of transaction data in chunks for efficient data management. Updates the relevant
        UI components, including the info label and load-more button, to reflect the current state of loaded
        transactions. Rebuilds the transaction model after loading a new chunk.

        :raises RuntimeError: If lazy loading is improperly configured.
        """
        if not self._is_lazy_loading:
            return

        # Nächsten Chunk laden
        remaining = self._total_transaction_count - self._loaded_transaction_count
        chunk_size = min(self.LAZY_LOAD_CHUNK_SIZE, remaining)

        self._loaded_transaction_count += chunk_size

        # Info aktualisieren
        self.info_label.setText(f"{self._loaded_transaction_count} / {self._total_transaction_count} Buchungen geladen")

        # Button verstecken wenn alle geladen
        if self._loaded_transaction_count >= self._total_transaction_count:
            self.load_more_btn.setVisible(False)
        else:
            remaining = self._total_transaction_count - self._loaded_transaction_count
            next_chunk = min(self.LAZY_LOAD_CHUNK_SIZE, remaining)
            self.load_more_btn.setText(f"⬇ Weitere {next_chunk} laden...")

        # Model neu aufbauen
        self._build_model()

    def _build_model(self):
        """
        Constructs or updates the model for the tree view component based on the provided
        configuration and dataset. It handles both flat and hierarchical groupings, applies
        column settings, adjusts header labels, and restores previously saved column widths
        if available. Additional footer rows are appended if specific settings are enabled.

        :return: None
        """
        # Speichere aktuelle Spalteneinstellungen (falls Model existiert)
        self._save_column_settings()

        if not self.config or not self.transactions:
            # Nur Platzhalter-Header wenn keine Config
            headers = ["Kategorie", "Betrag"]
            # Neues Model erstellen
            self.model = QStandardItemModel()
            self.model.setColumnCount(len(headers))
            self.tree_view.setModel(self.model)

            # Setze Header mit korrektem Alignment
            for i, header_name in enumerate(headers):
                from PyQt6.QtGui import QStandardItem
                item = QStandardItem(header_name)
                if header_name in ["Datum", "Buchungsdatum", "Valuta", "Betrag", "Anzahl"]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.model.setHorizontalHeaderItem(i, item)

            return

        # Header setzen basierend auf Konfiguration
        headers = self.config.fields.copy()

        if self.config.show_count:
            headers.append("Anzahl")

        # WICHTIG: Bei Gruppierung muss "Kategorie" IMMER an Position 0 sein!
        # Die Expand/Collapse-Dreiecke erscheinen in der ersten logischen Spalte
        if self.config.grouping:
            # Entferne "Kategorie" falls vorhanden
            if "Kategorie" in headers:
                headers.remove("Kategorie")
            # Füge "Kategorie" an erster Position ein
            headers.insert(0, "Kategorie")

        # Speichere aktuelle Header-Reihenfolge für Row-Erstellung
        self._current_headers = headers.copy()

        # Neues Model erstellen mit korrekter Spaltenanzahl
        self.model = QStandardItemModel()
        self.model.setColumnCount(len(headers))
        self.model.setHorizontalHeaderLabels(headers)
        self.tree_view.setModel(self.model)

        # Header-Alignment: Datum, Betrag und Anzahl rechtsbündig
        for i, header_name in enumerate(headers):
            header_item = self.model.horizontalHeaderItem(i)
            if header_item and header_name in ["Datum", "Buchungsdatum", "Valuta", "Betrag", "Anzahl"]:
                header_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Prüfe ob Gruppierung aktiv ist
        if not self.config.grouping:
            # Flache Liste
            self._build_flat_list()
            # Verstecke Expand/Collapse Buttons
            self.expand_all_btn.setVisible(False)
            self.collapse_all_btn.setVisible(False)
        else:
            # Hierarchische Gruppierung
            self._build_grouped_tree()
            # Zeige Expand/Collapse Buttons
            self.expand_all_btn.setVisible(True)
            self.collapse_all_btn.setVisible(True)

            # WICHTIG: Bei Gruppierung muss Kategorie-Spalte an visueller Position 0 sein
            # damit die Expand/Collapse-Dreiecke bei der Kategorie erscheinen
            self._ensure_category_column_at_position_zero()

        # Spaltenbreiten anpassen (nur wenn keine gespeicherten Einstellungen)
        if not self._saved_column_widths:
            for i in range(len(headers)):
                self.tree_view.resizeColumnToContents(i)
            # Kategorie-Spalte bei Gruppierung extra anpassen
            if self.config.grouping:
                self.tree_view.resizeColumnToContents(0)  # Kategorie ist immer Spalte 0

        # Stelle gespeicherte Spalteneinstellungen wieder her
        self._restore_column_settings(headers)

        # Füge Footer-Zeilen hinzu (Soll/Haben falls aktiviert)
        self._add_footer_rows()

        # Stelle sicher dass Header-Alignment korrekt ist (nach allen Änderungen)
        self._apply_header_alignment()

    def _build_flat_list(self):
        """
        Builds and populates a flat list of transactions within the model.

        This function sorts the transactions, performs lazy loading if enabled, and
        appends the resulting transaction rows to the model for display. The displayed
        transactions are either a subset based on lazy loading or the full sorted list.

        :return: None
        """
        # Sortieren
        sorted_trans = self._sort_transactions(self.transactions)

        # Lazy Loading: Nur geladene Transaktionen anzeigen
        display_trans = sorted_trans[:self._loaded_transaction_count] if self._is_lazy_loading else sorted_trans

        # Zeilen hinzufügen
        for trans in display_trans:
            row = self._create_transaction_row(trans)
            self.model.appendRow(row)

    def _build_grouped_tree(self):
        """
        Constructs a hierarchical grouping structure for the existing tree based
        on specified grouping levels. Traverses the tree's root nodes and applies
        grouping logic iteratively.

        The grouping levels are defined in the configuration and specify how the
        nodes should be logically grouped (e.g., by "Category" or "Subcategory").
        The method ensures that hierarchical group nodes are added as per the
        grouping configuration.

        :return: None
        """
        if not self.tree:
            return

        # Gruppierungs-Ebenen
        # Root-Knoten durchgehen - zeige ALLE Ebenen rekursiv an
        for root_name, root_node in sorted(self.tree.root_nodes.items()):
            self._add_group_node(root_node, None, level=0)

    def _add_group_node(self, node: CategoryNode, parent_item: Optional[QStandardItem], level: int):
        """
        Adds a group node to the model, representing a category and its associated transactions or
        child categories, recursively. Nodes with no transactions, direct or in their descendants,
        are skipped.

        Supports unlimited hierarchy depth - all levels are displayed recursively.

        :param node: The `CategoryNode` representing the current category to be added.
        :param parent_item: The parent `QStandardItem` to which this node belongs. Use `None`
            if the node is a root node.
        :param level: The current depth level of the node in the hierarchy.
        :return: None
        """
        # Überspringe Knoten ohne Transaktionen (weder direkt noch in Kindern)
        # AUSNAHME: "ohne Zuordnung" immer anzeigen (auch wenn leer)
        if node.transaction_count == 0 and node.name != "ohne Zuordnung":
            return

        # Gruppierungs-Zeile erstellen
        group_row = self._create_group_row(node, level)

        # Zu Parent oder Root hinzufügen
        if parent_item is None:
            self.model.appendRow(group_row)
        else:
            parent_item.appendRow(group_row)

        # Children rekursiv hinzufügen (alle Ebenen!)
        if node.children:
            for child_name, child_node in sorted(node.children.items()):
                self._add_group_node(child_node, group_row[0], level + 1)

        # Transaktionen hinzufügen (auf dieser Ebene)
        if node.transaction_ids:
            trans_for_node = [t for t in self.transactions if t.id in node.transaction_ids]
            sorted_trans = self._sort_transactions(trans_for_node)

            for trans in sorted_trans:
                trans_row = self._create_transaction_row(trans)
                group_row[0].appendRow(trans_row)

    def _create_group_row(self, node: CategoryNode, level: int) -> List[QStandardItem]:
        """
        Generates a row of `QStandardItem` objects representing a category group for
        a hierarchical data structure. The row includes formatted fields based on
        the configuration and the hierarchy level.

        :param node: The category node containing data to populate the row. Includes
            attributes such as the name, total amount, and transaction count of the
            category.
        :type node: CategoryNode
        :param level: The hierarchical level of the category node, where 0 represents
            the top level. Determines the indentation and visual styling for the row.
        :type level: int
        :return: A list of `QStandardItem` objects corresponding to the configured
            fields for the category group (e.g., name, amount, count).
        :rtype: List[QStandardItem]
        """
        row = []

        # Iteriere über die aktuellen Header (in korrekter Reihenfolge!)
        # NICHT über config.fields, da wir die Reihenfolge angepasst haben
        headers = self._current_headers if self._current_headers else self.config.fields
        for field in headers:
            if field == "Kategorie":
                # Gruppenname mit leichter Einrückung für Unterebenen
                indent = '  ' * level if level > 0 else ''
                name_item = QStandardItem(f"{indent}{node.name}")
                name_item.setFont(self._get_group_font(level))
                name_item.setBackground(self._get_group_background(level))
                row.append(name_item)
            elif field == "Betrag":
                # Subtotal
                amount_item = QStandardItem(self._format_amount(node.total_amount))
                amount_item.setFont(self._get_group_font(level))
                amount_item.setBackground(self._get_group_background(level))
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                row.append(amount_item)
            else:
                # Leer für andere Felder (Datum, Verwendungszweck, etc.)
                item = QStandardItem("")
                item.setBackground(self._get_group_background(level))
                row.append(item)

        # Anzahl-Spalte
        if self.config.show_count:
            count_item = QStandardItem(str(node.transaction_count))
            count_item.setFont(self._get_group_font(level))
            count_item.setBackground(self._get_group_background(level))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.append(count_item)

        return row

    def _create_transaction_row(self, trans: Transaction) -> List[QStandardItem]:
        """
        Generates a list of QStandardItem objects representing a transaction row in a table.
        The content and arrangement of the generated items depend on the configured fields
        and settings such as grouping and visibility of the count column.

        :param trans: The transaction object that contains the details for the row.
        :type trans: Transaction
        :return: A list of QStandardItem objects representing the data of the transaction
                 for the configured fields.
        :rtype: List[QStandardItem]
        """
        row = []

        # Iteriere über die aktuellen Header (in korrekter Reihenfolge!)
        # NICHT über config.fields, da wir die Reihenfolge angepasst haben
        headers = self._current_headers if self._current_headers else self.config.fields
        for field in headers:
            item = QStandardItem()

            if field == "Kategorie":
                # Kategorie kann angezeigt werden oder leer sein bei Gruppierung
                if self.config.grouping:
                    # Bei Gruppierung: leer (Kategorie ist schon durch Gruppe gezeigt)
                    pass
                else:
                    # Bei flacher Liste: Kategorie anzeigen
                    item.setText(trans.category_name or "")
            elif field == "Datum":
                # Verwende das ausgewählte Datumsfeld
                from src.data.models.domain_models import DateFieldType
                if self.config and self.config.date_range.date_field == DateFieldType.BOOKING_DATE:
                    date_value = trans.booking_date
                else:
                    date_value = trans.value_date
                item.setText(date_value.strftime("%d.%m.%Y"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            elif field == "Betrag":
                item.setText(self._format_amount(trans.amount))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            elif field == "Verwendungszweck":
                # Zeige original zweck, nicht den kombinierten Text
                item.setText(trans.purpose_original or "")
            elif field == "Gegenkonto":
                item.setText(trans.counter_account_name or "")
            elif field == "Kontonummer":
                item.setText(trans.counter_account_number or "")
            elif field == "BLZ":
                item.setText(trans.counter_account_blz or "")
            elif field == "Konto":
                item.setText(trans.account_name or "")
            elif field == "Buchungsdatum":
                item.setText(trans.booking_date.strftime("%d.%m.%Y"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            elif field == "Valuta":
                item.setText(trans.value_date.strftime("%d.%m.%Y"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            row.append(item)

        # Anzahl-Spalte (leer bei einzelner Transaktion)
        if self.config.show_count:
            row.append(QStandardItem(""))

        return row

    def _create_total_row(self, label: str, transactions: List[Transaction], is_grand_total: bool = False) -> List[QStandardItem]:
        """
        Creates a row of total values to be displayed in a table view. The row can represent either a
        grand total or a regular total, depending on the value of the provided flag. The first column
        contains a label describing the row, while subsequent columns display values for configured fields
        and potentially a total count of transactions if applicable.

        :param label: A descriptive label to be used in the first column of the row.
        :type label: str
        :param transactions: A list of transactions whose aggregate values are used to populate the row.
        :type transactions: List[Transaction]
        :param is_grand_total: A flag indicating whether this row represents a grand total. Defaults to False.
        :type is_grand_total: bool
        :return: A list of items representing the row, including its label, aggregated field values,
            and transaction count (if configured).
        :rtype: List[QStandardItem]
        """
        row = []

        # Erste Spalte: Label
        label_item = QStandardItem(label)
        label_item.setFont(self._get_total_font(is_grand_total))
        label_item.setBackground(self._get_total_background(is_grand_total))
        row.append(label_item)

        # Weitere Spalten
        for field in self.config.fields[1:]:
            if field == "Betrag":
                total = sum(t.amount for t in transactions)
                amount_item = QStandardItem(self._format_amount(total))
                amount_item.setFont(self._get_total_font(is_grand_total))
                amount_item.setBackground(self._get_total_background(is_grand_total))
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                row.append(amount_item)
            else:
                item = QStandardItem("")
                item.setBackground(self._get_total_background(is_grand_total))
                row.append(item)

        # Anzahl
        if self.config.show_count:
            count_item = QStandardItem(str(len(transactions)))
            count_item.setFont(self._get_total_font(is_grand_total))
            count_item.setBackground(self._get_total_background(is_grand_total))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.append(count_item)

        return row

    def _sort_transactions(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Sorts a list of transactions based on the provided configuration. The sorting
        can be performed on various fields such as transaction date, amount, or
        category name, and can be conducted in ascending or descending order.

        :param transactions: A list of `Transaction` objects to be sorted.
        :type transactions: List[Transaction]
        :return: A list of `Transaction` objects sorted according to the configuration.
        :rtype: List[Transaction]
        """
        if not self.config:
            return transactions

        reverse = (self.config.sort_order == "desc")

        if self.config.sort_field == "Datum":
            # Sortiere nach dem ausgewählten Datumsfeld
            from src.data.models.domain_models import DateFieldType
            if self.config.date_range.date_field == DateFieldType.BOOKING_DATE:
                return sorted(transactions, key=lambda t: t.booking_date, reverse=reverse)
            else:
                return sorted(transactions, key=lambda t: t.value_date, reverse=reverse)
        elif self.config.sort_field == "Betrag":
            return sorted(transactions, key=lambda t: t.amount, reverse=reverse)
        elif self.config.sort_field == "Kategorie":
            return sorted(transactions, key=lambda t: t.category_name if t.category_name else "", reverse=reverse)
        else:
            return transactions

    def _format_amount(self, amount: Decimal) -> str:
        """
        Formats a Decimal amount into a string representation with European currency
        formatting. The formatted amount uses a comma as the decimal separator and a
        dot for grouping thousands. The Euro symbol (€) is appended at the end.

        :param amount: The decimal amount to be formatted.
        :type amount: Decimal
        :return: The formatted string representation of the given amount.
        :rtype: str
        """
        return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    def _on_expand_all(self):
        """
        Expands all nodes in the tree view.

        This method triggers the expansion of all collapsible nodes in the
        tree view, making all items visible.

        :return: None
        :rtype: None
        """
        self.tree_view.expandAll()

    def _on_collapse_all(self):
        """
        Collapses all items in the tree view.

        :return: None
        """
        self.tree_view.collapseAll()

    def _on_search_text_changed(self, search_text: str):
        """
        Filter tree view based on search text.
        Searches in all text columns of the tree.

        :param search_text: The search query
        :return: None
        """
        if not search_text:
            # Show all items if search is empty
            self._show_all_items()
            return

        search_text = search_text.lower()

        # Hide items that don't match search
        def filter_item(item: QStandardItem, parent_visible: bool = False) -> bool:
            """
            Recursively filter items. Returns True if item or any child matches.
            """
            # Check if this item matches
            row_matches = False
            row = item.row()
            parent = item.parent() if item.parent() else self.model.invisibleRootItem()

            # Search in all columns of this row
            for col in range(self.model.columnCount()):
                cell_item = parent.child(row, col)
                if cell_item:
                    text = cell_item.text().lower()
                    if search_text in text:
                        row_matches = True
                        break

            # Check children recursively
            has_matching_children = False
            if item.hasChildren():
                for i in range(item.rowCount()):
                    child = item.child(i, 0)
                    if child and filter_item(child, row_matches):
                        has_matching_children = True

            # Show item if it matches, has matching children, or parent is visible
            should_show = row_matches or has_matching_children or parent_visible

            # Hide/show the row in tree view
            index = self.model.indexFromItem(item)
            self.tree_view.setRowHidden(index.row(), index.parent(), not should_show)

            return should_show

        # Filter from root
        root = self.model.invisibleRootItem()
        for i in range(root.rowCount()):
            item = root.child(i, 0)
            if item:
                filter_item(item)

        # Expand all visible items when searching
        if search_text:
            self.tree_view.expandAll()

    def _show_all_items(self):
        """
        Show all items in the tree view (remove search filter).
        """
        def show_item_recursive(item: QStandardItem):
            index = self.model.indexFromItem(item)
            self.tree_view.setRowHidden(index.row(), index.parent(), False)

            if item.hasChildren():
                for i in range(item.rowCount()):
                    child = item.child(i, 0)
                    if child:
                        show_item_recursive(child)

        root = self.model.invisibleRootItem()
        for i in range(root.rowCount()):
            item = root.child(i, 0)
            if item:
                show_item_recursive(item)

    def _apply_header_alignment(self):
        """
        Applies correct text alignment to header items.
        Must be called after model changes to ensure alignment is correct.
        """
        for i in range(self.model.columnCount()):
            header_item = self.model.horizontalHeaderItem(i)
            if header_item:
                header_text = header_item.text()
                if header_text in ["Datum", "Buchungsdatum", "Valuta", "Betrag", "Anzahl"]:
                    header_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    header_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _ensure_category_column_at_position_zero(self):
        """
        Ensures that the "Kategorie" column is always at visual position 0.
        This is crucial because QTreeView shows expand/collapse triangles in the first visual column.
        """
        if not self.config or not self.config.grouping:
            return

        header = self.tree_view.header()

        # Finde den logischen Index der Kategorie-Spalte
        kategorie_logical_idx = None
        for i in range(self.model.columnCount()):
            header_text = self.model.headerData(i, Qt.Orientation.Horizontal)
            if header_text == "Kategorie":
                kategorie_logical_idx = i
                break

        if kategorie_logical_idx is None:
            return

        # Prüfe aktuelle visuelle Position der Kategorie-Spalte
        kategorie_visual_idx = header.visualIndex(kategorie_logical_idx)

        # Wenn nicht an Position 0, bewege sie dorthin
        if kategorie_visual_idx != 0:
            header.moveSection(kategorie_visual_idx, 0)

    def _on_header_section_moved(self, logical_index: int, old_visual_index: int, new_visual_index: int):
        """
        Handles the event when a section of the header is moved. This method ensures that
        the "Kategorie" column always stays at visual position 0 when grouping is enabled,
        because QTreeView shows expand/collapse triangles in the first visual column.

        :param logical_index: The logical index of the affected section of the header.
        :type logical_index: int
        :param old_visual_index: The previous visual index of the section before the move.
        :type old_visual_index: int
        :param new_visual_index: The new visual index of the section after the move.
        :type new_visual_index: int
        :return: None
        """
        if not self.config or not self.config.grouping:
            return

        header = self.tree_view.header()

        # Finde den logischen Index der Kategorie-Spalte
        kategorie_logical_idx = None
        for i in range(self.model.columnCount()):
            header_text = self.model.headerData(i, Qt.Orientation.Horizontal)
            if header_text == "Kategorie":
                kategorie_logical_idx = i
                break

        if kategorie_logical_idx is None:
            return

        # Prüfe ob Kategorie-Spalte jetzt an visueller Position 0 ist
        kategorie_visual_idx = header.visualIndex(kategorie_logical_idx)

        # Wenn Kategorie-Spalte NICHT an Position 0 ist, korrigiere das
        if kategorie_visual_idx != 0:
            # Blockiere Signale um Rekursion zu vermeiden
            header.blockSignals(True)

            # Bewege Kategorie-Spalte zurück an Position 0
            header.moveSection(kategorie_visual_idx, 0)

            header.blockSignals(False)

    def _add_footer_rows(self):
        """
        Adds footer rows to the table model for displaying summary calculations,
        such as total amount, debit, and credit balances, as well as optional counts
        of transactions, depending on configuration settings. The footer rows may include:

        - Grand total of all transaction amounts if `show_grand_total` is enabled.
        - Debit total (expenses) and credit total (income) if `show_debit_credit` is
          enabled.

        Each row is styled with customizable fonts and background colors, and values
        are aligned appropriately.

        :raises: This method does not explicitly raise exceptions but relies on proper
                 initialization of `transactions`, `config`, and `model`.

        :param self: An instance of the class containing the method.
        :return: None
        """
        if not self.transactions:
            return

        # Berechne Summen
        gesamt = sum(t.amount for t in self.transactions)
        soll = sum(t.amount for t in self.transactions if t.amount < 0)
        haben = sum(t.amount for t in self.transactions if t.amount > 0)

        # Verwende konfigurierte Felder
        fields = self.config.fields

        # Font für Footer
        footer_font = QFont()
        footer_font.setBold(True)

        # === GESAMTSUMME (immer wenn show_grand_total aktiv) ===
        if self.config.show_grand_total:
            row = []

            # Label-Spalte
            label_item = QStandardItem("Gesamtsumme")
            label_item.setFont(footer_font)
            label_item.setBackground(QBrush(QColor(200, 200, 200, 150)))
            row.append(label_item)

            # Weitere Spalten
            for field in fields[1:]:
                item = QStandardItem()
                item.setBackground(QBrush(QColor(200, 200, 200, 150)))

                if field == "Betrag":
                    item.setText(self._format_amount(gesamt))
                    item.setFont(footer_font)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setText("")

                row.append(item)

            # Anzahl-Spalte
            if self.config.show_count:
                count_item = QStandardItem(str(len(self.transactions)))
                count_item.setFont(footer_font)
                count_item.setBackground(QBrush(QColor(200, 200, 200, 150)))
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                row.append(count_item)

            self.model.appendRow(row)

        # === SOLL-SUMME (nur wenn show_debit_credit aktiv) ===
        if self.config.show_debit_credit:
            row = []

            label_item = QStandardItem("Soll (Ausgaben)")
            label_item.setFont(footer_font)
            label_item.setBackground(QBrush(QColor(255, 200, 200, 150)))  # Rötlich
            row.append(label_item)

            for field in fields[1:]:
                item = QStandardItem()
                item.setBackground(QBrush(QColor(255, 200, 200, 150)))

                if field == "Betrag":
                    item.setText(self._format_amount(soll))
                    item.setFont(footer_font)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setText("")

                row.append(item)

            if self.config.show_count:
                count = len([t for t in self.transactions if t.amount < 0])
                count_item = QStandardItem(str(count))
                count_item.setFont(footer_font)
                count_item.setBackground(QBrush(QColor(255, 200, 200, 150)))
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                row.append(count_item)

            self.model.appendRow(row)

            # === HABEN-SUMME ===
            row = []

            label_item = QStandardItem("Haben (Einnahmen)")
            label_item.setFont(footer_font)
            label_item.setBackground(QBrush(QColor(200, 255, 200, 150)))  # Grünlich
            row.append(label_item)

            for field in fields[1:]:
                item = QStandardItem()
                item.setBackground(QBrush(QColor(200, 255, 200, 150)))

                if field == "Betrag":
                    item.setText(self._format_amount(haben))
                    item.setFont(footer_font)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setText("")

                row.append(item)

            if self.config.show_count:
                count = len([t for t in self.transactions if t.amount > 0])
                count_item = QStandardItem(str(count))
                count_item.setFont(footer_font)
                count_item.setBackground(QBrush(QColor(200, 255, 200, 150)))
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                row.append(count_item)

            self.model.appendRow(row)

    def _get_group_font(self, level: int) -> QFont:
        """
        Gets the font settings for a specified group level.

        This function returns a QFont object adjusted based on the specified
        group level. It modifies font attributes such as point size and boldness
        to match the visual requirements for different levels.

        Supports arbitrary depth hierarchies - deeper levels get progressively
        smaller fonts while maintaining bold formatting.

        :param level: Integer representing the group level. A value of `0`
            corresponds to the topmost level with larger font settings, while
            higher values decrease the font size where applicable.
        :return: A QFont object configured with the appropriate font settings
            for the specified group level.
        :rtype: QFont
        """
        font = QFont()
        if level == 0:
            font.setPointSize(11)
            font.setBold(True)
        elif level == 1:
            font.setPointSize(10)
            font.setBold(True)
        elif level == 2:
            font.setPointSize(9)
            font.setBold(True)
        else:
            # Levels 3+ use standard size but stay bold
            font.setBold(True)
        return font

    def _get_group_background(self, level: int) -> QBrush:
        """
        Retrieves the background brush for a group based on its level. The function ensures
        transparency to allow the TreeView's alternating colors to be used, providing a subtle
        visual distinction without overriding the default appearance.

        :param level: The hierarchical level of the group for which the background brush
                      is being retrieved.
        :type level: int
        :return: A QBrush object representing the transparent background for the group.
        :rtype: QBrush
        """
        # Verwende transparente Farben, die vom TreeView alternating colors übernommen werden
        # Keine besonderen Hintergrundfarben - nur leichte visuelle Unterscheidung
        return QBrush(QColor(0, 0, 0, 0))  # Transparent

    def _get_total_font(self, is_grand_total: bool) -> QFont:
        """
        Calculates and returns a QFont object configured based on whether the total is a grand
        total or not. The font will always be bold, and its size will be adjusted if it is a grand total.

        :param is_grand_total: A boolean indicating if the total is a grand total. If True, the font's point
            size will be set to 12.
        :return: A QFont object configured with bold formatting and adjusted point size if
            applicable.
        :rtype: QFont
        """
        font = QFont()
        font.setBold(True)
        if is_grand_total:
            font.setPointSize(12)
        return font

    def _get_total_background(self, is_grand_total: bool) -> QBrush:
        """
        Determines the background brush color based on whether the total
        is a grand total or not. The method uses semi-transparent green
        shades that work well on both light and dark backgrounds.

        :param is_grand_total: A boolean flag that specifies whether the
                               total is a grand total or a regular total.
                               If True, a more opaque green shade is used.
        :return: A QBrush object representing the background color
                 corresponding to the total type.
        """
        # Verwende semi-transparente Grüntöne für Summen
        # Diese funktionieren auf hellem und dunklem Hintergrund
        if is_grand_total:
            return QBrush(QColor(76, 175, 80, 60))  # Grün, 24% Deckkraft
        else:
            return QBrush(QColor(76, 175, 80, 30))  # Grün, 12% Deckkraft


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from datetime import date
    from src.data.models.domain_models import Category, Account, DateRange

    app = QApplication(sys.argv)

    # Test-Daten
    cat1 = Category(id=1, name="Versicherungen:KFZ:Allianz")
    cat2 = Category(id=2, name="Versicherungen:KFZ:Ergo")
    acc1 = Account(id=1, name="Girokonto", account_number="12345")

    transactions = [
        Transaction(
            id=1,
            date=date(2024, 1, 15),
            amount=Decimal("-150.00"),
            description="KFZ-Versicherung Allianz",
            category=cat1,
            account=acc1
        ),
        Transaction(
            id=2,
            date=date(2024, 2, 15),
            amount=Decimal("-150.00"),
            description="KFZ-Versicherung Allianz",
            category=cat1,
            account=acc1
        ),
        Transaction(
            id=3,
            date=date(2024, 1, 20),
            amount=Decimal("-80.00"),
            description="Haftpflicht Ergo",
            category=cat2,
            account=acc1
        ),
    ]

    # Config
    config = ReportConfig(
        account_ids=[1],
        category_ids=[1, 2],
        date_range=DateRange(start_date=date(2024, 1, 1), end_date=date(2024, 12, 31)),
        fields=["Kategorie", "Datum", "Betrag", "Verwendungszweck"],
        grouping=["Kategorie", "Subkategorie"],
        sort_field="Datum",
        sort_order="asc",
        show_subtotals=True,
        show_grand_total=True,
        show_count=True
    )

    # Tree bauen
    builder = HierarchyBuilder()
    tree = builder.build_tree([cat1, cat2])
    tree = builder.assign_transactions(tree, transactions)
    tree = builder.calculate_aggregates(tree, transactions)

    # Widget
    widget = PreviewWidget()
    widget.set_data(config, transactions, tree)
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
