"""
===============================================================================
Project   : Hibi-BuRe
Module    : field_selection_widget.py
Created   : 13.02.26
Author    : florian
Purpose   : FieldSelectionWidget - Selection widget for report fields

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal


class FieldSelectionWidget(QWidget):
    """
    FieldSelectionWidget is a widget that allows users to select fields from a list of
    available options. The widget provides checkboxes for each field, allowing users to
    toggle their selections. A default selection can be applied, and the widget ensures
    that at least one field is always selected. Additionally, it includes an option to
    display a count of transactions.

    The widget emits a signal whenever the selection changes, and it provides methods
    to query or update the selected fields programmatically.

    :ivar selection_changed: Signal emitted when the selection of fields changes.
                              Emits the list of selected field names as `list[str]`.
    :type selection_changed: pyqtSignal

    :ivar AVAILABLE_FIELDS: Dictionary of available fields and their default selected
                            states. The key is the field name (str) and the value is
                            a boolean indicating whether the field is selected by default.
    :type AVAILABLE_FIELDS: dict
    """

    # Signal wenn Auswahl sich ändert
    selection_changed = pyqtSignal(list)  # List[str] - field names

    # Verfügbare Felder
    AVAILABLE_FIELDS = {
        "Datum": True,  # Default ausgewählt (wird dynamisch zu Buchungsdatum oder Valuta)
        "Betrag": True,
        "Kategorie": True,
        "Verwendungszweck": False,
        "Gegenkonto": False,
        "Kontonummer": False,
        "BLZ": False,
        "Konto": False,
        "Buchungsdatum": False,  # Optional: Zusätzlich zum Hauptdatum
        "Valuta": False,  # Optional: Zusätzlich zum Hauptdatum
    }

    def __init__(self, parent=None):
        """
        Initializes an instance of the class.

        This constructor is responsible for setting up the user interface and initializing
        the internal attributes for managing checkboxes. It extends functionality from
        its parent class and prepares the `checkboxes` dictionary for further operations
        to map field names to their respective QCheckBox instances.

        :param parent: The parent widget, if any, to which this instance belongs. Default is None.
        :type parent: QWidget or None
        """
        super().__init__(parent)

        self.checkboxes = {}  # field_name -> QCheckBox
        self._setup_ui()

    def _setup_ui(self):
        """
        Initializes and sets up the user interface components within the given layout.

        This method configures the main layout and various UI elements, such as headers, labels,
        checkboxes, and buttons. The layout is organized with margins and alignment adjustments,
        and interactivity is added by connecting signals to appropriate slots.

        :raise: No specific exceptions are raised directly by this method.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QHBoxLayout()

        title = QLabel("Anzuzeigende Felder")
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        # Standard Button (setzt Defaults)
        default_btn = QPushButton("Standard")
        default_btn.setMaximumWidth(70)
        default_btn.clicked.connect(self.select_defaults)
        header.addWidget(default_btn)

        layout.addLayout(header)

        # Info
        info = QLabel("Mindestens ein Feld muss ausgewählt sein")
        info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info)

        # Checkboxen für Felder
        for field_name, default_selected in self.AVAILABLE_FIELDS.items():
            cb = QCheckBox(field_name)
            cb.setChecked(default_selected)
            cb.stateChanged.connect(self._on_selection_changed)
            layout.addWidget(cb)
            self.checkboxes[field_name] = cb

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Anzahl Spalte (extra Checkbox)
        self.show_count_cb = QCheckBox("Anzahl Buchungen")
        self.show_count_cb.setChecked(False)  # Standard: aus
        self.show_count_cb.stateChanged.connect(self._on_selection_changed)
        layout.addWidget(self.show_count_cb)

        layout.addStretch()

    def get_selected_fields(self) -> List[str]:
        """
        Retrieve the names of selected fields.

        This method iterates through a dictionary of field names and their corresponding
        checkbox widgets, returning a list of field names where the associated checkboxes
        are marked as checked.

        :return: A list of field names whose checkboxes are currently checked.
        :rtype: List[str]
        """
        return [
            field_name
            for field_name, cb in self.checkboxes.items()
            if cb.isChecked()
        ]

    def set_selected_fields(self, field_names: List[str]):
        """
        Sets the selected state for the checkboxes corresponding to the provided field names.

        This method iterates through all checkboxes, and for each checkbox, it checks
        whether the associated field name exists in the provided field names list. If it
        exists, the checkbox is marked as selected; otherwise, it is deselected.

        :param field_names: A list of field names that should be selected in the checkboxes.
        :type field_names: List[str]
        :return: None
        """
        for field_name, cb in self.checkboxes.items():
            cb.setChecked(field_name in field_names)

    def select_defaults(self):
        """
        Sets the default state for all checkboxes based on their associated field's predefined
        default value. Each checkbox corresponds to a field, and this method ensures all
        checkboxes reflect their field's default state.

        :raises KeyError: If a field name in the checkboxes does not exist in AVAILABLE_FIELDS.
        """
        for field_name, cb in self.checkboxes.items():
            default = self.AVAILABLE_FIELDS[field_name]
            cb.setChecked(default)

    def get_show_count(self) -> bool:
        """
        Checks if the "show count" checkbox is selected.

        This method retrieves the state of the "show count" checkbox and determines
        whether it is checked or not. It can be used to conditionally perform actions
        based on the state of the checkbox.

        :return: Returns True if the "show count" checkbox is checked, otherwise False.
        :rtype: bool
        """
        return self.show_count_cb.isChecked()

    def set_show_count(self, show_count: bool):
        """
        Sets the checked state of the show_count checkbox.

        :param show_count: Boolean value to determine whether the checkbox
            should be checked or not.
        :type show_count: bool
        """
        self.show_count_cb.setChecked(show_count)

    def validate(self) -> bool:
        """
        Validates the selection of fields.

        This method checks if there is at least one selected field available
        within the object's current state. It returns a boolean value indicating
        whether the selected fields are non-empty.

        :return: A boolean indicating whether at least one field has been selected.
        :rtype: bool
        """
        return len(self.get_selected_fields()) > 0

    def _on_selection_changed(self):
        """
        Handles the logic when the selection is changed by validating the selection
        and emitting changes if necessary. Ensures that at least one field is always
        selected and prevents the last field from being unchecked.

        :raises TypeError: If the sender is not a QCheckBox.
        :return: None
        """
        selected = self.get_selected_fields()

        # Validierung: Mindestens 1 Feld
        if not selected:
            # Verhindere dass letztes Feld abgewählt wird
            sender = self.sender()
            if isinstance(sender, QCheckBox):
                sender.setChecked(True)
                return

        self.selection_changed.emit(selected)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = QWidget()
    layout = QVBoxLayout(widget)

    field_widget = FieldSelectionWidget()
    field_widget.selection_changed.connect(
        lambda fields: print(f"Ausgewählte Felder: {fields}")
    )
    layout.addWidget(field_widget)

    layout.addStretch()

    widget.resize(300, 400)
    widget.show()

    sys.exit(app.exec())
