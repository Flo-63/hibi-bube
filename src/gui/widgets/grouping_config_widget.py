"""
===============================================================================
Project   : Hibi-BuBe
Module    : grouping_config_widget.py
Created   : 13.02.26
Author    : florian
Purpose   : GroupingConfigWidget - Configuration widget for grouping and sorting

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QComboBox, QGroupBox, QRadioButton,
    QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal


class GroupingConfigWidget(QWidget):
    """
    Widget for configuring grouping and sorting options.

    Provides a graphical user interface to configure grouping levels, sorting
    fields, sorting order, and display options for aggregated values such as
    subtotals, grand totals, record counts, and debit/credit sums. Signals are
    emitted when configuration changes are made.

    :ivar config_changed: Signal emitted when the configuration is changed. The
        signal passes a dictionary representing the current configuration.
    :type config_changed: pyqtSignal

    :ivar GROUPING_LEVELS: List of available grouping levels that can be selected.
    :type GROUPING_LEVELS: list[str]

    :ivar SORT_FIELDS: List of available fields for sorting.
    :type SORT_FIELDS: list[str]

    :ivar grouping_checkboxes: Dictionary mapping grouping levels to their
        corresponding checkboxes.
    :type grouping_checkboxes: dict[str, QCheckBox]

    :ivar sort_field_combo: ComboBox for selecting the sorting field.
    :type sort_field_combo: QComboBox

    :ivar sort_order_group: Button group for sorting order radio buttons.
    :type sort_order_group: QButtonGroup

    :ivar sort_asc_radio: Radio button for selecting ascending sort order.
    :type sort_asc_radio: QRadioButton

    :ivar sort_desc_radio: Radio button for selecting descending sort order.
    :type sort_desc_radio: QRadioButton

    :ivar show_subtotals_cb: Checkbox for enabling or disabling the display of
        subtotals.
    :type show_subtotals_cb: QCheckBox

    :ivar show_grand_total_cb: Checkbox for enabling or disabling the display of
        grand totals.
    :type show_grand_total_cb: QCheckBox

    :ivar show_count_cb: Checkbox for enabling or disabling the display of the
        number of records.
    :type show_count_cb: QCheckBox

    :ivar show_debit_credit_cb: Checkbox for enabling or disabling the display of
        debit and credit sums.
    :type show_debit_credit_cb: QCheckBox
    """

    # Signal wenn Konfiguration sich ändert
    config_changed = pyqtSignal(dict)  # Dict mit Gruppierungs-Config

    # Gruppierungs-Ebenen
    GROUPING_LEVELS = [
        "Kategorie",
        "Subkategorie",
        "Gruppe"
    ]

    # Sortier-Felder
    SORT_FIELDS = [
        "Datum",
        "Betrag",
        "Kategorie"
    ]

    def __init__(self, parent=None):
        """
        Initializes an instance of the class.

        :param parent: The parent widget for this instance. Defaults to None.
        """
        super().__init__(parent)

        self._setup_ui()

    def _setup_ui(self):
        """
        Sets up the user interface components for grouping, sorting, and display
        options within the application. This method defines the layout, widgets,
        and their connections to corresponding signals for updating configuration
        parameters.

        Grouping:
            - Allows users to select grouping levels using checkboxes.

        Sorting:
            - Provides a dropdown menu for selecting the sorting field and
              radio buttons for sorting order (ascending or descending).

        Options:
            - Includes checkboxes to enable or disable display options, such as
              subtotals, grand total, booking count, and debit/credit summary.

        The method ensures all signals are connected after the widgets are created
        to avoid runtime errors and initializes default settings for grouping by
        category and subcategory.

        :return: None
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # === GRUPPIERUNG ===
        grouping_group = QGroupBox("Gruppierung")
        grouping_layout = QVBoxLayout(grouping_group)

        # Checkboxen für Gruppierungs-Ebenen
        self.grouping_checkboxes = {}
        for level in self.GROUPING_LEVELS:
            cb = QCheckBox(level)
            # WICHTIG: Signal wird NACH Erstellung aller Widgets verbunden
            grouping_layout.addWidget(cb)
            self.grouping_checkboxes[level] = cb

        layout.addWidget(grouping_group)

        # === SORTIERUNG ===
        sort_group = QGroupBox("Sortierung")
        sort_layout = QVBoxLayout(sort_group)

        # Sortier-Feld
        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel("Sortieren nach:"))
        self.sort_field_combo = QComboBox()
        self.sort_field_combo.addItems(self.SORT_FIELDS)
        # Signal wird später verbunden
        field_layout.addWidget(self.sort_field_combo)
        sort_layout.addLayout(field_layout)

        # Sortier-Reihenfolge (RadioButtons)
        self.sort_order_group = QButtonGroup(self)

        self.sort_asc_radio = QRadioButton("Aufsteigend")
        self.sort_asc_radio.setChecked(True)
        # Signal wird später verbunden
        self.sort_order_group.addButton(self.sort_asc_radio)
        sort_layout.addWidget(self.sort_asc_radio)

        self.sort_desc_radio = QRadioButton("Absteigend")
        # Signal wird später verbunden
        self.sort_order_group.addButton(self.sort_desc_radio)
        sort_layout.addWidget(self.sort_desc_radio)

        layout.addWidget(sort_group)

        # === OPTIONEN ===
        options_group = QGroupBox("Anzeige-Optionen")
        options_layout = QVBoxLayout(options_group)

        self.show_subtotals_cb = QCheckBox("Zwischensummen anzeigen")
        self.show_subtotals_cb.setChecked(True)
        # Signal wird später verbunden
        options_layout.addWidget(self.show_subtotals_cb)

        self.show_grand_total_cb = QCheckBox("Gesamtsumme anzeigen")
        self.show_grand_total_cb.setChecked(True)
        # Signal wird später verbunden
        options_layout.addWidget(self.show_grand_total_cb)

        self.show_count_cb = QCheckBox("Anzahl Buchungen anzeigen")
        self.show_count_cb.setChecked(True)
        # Signal wird später verbunden
        options_layout.addWidget(self.show_count_cb)

        self.show_debit_credit_cb = QCheckBox("Soll/Haben-Summen anzeigen")
        self.show_debit_credit_cb.setChecked(False)
        # Signal wird später verbunden
        options_layout.addWidget(self.show_debit_credit_cb)

        layout.addWidget(options_group)

        layout.addStretch()

        # === SIGNALE VERBINDEN (erst NACH Erstellung ALLER Widgets!) ===
        # Gruppierung
        for cb in self.grouping_checkboxes.values():
            cb.stateChanged.connect(self._on_config_changed)

        # Default: Kategorie + Subkategorie
        self.grouping_checkboxes["Kategorie"].setChecked(True)
        self.grouping_checkboxes["Subkategorie"].setChecked(True)

        # Sortierung
        self.sort_field_combo.currentTextChanged.connect(self._on_config_changed)
        self.sort_asc_radio.toggled.connect(self._on_config_changed)
        self.sort_desc_radio.toggled.connect(self._on_config_changed)

        # Optionen
        self.show_subtotals_cb.stateChanged.connect(self._on_config_changed)
        self.show_grand_total_cb.stateChanged.connect(self._on_config_changed)
        self.show_count_cb.stateChanged.connect(self._on_config_changed)
        self.show_debit_credit_cb.stateChanged.connect(self._on_config_changed)

    def get_config(self) -> Dict:
        """
        Generates and returns a configuration dictionary based on user-selected
        options, such as grouping levels, sorting preferences, and output display
        settings.

        :return: A dictionary with user-selected configuration options including
                 grouping levels, sorting field and order, and display settings for
                 subtotals, grand total, count, and debit/credit columns.
        :rtype: Dict
        """
        # Gruppierungs-Ebenen
        grouping = [
            level for level, cb in self.grouping_checkboxes.items()
            if cb.isChecked()
        ]

        # Sortierung
        sort_field = self.sort_field_combo.currentText()
        sort_order = "asc" if self.sort_asc_radio.isChecked() else "desc"

        # Optionen
        show_subtotals = self.show_subtotals_cb.isChecked()
        show_grand_total = self.show_grand_total_cb.isChecked()
        show_count = self.show_count_cb.isChecked()
        show_debit_credit = self.show_debit_credit_cb.isChecked()

        return {
            "grouping": grouping,
            "sort_field": sort_field,
            "sort_order": sort_order,
            "show_subtotals": show_subtotals,
            "show_grand_total": show_grand_total,
            "show_count": show_count,
            "show_debit_credit": show_debit_credit
        }

    def set_config(self, config: Dict):
        """
        Configures the user interface elements based on the provided configuration dictionary. This method
        updates the state of grouping checkboxes, sort field and order, as well as various display options
        according to the values in the configuration.

        :param config: Configuration dictionary containing settings to apply. Expected keys include:
                       - grouping (List[str]): A list of grouping levels to be checked.
                       - sort_field (str): The field to sort by. It should match one of the predefined sort fields.
                       - sort_order (str): Order of sorting, either "asc" (ascending) or "desc" (descending).
                       - show_subtotals (bool): Whether to show subtotals in the user interface.
                       - show_grand_total (bool): Whether to show the grand total in the user interface.
                       - show_count (bool): Whether to show the count of items.
                       - show_debit_credit (bool): Whether to show debit and credit information.

        :return: None
        """
        # Gruppierung
        grouping = config.get("grouping", [])
        for level, cb in self.grouping_checkboxes.items():
            cb.setChecked(level in grouping)

        # Sortierung
        sort_field = config.get("sort_field", "Datum")
        if sort_field in self.SORT_FIELDS:
            self.sort_field_combo.setCurrentText(sort_field)

        sort_order = config.get("sort_order", "asc")
        if sort_order == "asc":
            self.sort_asc_radio.setChecked(True)
        else:
            self.sort_desc_radio.setChecked(True)

        # Optionen
        self.show_subtotals_cb.setChecked(config.get("show_subtotals", True))
        self.show_grand_total_cb.setChecked(config.get("show_grand_total", True))
        self.show_count_cb.setChecked(config.get("show_count", True))
        self.show_debit_credit_cb.setChecked(config.get("show_debit_credit", False))

    def validate(self) -> bool:
        """
        Validates the logical entity to ensure any specified rules or constraints are met.

        This method is used to verify the validity of an entity without performing any
        actual changes to its state. In the context of a flat list structure, no
        specific validation logic is necessary, allowing this method to always return
        `True`.

        :return: The result of the validation process, which is always `True` for this
            implementation.
        :rtype: bool
        """
        # Keine spezielle Validierung nötig
        # (Gruppierung kann leer sein für flache Liste)
        return True

    def _on_config_changed(self):
        """
        Handles configuration changes by emitting a signal with the updated configuration.

        This method retrieves the current configuration and triggers the `config_changed`
        signal, passing the updated configuration as an argument.

        :return: None
        """
        config = self.get_config()
        self.config_changed.emit(config)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = QWidget()
    layout = QVBoxLayout(widget)

    grouping_widget = GroupingConfigWidget()
    grouping_widget.config_changed.connect(
        lambda cfg: print(f"Config: {cfg}")
    )
    layout.addWidget(grouping_widget)

    widget.resize(350, 500)
    widget.show()

    sys.exit(app.exec())
