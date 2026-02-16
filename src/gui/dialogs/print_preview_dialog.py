"""
===============================================================================
Project   : Hibi-BuRe
Module    : print_preview_dialog.py
Created   : 13.02.26
Author    : florian
Purpose   : PrintPreviewDialog provides a dialog for previewing and exporting reports.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Optional
from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QPageLayout

from src.data.models.report_config import ReportConfig
from src.data.models.domain_models import Transaction
from src.business.services.hierarchy_builder import CategoryTree, CategoryNode


class PrintPreviewDialog(QDialog):
    """
    Handles the Print Preview dialog for generating and customizing reports,
    allowing users to preview, adjust column settings, and save or print.

    This class provides a graphical interface to visually arrange columns,
    inspect report data in depth, and interact with printing or exporting
    options.

    :ivar config: The configuration settings for the report.
    :type config: ReportConfig
    :ivar transactions: The list of transactions to be displayed in the report.
    :type transactions: List[Transaction]
    :ivar tree: The category tree structure for hierarchical grouping
        (optional).
    :type tree: Optional[CategoryTree]
    :ivar headers: List of column headers for the table (optional).
    :type headers: Optional[List[str]]
    :ivar column_order: Order of columns for initial display (optional).
    :type column_order: Optional[List[int]]
    :ivar column_widths: The width of columns for initial display (optional).
    :type column_widths: Optional[List[int]]
    :ivar final_column_order: Stores the final column order after user
        adjustments.
    :type final_column_order: List[int]
    :ivar final_column_widths: Stores the final column widths after user
        adjustments.
    :type final_column_widths: List[int]
    """

    def __init__(self, config: ReportConfig, transactions: List[Transaction], tree: Optional[CategoryTree] = None,
                 headers: Optional[List[str]] = None, column_order: Optional[List[int]] = None,
                 column_widths: Optional[List[int]] = None, parent=None):
        """
        Initializes the report preview window UI with configuration settings, transaction data, and optional
        tree, headers, column order, and column widths. This class is responsible for managing the report
        preview and its visual configuration.

        :param config: The configuration object of type ReportConfig used for the report.
        :param transactions: A list of transaction objects of type Transaction to be included in the report.
        :param tree: An optional CategoryTree instance representing a hierarchical structure for grouping
            transactions.
        :param headers: An optional list of strings representing custom column headers for the report table.
        :param column_order: An optional list of integers specifying the order of columns in the table.
        :param column_widths: An optional list of integers specifying the width of each column in the table.
        :param parent: An optional parent widget for this window.
        """
        super().__init__(parent)

        self.config = config
        self.transactions = transactions
        self.tree = tree
        self.headers = headers or []
        self.column_order = column_order or []
        self.column_widths = column_widths or []

        # Für Rückgabe der finalen Spalteneinstellungen
        self.final_column_order: List[int] = []
        self.final_column_widths: List[int] = []

        self.setWindowTitle("Druckvorschau - Hibi-BuBe Report")
        self.resize(1000, 700)

        self._setup_ui()
        self._apply_theme()
        self._build_table()

    def _setup_ui(self):
        """
        Sets up the user interface of the report view, including a header, a table, and a button
        toolbar to interact with the displayed data.

        :Attributes:
            self.table (QTableWidget): Widget for displaying transactional data in a table format.

        """
        layout = QVBoxLayout(self)

        # Header mit Info
        header = QHBoxLayout()

        title = QLabel(f"Report: {len(self.transactions)} Buchungen")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)

        header.addStretch()

        layout.addLayout(header)

        # Tabelle
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Spalten verschiebbar machen
        table_header = self.table.horizontalHeader()
        table_header.setSectionsMovable(True)
        table_header.setDragEnabled(True)
        table_header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)

        # Spaltenbreiten anpassbar machen
        table_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table_header.setStretchLastSection(False)

        # Vertikale Header (Zeilennummern) verstecken
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

        # Button-Leiste
        button_layout = QHBoxLayout()

        print_btn = QPushButton("🖨 Drucken")
        print_btn.clicked.connect(self._print)
        button_layout.addWidget(print_btn)

        pdf_btn = QPushButton("📄 Als PDF speichern")
        pdf_btn.clicked.connect(self._export_pdf)
        button_layout.addWidget(pdf_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self._on_close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _build_table(self):
        """
        Builds and populates the table with headers, row data, and styling configurations.

        This method is responsible for initializing the table structure and filling it with
        transaction data based on the given configuration and hierarchical structure. It adjusts
        the column headers, widths, order, and styles the rows accordingly to enhance clarity
        and readability.

        :raises KeyError: Raised if a required key is missing during the row data construction.

        :attribute config: The current configuration object containing options for table building.
        :type config: Config

        :attribute headers: Predefined table headers if available.
        :type headers: list[str]

        :attribute column_order: Visual column ordering specified as a list of indices.
        :type column_order: list[int]

        :attribute column_widths: Specific column widths defined as a list of integers.
        :type column_widths: list[int]

        :attribute transactions: List of transactions available for table population.
        :type transactions: list[Transaction]

        :return: None
        """
        # Verwende Header aus dem Hauptfenster (wenn vorhanden) oder erstelle sie neu
        if self.headers:
            # Verwende die gleichen Header wie im Hauptfenster
            headers = self.headers.copy()
        else:
            # Fallback: Erstelle Header aus config
            headers = self.config.fields.copy()
            if self.config.show_count:
                headers.append("Anzahl")

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # Header-Alignment: Datum, Betrag, Anzahl rechtsbündig, Rest linksbündig
        for col_idx in range(len(headers)):
            header_item = self.table.horizontalHeaderItem(col_idx)
            if header_item:
                header_text = header_item.text()
                if header_text in ["Datum", "Buchungsdatum", "Valuta", "Betrag", "Anzahl"]:
                    header_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    header_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Header Style
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)

        # Spaltenreihenfolge anwenden (wenn vorhanden)
        if self.column_order and len(self.column_order) == len(headers):
            # Wende die visuelle Reihenfolge an
            for visual_idx, logical_idx in enumerate(self.column_order):
                header.moveSection(header.visualIndex(logical_idx), visual_idx)

        # Spaltenbreiten setzen (wenn vorhanden) - NACH der Spaltenreihenfolge!
        if self.column_widths and len(self.column_widths) == len(headers):
            for visual_idx, width in enumerate(self.column_widths):
                header.resizeSection(visual_idx, width)
        else:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Letzte Spalte NICHT strecken - alle Spalten gleich behandeln
        header.setStretchLastSection(False)

        # Zeilen hinzufügen
        rows_data = []

        # KEINE Summenzeile im PDF/Druck - nur Daten-Zeilen
        if self.config.grouping and self.tree:
            # Hierarchisch - flach machen
            rows_data.extend(self._flatten_tree(headers))
        else:
            # Flache Liste
            for trans in self.transactions:
                row_data = self._create_transaction_row_data(trans, headers)
                rows_data.append(("transaction", row_data))

        # Footer-Zeilen
        if self.config.show_grand_total:
            total_row = self._create_total_row_data("Gesamtsumme", self.transactions, headers)
            rows_data.append(("total", total_row))

        # Soll/Haben Zeilen (falls aktiviert)
        if self.config.show_debit_credit:
            from decimal import Decimal
            # Soll (Ausgaben)
            soll_trans = [t for t in self.transactions if t.amount < 0]
            if soll_trans:
                soll_row = self._create_total_row_data("Soll (Ausgaben)", soll_trans, headers)
                rows_data.append(("debit", soll_row))

            # Haben (Einnahmen)
            haben_trans = [t for t in self.transactions if t.amount > 0]
            if haben_trans:
                haben_row = self._create_total_row_data("Haben (Einnahmen)", haben_trans, headers)
                rows_data.append(("credit", haben_row))

        # Tabelle füllen - INKLUSIVE Header-Zeilen (ohne separator)
        display_rows = [(t, d) for t, d in rows_data if t != "separator"]
        self.table.setRowCount(len(display_rows))

        for row_idx, (row_type, row_data) in enumerate(display_rows):
            # Bei Header-Zeilen: Spanning über alle Spalten
            if row_type in ["category_header", "subcategory_header"]:
                # Hintergrundfarbe - Dark Mode Support
                from PyQt6.QtGui import QBrush, QColor
                from src.config.settings import settings
                is_dark = settings.app.theme == "dark"

                # Font vorbereiten
                font = QFont()
                font.setBold(True)
                if row_type == "category_header":
                    font.setPointSize(12)
                else:  # subcategory_header
                    font.setPointSize(11)

                # Farben bestimmen
                if row_type == "category_header":
                    if is_dark:
                        bg_color = QColor(60, 60, 60)  # Dunkelgrau für Dark Mode
                        fg_color = QColor(255, 255, 255)  # Weiße Schrift
                    else:
                        bg_color = QColor(220, 220, 220)  # Hellgrau für Light Mode
                        fg_color = QColor(0, 0, 0)  # Schwarze Schrift
                else:  # subcategory_header
                    if is_dark:
                        bg_color = QColor(45, 45, 45)  # Noch dunkler für Dark Mode
                        fg_color = QColor(255, 255, 255)  # Weiße Schrift
                    else:
                        bg_color = QColor(240, 240, 240)  # Sehr hellgrau für Light Mode
                        fg_color = QColor(0, 0, 0)  # Schwarze Schrift

                # Setze nur Item in erster Spalte mit vollem Text
                item = QTableWidgetItem(str(row_data[0]))
                item.setFont(font)
                item.setBackground(QBrush(bg_color))
                item.setForeground(QBrush(fg_color))
                self.table.setItem(row_idx, 0, item)

                # Setze leere Items in anderen Spalten (für Hintergrundfarbe)
                for col_idx in range(1, len(headers)):
                    empty_item = QTableWidgetItem("")
                    empty_item.setBackground(QBrush(bg_color))
                    self.table.setItem(row_idx, col_idx, empty_item)

                # Verbinde (span) alle Spalten für diese Zeile
                # Dadurch wird der Text nicht abgeschnitten
                self.table.setSpan(row_idx, 0, 1, len(headers))

                continue

            # Summen-Zeilen mit speziellem Layout
            if row_type in ["subcategory_total", "category_total", "total", "debit", "credit"]:
                from PyQt6.QtGui import QColor
                from src.config.settings import settings
                is_dark = settings.app.theme == "dark"

                # Font und Farbe basierend auf Typ
                font = QFont()
                font.setBold(True)

                if row_type == "subcategory_total":
                    bg_color = QColor(76, 175, 80, 40) if is_dark else QColor(76, 175, 80, 30)
                elif row_type == "category_total":
                    font.setPointSize(11)
                    bg_color = QColor(76, 175, 80, 70) if is_dark else QColor(76, 175, 80, 50)
                elif row_type == "total":
                    font.setPointSize(12)
                    bg_color = QColor(120, 120, 120, 150) if is_dark else QColor(200, 200, 200, 150)
                elif row_type == "debit":
                    bg_color = QColor(150, 60, 60, 150) if is_dark else QColor(255, 200, 200, 150)
                else:  # credit
                    bg_color = QColor(60, 150, 60, 150) if is_dark else QColor(200, 255, 200, 150)

                # Setze alle Zellen mit Hintergrundfarbe
                for col_idx, cell_value in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_value))
                    item.setFont(font)
                    item.setBackground(bg_color)

                    # Explizit Textfarbe setzen (Dark Mode Support)
                    if is_dark:
                        item.setForeground(QBrush(QColor(255, 255, 255)))  # Weiß
                    else:
                        item.setForeground(QBrush(QColor(0, 0, 0)))  # Schwarz

                    # Rechts-Ausrichtung für Betrag und Anzahl
                    if col_idx < len(headers):
                        header_text = headers[col_idx]
                        if header_text in ["Datum", "Buchungsdatum", "Valuta", "Betrag", "Anzahl"]:
                            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                    self.table.setItem(row_idx, col_idx, item)

                # Finde die Betrag-Spalte für Spanning
                betrag_col = None
                for i, h in enumerate(headers):
                    if h == "Betrag":
                        betrag_col = i
                        break

                # Wenn es mehr als eine Spalte zwischen Label (0) und Betrag gibt, spanne erste Spalte
                if betrag_col and betrag_col > 1:
                    # Spanne erste Spalte über alle Spalten BIS zur Betrag-Spalte (exklusiv)
                    self.table.setSpan(row_idx, 0, 1, betrag_col)

            # Normale Transaktions-Zeilen
            else:
                for col_idx, cell_value in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_value))

                    # Rechts-Ausrichtung für Datum, Betrag und Anzahl
                    if col_idx < len(headers):
                        header_text = headers[col_idx]
                        if header_text in ["Datum", "Buchungsdatum", "Valuta", "Betrag", "Anzahl"]:
                            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                    self.table.setItem(row_idx, col_idx, item)

        # Passe Spaltenbreiten automatisch an den Inhalt an (nach dem Füllen)
        # Nur wenn keine gespeicherten Breiten vorhanden sind
        if not self.column_widths:
            self.table.resizeColumnsToContents()
            # Erste Spalte (meist Kategorie/Label) extra breit für lange Texte
            if self.table.columnCount() > 0:
                current_width = self.table.columnWidth(0)
                self.table.setColumnWidth(0, max(current_width, 250))  # Minimum 250px

    def _create_summary_row_data(self, soll: Decimal, haben: Decimal, gesamt: Decimal, headers: List[str]) -> List[str]:
        """
        Creates a summary row of data containing totals for 'Soll', 'Haben', and 'Gesamt' values, formatted
        according to the provided headers. It includes a specific representation of financial totals in
        certain columns and empty placeholders for others.

        :param soll: The total "Soll" amount.
        :type soll: Decimal
        :param haben: The total "Haben" amount.
        :type haben: Decimal
        :param gesamt: The total "Gesamt" amount obtained from the "Soll" and "Haben".
        :type gesamt: Decimal
        :param headers: A list of column headers determining the structure of the summary row.
        :type headers: List[str]
        :return: The summary row data as a list of strings, formatted based on the provided headers.
        :rtype: List[str]
        """
        row = []
        for header in headers:
            if header == headers[0]:  # Erste Spalte
                row.append("Σ Soll / Haben / Gesamt")
            elif header == "Betrag":
                row.append(f"{self._format_amount(soll)} / {self._format_amount(haben)} / {self._format_amount(gesamt)}")
            elif header == "Anzahl":
                row.append(str(len(self.transactions)))
            else:
                row.append("")
        return row

    def _create_transaction_row_data(self, trans: Transaction, headers: List[str]) -> List[str]:
        """
        Creates and formats a row of transaction data based on provided headers. The transaction data
        is extracted and processed depending on the matching header, such as date, amount, category,
        purpose, and account details.

        :param trans: The transaction instance containing details like amount, date, category, and
                      account information.
        :type trans: Transaction
        :param headers: A list of headers specifying the order and type of transaction elements to
                        include in the formatted row.
        :type headers: List[str]
        :return: A list of strings representing the formatted transaction row based on the given
                 headers.
        :rtype: List[str]
        """
        row = []
        for header in headers:
            if header == "Datum":
                # Verwende das ausgewählte Datumsfeld
                from src.data.models.domain_models import DateFieldType
                if self.config and self.config.date_range.date_field == DateFieldType.BOOKING_DATE:
                    date_value = trans.booking_date
                else:
                    date_value = trans.value_date
                row.append(date_value.strftime("%d.%m.%Y"))
            elif header == "Betrag":
                row.append(self._format_amount(trans.amount))
            elif header == "Kategorie":
                row.append(trans.category_name or "(ohne)")
            elif header == "Verwendungszweck":
                # Zeige original zweck, nicht den kombinierten Text
                row.append(trans.purpose_original or "")
            elif header == "Gegenkonto":
                row.append(trans.counter_account_name or "")
            elif header == "Kontonummer":
                row.append(trans.counter_account_number or "")
            elif header == "BLZ":
                row.append(trans.counter_account_blz or "")
            elif header == "Konto":
                row.append(trans.account_name or "")
            elif header == "Buchungsdatum":
                row.append(trans.booking_date.strftime("%d.%m.%Y"))
            elif header == "Valuta":
                row.append(trans.value_date.strftime("%d.%m.%Y"))
            elif header == "Anzahl":
                row.append("")  # Leer bei Transaktionen
            else:
                row.append("")
        return row

    def _create_total_row_data(self, label: str, transactions: List[Transaction], headers: List[str]) -> List[str]:
        """
        Generates a total row of data based on the provided label, transactions, and headers.
        The resulting row reflects aggregated values, such as the sum of amounts and the count
        of transactions, in relevant header positions.

        :param label: Label representing the row (e.g., a category or identifier).
        :type label: str
        :param transactions: List of transactions used to calculate total amounts and counts.
        :type transactions: List[Transaction]
        :param headers: List of column headers used to align the generated row.
        :type headers: List[str]
        :return: A list of strings representing the generated total row data, aligned with the headers.
        :rtype: List[str]
        """
        total = sum(t.amount for t in transactions)

        row = []
        for header in headers:
            if header == headers[0]:
                row.append(label)
            elif header == "Betrag":
                row.append(self._format_amount(total))
            elif header == "Anzahl":
                row.append(str(len(transactions)))
            else:
                row.append("")
        return row

    def _flatten_tree(self, headers: List[str]) -> List[tuple]:
        """
        Flatten the hierarchical tree structure into a list of tuples for further processing
        or rendering. The method processes root categories and their subcategories,
        collecting transaction data and optional subtotals.

        :param headers: A list of strings representing the column headers that define
            the data structure for flattened tree rows.
        :return: A list of tuples where each tuple contains a row type as a string and
            associated row data as a list. The row types can include "category_header",
            "category_total", "separator", or row data for subcategories and their
            transactions.
        """
        rows = []

        for root_name, root_node in sorted(self.tree.root_nodes.items()):
            if root_node.transaction_count > 0:
                # Kategorie-Überschrift (table_header)
                rows.append(("category_header", [root_node.name]))

                # Verarbeite Unterkategorien und Transaktionen
                category_rows = self._flatten_category_node(root_node, headers, level=0)
                rows.extend(category_rows)

                # Kategorie-Summe
                if self.config.show_subtotals:
                    total_row = self._create_subtotal_row_data(f"Summe {root_node.name}", root_node, headers)
                    rows.append(("category_total", total_row))

                # Separator nach jeder Kategorie
                rows.append(("separator", []))

        return rows

    def _flatten_category_node(self, node: CategoryNode, headers: List[str], level: int) -> List[tuple]:
        """
        Flatten a category node into a list of tuples containing categorized rows, such as subcategory headers,
        transaction rows, and subtotal rows if applicable. This method processes transactions and subcategories
        for the given category node recursively.

        :param node: The category node to process, which may contain subcategories and/or transactions.
        :type node: CategoryNode
        :param headers: A list of headers used for structuring the transaction row data.
        :type headers: List[str]
        :param level: The depth level of the current category node in the hierarchy.
        :type level: int
        :return: A list of tuples where each tuple contains a row type (e.g., "subcategory_header",
                 "transaction", "subcategory_total") and corresponding structured data.
        :rtype: List[tuple]
        """
        rows = []

        # Hat Unterkategorien?
        if node.children:
            # Verarbeite jede Unterkategorie REKURSIV (alle Ebenen!)
            for child_name, child_node in sorted(node.children.items()):
                if child_node.transaction_count > 0:
                    # Unterkategorie-Header
                    rows.append(("subcategory_header", [child_node.name]))

                    # REKURSION: Verarbeite Child-Node (kann selbst weitere Children haben!)
                    child_rows = self._flatten_category_node(child_node, headers, level + 1)
                    rows.extend(child_rows)

                    # Unterkategorie-Summe
                    if self.config.show_subtotals:
                        subtotal_row = self._create_subtotal_row_data(f"Summe {child_node.name}", child_node, headers)
                        rows.append(("subcategory_total", subtotal_row))

        # Direkte Transaktionen auf dieser Ebene (ohne Children)
        if node.transaction_ids and not node.children:
            trans_for_node = [t for t in self.transactions if t.id in node.transaction_ids]
            for trans in trans_for_node:
                trans_row = self._create_transaction_row_data(trans, headers)
                rows.append(("transaction", trans_row))

        return rows

    def _create_subtotal_row_data(self, label: str, node: CategoryNode, headers: List[str]) -> List[str]:
        """
        Generates a list of strings representing a subtotal row based on the provided label, category node,
        and headers. Each header corresponds to a cell value in the row. The first header value is replaced by
        the `label`. The "Betrag" column is populated by the formatted total amount of the category node, and
        the "Anzahl" column is populated by the transaction count. Any other headers result in blank cells.

        :param label: The label to display in the first cell of the subtotal row.
        :type label: str
        :param node: The category node containing total amount and transaction count data.
        :type node: CategoryNode
        :param headers: A list of headers specifying the columns in the row.
        :type headers: List[str]
        :return: A list of strings representing the subtotal row, where each string corresponds to a cell value.
        :rtype: List[str]
        """
        row = []
        for header in headers:
            if header == headers[0]:
                row.append(label)
            elif header == "Betrag":
                row.append(self._format_amount(node.total_amount))
            elif header == "Anzahl":
                row.append(str(node.transaction_count))
            else:
                row.append("")
        return row

    def _format_amount(self, amount: Decimal) -> str:
        """
        Formats a monetary amount into a localized string representation.

        This method converts a numeric monetary value into a string format that adheres
        to European-style formatting with a comma (",") as the decimal separator and
        a period (".") for thousand-grouping. The resultant string includes the Euro
        symbol ("€") appended at the end.

        :param amount: The monetary value to format.
        :type amount: Decimal
        :return: A string representing the formatted monetary value with proper
                 localization.
        :rtype: str
        """
        return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    def _print(self):
        """
        Renders the content to a printer if the print dialog is accepted.

        The method creates a QPrinter object with high resolution mode and opens a
        QPrintDialog for the user to configure print settings. If the user accepts
        the dialog, it proceeds to render the document to the configured printer.

        :raises NotImplementedError: If `_render_to_printer` is not implemented in the
            subclass.

        :param None: The method does not take any external arguments.

        :return: None
        """
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self._render_to_printer(printer)

    def _export_pdf(self):
        """
        Exports a list of transaction data into a PDF file. The function opens a
        file dialog for the user to select the destination of the PDF. If a filename
        is provided, the PDF will be generated and saved at the specified location.
        A confirmation message box is displayed upon successful saving of the file.

        :raises None: This function does not explicitly raise any exceptions.
        """
        from PyQt6.QtWidgets import QFileDialog
        from src.config.settings import settings
        from pathlib import Path

        # Vorgeschlagener Dateiname
        # 1. Priorität: Report-Name (wenn vorhanden und nicht "Neuer Bericht")
        if self.config and self.config.name and self.config.name != "Neuer Bericht":
            safe_name = self.config.name.replace('/', '_').replace('\\', '_').replace(':', '_')
            suggested_name = f"{safe_name}.pdf"
        # 2. Priorität: Datum aus Transaktionen
        elif self.transactions:
            from src.data.models.domain_models import DateFieldType
            if self.config and self.config.date_range.date_field == DateFieldType.BOOKING_DATE:
                date_str = self.transactions[0].booking_date.strftime('%Y%m%d')
            else:
                date_str = self.transactions[0].value_date.strftime('%Y%m%d')
            suggested_name = f"report_{date_str}.pdf"
        else:
            suggested_name = "report_export.pdf"

        # Vollständiger Pfad mit Export-Verzeichnis
        default_path = settings.app.export_dir / suggested_name

        # Datei-Dialog mit Dark Mode Support
        dialog = QFileDialog(self)
        dialog.setWindowTitle("PDF speichern")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter("PDF Files (*.pdf)")
        dialog.setDefaultSuffix("pdf")
        dialog.selectFile(str(default_path))
        
        # Wende Theme auf Dialog an
        if settings.app.theme == "dark":
            dialog.setStyleSheet(self._get_file_dialog_stylesheet())
        
        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return
        
        selected_files = dialog.selectedFiles()
        if not selected_files:
            return
            
        filename = selected_files[0]
        
        if filename:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(filename)
            self._render_to_printer(printer)

            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "PDF gespeichert", f"PDF wurde gespeichert:\n{filename}")

    def _render_to_printer(self, printer: QPrinter):
        """
        Renders content to the provided QPrinter instance by generating an HTML table,
        configuring the page layout, and utilizing a QTextDocument for the rendering and
        printing process.

        :param printer: The QPrinter instance where the content will be rendered and
            printed.
        :type printer: QPrinter
        """
        from PyQt6.QtGui import QTextDocument, QPageSize
        from PyQt6.QtCore import QSizeF, QMarginsF

        # Erstelle PageLayout mit korrekten Parametern
        page_layout = QPageLayout()
        page_layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        page_layout.setOrientation(QPageLayout.Orientation.Portrait)
        page_layout.setMargins(QMarginsF(15, 15, 15, 15))
        page_layout.setUnits(QPageLayout.Unit.Millimeter)

        # Setze Layout für Printer
        printer.setPageLayout(page_layout)

        # HTML-Tabelle erstellen
        html = self._generate_html_table()

        # QTextDocument für Rendering
        document = QTextDocument()
        document.setHtml(html)

        # Setze Seitengröße für das Dokument (nutze pageLayout)
        page_rect = printer.pageLayout().paintRect(QPageLayout.Unit.Point)
        document.setPageSize(QSizeF(page_rect.width(), page_rect.height()))

        # Drucken
        document.print(printer)

    def _generate_html_table(self) -> str:
        """
        Generates an HTML table representation of transaction data based on the specified configuration,
        allowing customization of styles, grouping, and headers. The output follows a structured and
        visually enhanced format with categorized and sub-categorized data, supporting flexible column
        ordering, and includes a summary of the transaction count and date range.

        :param self: Reference to the current instance calling the method.
        :return: A string containing the generated HTML document with inline CSS styles.
        :rtype: str

        :raises AttributeError: If required attributes are not initialized or accessible in the instance.
        :raises TypeError: If the format of headers, transactions, or other dependencies is invalid.
        """
        # CSS-Style separat (ohne .format() Probleme)
        css = """
                body { font-family: Arial, sans-serif; margin: 10mm; }
                h2 { font-size: 18pt; margin-bottom: 8px; font-weight: bold; }
                p { font-size: 11pt; margin-bottom: 12px; color: #555; }
                h3 {
                    font-size: 14pt;
                    margin-top: 15px;
                    margin-bottom: 8px;
                    font-weight: bold;
                    background-color: #e0e0e0;
                    padding: 8px;
                    border-left: 4px solid #333;
                }
                h4 {
                    font-size: 12pt;
                    margin-top: 10px;
                    margin-bottom: 5px;
                    font-weight: bold;
                    padding: 5px;
                    background-color: #f0f0f0;
                    border-left: 3px solid #666;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                    font-family: Arial, sans-serif;
                    font-size: 10pt;
                    border: 2px solid #000;
                    margin-bottom: 8px;
                }
                th {
                    background-color: #333;
                    color: white;
                    padding: 8px 6px;
                    text-align: left;
                    border: 1px solid #000;
                    font-weight: bold;
                    font-size: 10pt;
                }
                td {
                    padding: 6px;
                    border: 1px solid #666;
                    font-size: 9pt;
                }
                td.right, th.right {
                    text-align: right;
                }
                tr:nth-child(even) { background-color: #f5f5f5; }
                .subcategory_total {
                    background-color: #c8e6c9 !important;
                    font-weight: bold;
                    font-size: 9pt;
                }
                .category_total {
                    background-color: #a5d6a7 !important;
                    font-weight: bold;
                    font-size: 10pt;
                    border-top: 2px solid #333;
                }
                .total {
                    background-color: #cccccc !important;
                    font-weight: bold;
                    font-size: 11pt;
                    border-top: 3px solid #333;
                }
                .debit {
                    background-color: #ffcccc !important;
                    font-weight: bold;
                    font-size: 10pt;
                }
                .credit {
                    background-color: #ccffcc !important;
                    font-weight: bold;
                    font-size: 10pt;
                }
                .right { text-align: right; font-family: monospace; }
                .category-break { page-break-after: auto; margin-bottom: 20px; }
        """

        # Daten für Header
        count = len(self.transactions)
        start = self.config.date_range.start_date.strftime("%d.%m.%Y") if self.config.date_range else ""
        end = self.config.date_range.end_date.strftime("%d.%m.%Y") if self.config.date_range else ""

        # Hole Header-Namen in visueller Reihenfolge (nach Benutzersortierung)
        table_header = self.table.horizontalHeader()
        headers = []
        visual_to_logical = []
        for visual_idx in range(self.table.columnCount()):
            logical_idx = table_header.logicalIndex(visual_idx)
            visual_to_logical.append(logical_idx)
            headers.append(self.table.horizontalHeaderItem(logical_idx).text())

        # Hole alle Zeilen mit Typen (mit originalen Header-Namen)
        original_headers = []
        for col in range(self.table.columnCount()):
            original_headers.append(self.table.horizontalHeaderItem(col).text())

        if self.config.grouping and self.tree:
            rows_data = self._flatten_tree(original_headers)
        else:
            rows_data = []
            for trans in self.transactions:
                row_data = self._create_transaction_row_data(trans, headers)
                rows_data.append(("transaction", row_data))
            if self.config.show_grand_total:
                total_row = self._create_total_row_data("Gesamtsumme", self.transactions, headers)
                rows_data.append(("total", total_row))

        # HTML zusammenbauen
        html = f"""
        <html>
        <head>
            <style>
{css}
            </style>
        </head>
        <body>
            <h2>{self.config.name}</h2>
            <p>Buchungen: {count} | Zeitraum: {start} - {end}</p>
        """

        # Verarbeite Zeilen und erstelle separate Tabellen
        current_category = None
        current_subcategory = None
        in_table = False

        for row_type, row_data in rows_data:
            if row_type == "category_header":
                # Neue Kategorie - schließe alte Tabelle
                if in_table:
                    html += "</tbody></table></div>"
                    in_table = False

                current_category = row_data[0]
                html += f'<div class="category-break"><h3>{current_category}</h3>'

            elif row_type == "subcategory_header":
                # Neue Unterkategorie - schließe alte Tabelle
                if in_table:
                    html += "</tbody></table>"
                    in_table = False

                current_subcategory = row_data[0]
                html += f'<h4>{current_subcategory}</h4>'

            elif row_type == "separator":
                # Separator - schließe Tabelle und Kategorie-Div
                if in_table:
                    html += "</tbody></table></div>"
                    in_table = False
                current_category = None
                current_subcategory = None

            else:
                # Datenzeile - öffne Tabelle falls nötig
                if not in_table:
                    html += '<table><thead><tr>'
                    for header in headers:
                        # Rechts-Ausrichtung für Datum, Betrag und Anzahl Headers
                        align_class = "right" if header in ["Datum", "Buchungsdatum", "Valuta", "Betrag", "Anzahl"] else ""
                        html += f'<th class="{align_class}">{header}</th>'
                    html += "</tr></thead><tbody>"
                    in_table = True

                # Bestimme CSS-Klasse
                row_class = ""
                if row_type == "subcategory_total":
                    row_class = "subcategory_total"
                elif row_type == "category_total":
                    row_class = "category_total"
                elif row_type == "total":
                    row_class = "total"
                elif row_type == "debit":
                    row_class = "debit"
                elif row_type == "credit":
                    row_class = "credit"

                html += f'<tr class="{row_class}">'
                # Daten in der visuellen Reihenfolge ausgeben
                reordered_row_data = [row_data[logical_idx] for logical_idx in visual_to_logical]
                for col_idx, cell_value in enumerate(reordered_row_data):
                    # Rechts-Ausrichtung für Datum, Betrag und Anzahl
                    align_class = "right" if col_idx < len(headers) and headers[col_idx] in ["Datum", "Buchungsdatum", "Valuta", "Betrag", "Anzahl"] else ""
                    html += f'<td class="{align_class}">{cell_value}</td>'
                html += "</tr>"

        # Schließe letzte Tabelle falls offen
        if in_table:
            html += "</tbody></table></div>"

        html += "</body></html>"
        return html

    def _get_file_dialog_stylesheet(self) -> str:
        """
        Returns a comprehensive stylesheet for QFileDialog in dark mode.
        
        :return: Dark mode stylesheet for file dialogs
        :rtype: str
        """
        return """
        QFileDialog {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QFileDialog QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QFileDialog QListView, QFileDialog QTreeView, QFileDialog QTableView {
            background-color: #252525;
            color: #ffffff;
            border: 1px solid #3a3a3a;
            alternate-background-color: #2a2a2a;
        }
        QFileDialog QListView::item:selected, QFileDialog QTreeView::item:selected {
            background-color: #1e88e5;
            color: #ffffff;
        }
        QFileDialog QListView::item:hover, QFileDialog QTreeView::item:hover {
            background-color: #2a2a2a;
        }
        QFileDialog QPushButton {
            background-color: #3a3a3a;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            border-radius: 3px;
            padding: 5px 15px;
            min-width: 60px;
        }
        QFileDialog QPushButton:hover {
            background-color: #4a4a4a;
            border-color: #5a5a5a;
        }
        QFileDialog QPushButton:pressed {
            background-color: #2a2a2a;
        }
        QFileDialog QLineEdit, QFileDialog QTextEdit {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            border-radius: 3px;
            padding: 4px;
        }
        QFileDialog QLineEdit:focus {
            border-color: #1e88e5;
        }
        QFileDialog QComboBox {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            border-radius: 3px;
            padding: 4px 8px;
        }
        QFileDialog QComboBox:hover {
            border-color: #5a5a5a;
        }
        QFileDialog QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QFileDialog QComboBox QAbstractItemView {
            background-color: #2a2a2a;
            color: #ffffff;
            selection-background-color: #1e88e5;
            selection-color: #ffffff;
            border: 1px solid #4a4a4a;
        }
        QFileDialog QLabel {
            color: #ffffff;
            background: transparent;
        }
        QFileDialog QHeaderView::section {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #3a3a3a;
            padding: 4px;
        }
        QFileDialog QScrollBar:vertical {
            background-color: #2a2a2a;
            width: 12px;
        }
        QFileDialog QScrollBar::handle:vertical {
            background-color: #4a4a4a;
            border-radius: 6px;
        }
        QFileDialog QScrollBar::handle:vertical:hover {
            background-color: #5a5a5a;
        }
        QFileDialog QScrollBar:horizontal {
            background-color: #2a2a2a;
            height: 12px;
        }
        QFileDialog QScrollBar::handle:horizontal {
            background-color: #4a4a4a;
            border-radius: 6px;
        }
        QFileDialog QSplitter::handle {
            background-color: #3a3a3a;
        }
        """

    def _apply_theme(self):
        """
        Applies the appropriate theme (dark or light) to the application's user interface.

        The method dynamically sets a Qt stylesheet for various widgets, such as QDialog,
        QPushButton, QTableWidget, QLabel, QHeaderView, and QScrollBar, based on the
        application's theme configuration.

        :raises ImportError: If the `settings` module from `src.config.settings` cannot be imported.
        """
        from src.config.settings import settings

        if settings.app.theme == "dark":
            stylesheet = """
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #1e88e5;
            }
            QTableWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                alternate-background-color: #202020;
                gridline-color: #3a3a3a;
            }
            QTableWidget::item {
                color: #ffffff;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #1e88e5;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 8px;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
            QScrollBar:horizontal {
                background-color: #2a2a2a;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #4a4a4a;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5a5a5a;
            }
            """
        else:
            stylesheet = """
            QDialog {
                background-color: #f0f0f0;
                color: #000000;
            }
            QLabel {
                color: #000000;
            }
            QPushButton {
                background-color: #f0f0f0;
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #aaaaaa;
            }
            QPushButton:pressed {
                background-color: #1e88e5;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                alternate-background-color: #f8f8f8;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                color: #000000;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #1e88e5;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #e8e8e8;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 8px;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #cccccc;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #999999;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #cccccc;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #999999;
            }
            """

        self.setStyleSheet(stylesheet)

    def _on_close(self):
        """
        Handles the closing operation of the current window or dialog.

        This method performs necessary cleanup operations, such as saving the
        current settings, before accepting and closing the window.

        :return: None
        """
        self._save_current_column_settings()
        self.accept()

    def _save_current_column_settings(self):
        """
        Saves the current configuration of column settings for a table, including
        column order and column widths, if a valid table is present.

        :return: None
        """
        if not self.table or self.table.columnCount() == 0:
            return

        header = self.table.horizontalHeader()

        # Speichere Spaltenreihenfolge (visual -> logical mapping)
        self.final_column_order = []
        for visual_idx in range(header.count()):
            logical_idx = header.logicalIndex(visual_idx)
            self.final_column_order.append(logical_idx)

        # Speichere Spaltenbreiten (in visueller Reihenfolge)
        self.final_column_widths = []
        for visual_idx in range(header.count()):
            width = header.sectionSize(visual_idx)
            self.final_column_widths.append(width)

    def get_column_settings(self):
        """
        Retrieves the final column order and widths.

        This method returns the final configuration of column order and their
        corresponding widths.

        :return: A tuple containing the final column order and widths.
        :rtype: tuple
        """
        return (self.final_column_order, self.final_column_widths)
