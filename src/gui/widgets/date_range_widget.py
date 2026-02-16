"""
===============================================================================
Project   :
Module    : date_range_widget.py
Created   : 13.02.26
Author    : florian
Purpose   : Date Range Widget - Selection widget for date ranges
Options:
    - Free selection (start/end date)
    - Month (this/last year)
    - Year (current year to today, last year)
    - Quarter (current quarter to today, previous quarter)

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDateEdit, QFrame, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

from src.data.models.domain_models import DateRange, DateFieldType


class DateRangeWidget(QWidget):
    """
    Widget for selecting and managing date ranges.

    The DateRangeWidget class is a graphical component that provides functionality to
    select and manage various types of date ranges. Users can choose predefined date
    ranges (such as the current month, last year, etc.) or manually input custom date
    ranges. The widget emits a signal when the selected date range changes.

    :ivar range_changed: Signal emitted when the date range changes.
    :type range_changed: pyqtSignal

    :ivar RANGE_TYPES: Dictionary defining predefined range types and their internal
        representations.
    :type RANGE_TYPES: dict

    :ivar current_range_type: The currently selected range type.
    :type current_range_type: str
    """

    # Signal wenn Zeitraum sich ändert
    range_changed = pyqtSignal(object)  # DateRange

    # Zeitraum-Typen
    RANGE_TYPES = {
        "Freie Auswahl": "custom",

        "Dieser Monat": "month_current",
        "Vormonat": "month_previous",
        "Monat im letzten Jahr": "month_last_year",

        "Aktuelles Jahr (bis heute)": "year_current_to_date",
        "Letztes Jahr": "year_previous",

        "Quartal (bis heute)": "quarter_current_to_date",
        "Vorheriges Quartal": "quarter_previous",
        "Quartal im Vorjahr": "quarter_last_year",
    }

    def __init__(self, parent=None):
        """
        Initializes the instance and sets up the user interface components.

        The constructor sets the default range type to `custom` and initializes
        the UI components. It also preloads the range type combo box with the
        default value "Aktuelles Jahr (bis heute)".

        :param parent: The parent widget of this instance. Defaults to None. If not
                       provided, the instance will have no parent.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)

        self.current_range_type = "custom"
        self._setup_ui()

        # Initialisiere mit "Aktuelles Jahr bis heute"
        self.range_type_combo.setCurrentText("Aktuelles Jahr (bis heute)")

    def _setup_ui(self):
        """
        Sets up the user interface for selecting a date range. The UI includes various
        elements such as a range type dropdown, date selection widgets, and a label
        for displaying computed range information.

        :raises ValueError: Raised if invalid date values are entered during user
            interaction with date fields.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        title = QLabel("Zeitraum")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        # Zeitraum-Typ Auswahl
        self.range_type_combo = QComboBox()
        self.range_type_combo.addItems(self.RANGE_TYPES.keys())
        self.range_type_combo.currentTextChanged.connect(self._on_range_type_changed)
        layout.addWidget(self.range_type_combo)

        # Container für Datum-Auswahl (nur bei "Freie Auswahl")
        self.date_container = QWidget()
        date_layout = QVBoxLayout(self.date_container)
        date_layout.setContentsMargins(0, 5, 0, 0)

        # Von-Datum
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("Von:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addYears(-1))
        self.start_date_edit.dateChanged.connect(self._on_date_changed)
        from_layout.addWidget(self.start_date_edit)
        date_layout.addLayout(from_layout)

        # Bis-Datum
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("Bis:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.dateChanged.connect(self._on_date_changed)
        to_layout.addWidget(self.end_date_edit)
        date_layout.addLayout(to_layout)

        layout.addWidget(self.date_container)

        # Info-Label (zeigt berechneten Zeitraum)
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: gray; font-size: 10px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Datumsfeld-Auswahl (Buchungsdatum vs. Valuta)
        date_field_label = QLabel("Datumsfeld:")
        date_field_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(date_field_label)

        date_field_layout = QVBoxLayout()
        date_field_layout.setContentsMargins(10, 0, 0, 0)

        self.date_field_group = QButtonGroup(self)
        self.booking_date_radio = QRadioButton("Buchungsdatum")
        self.value_date_radio = QRadioButton("Valuta (Wertstellung)")

        self.date_field_group.addButton(self.booking_date_radio, 0)
        self.date_field_group.addButton(self.value_date_radio, 1)

        # Default: Buchungsdatum (wie in Hibiscus)
        self.booking_date_radio.setChecked(True)

        # Signal wenn sich die Auswahl ändert
        self.booking_date_radio.toggled.connect(self._on_date_field_changed)

        date_field_layout.addWidget(self.booking_date_radio)
        date_field_layout.addWidget(self.value_date_radio)
        layout.addLayout(date_field_layout)

    def _on_range_type_changed(self, range_type_name: str):
        """
        Handles changes in the selected range type and updates UI elements based on the selection.

        When the range type changes, this method adjusts the state of the corresponding user
        interface elements such as the date selection container and recalculates the date range
        if the range type is not "custom". For the "custom" range type, it relies on user-entered
        dates.

        :param range_type_name: The name of the selected range type. Must correspond to one of
                                the predefined range types in `RANGE_TYPES`.
        :return: None
        """
        range_type = self.RANGE_TYPES[range_type_name]
        self.current_range_type = range_type

        # Zeige/Verstecke Datum-Auswahl
        is_custom = range_type == "custom"
        self.date_container.setVisible(is_custom)

        # Berechne Zeitraum
        if not is_custom:
            date_range = self._calculate_range(range_type)
            self._update_info_label(date_range)
            self.range_changed.emit(date_range)
        else:
            # Bei Freier Auswahl: Nutze eingegebene Daten
            self._on_date_changed()

    def _on_date_changed(self):
        """
        Handles the logic executed when the date is changed.

        This method is called when the date-related attributes are updated, specifically
        when the current range type is set to "custom." It retrieves the date range by
        invoking the `get_date_range` method, updates the associated label with the
        obtained date range, and emits the `range_changed` signal with the updated range.

        :return: None
        """
        if self.current_range_type == "custom":
            date_range = self.get_date_range()
            self._update_info_label(date_range)
            self.range_changed.emit(date_range)

    def _on_date_field_changed(self):
        """
        Handles changes to the date field selection (Buchungsdatum vs. Valuta).

        Emits the range_changed signal with the updated DateRange including the selected date field.

        :return: None
        """
        date_range = self.get_date_range()
        self.range_changed.emit(date_range)

    def _calculate_range(self, range_type: str) -> DateRange:
        """
        Calculates and returns a date range based on the provided range type. The date range
        can correspond to the current or previous month, year, quarter, or their counterparts
        from the previous year. If no specific range type is provided, it defaults to returning
        the entire date range of the previous year.

        :param range_type: The type of date range to calculate. The valid range types are:
            - "month_current": The first day of the current month to the current date.
            - "month_previous": The full range of the previous month.
            - "month_last_year": The equivalent month of the previous year.
            - "year_current_to_date": The first day of the current year to the current date.
            - "year_previous": The entire date range of the previous year.
            - "quarter_current_to_date": The first day of the current quarter to the current date.
            - "quarter_previous": The entire date range of the previous quarter.
            - "quarter_last_year": The matching quarter of the previous year.
            Defaults to the range for the entire previous year if an invalid or no range type
            is provided.
        :type range_type: str

        :return: An object representing the calculated date range with `start` and `end`
            attributes, indicating the start and end dates of the range respectively.
        :rtype: DateRange
        """
        today = date.today()

        # === MONAT ===
        if range_type == "month_current":
            # Dieser Monat (1. bis heute)
            start = today.replace(day=1)
            end = today

        elif range_type == "month_previous":
            # Vormonat (kompletter Monat)
            first_of_month = today.replace(day=1)
            last_month_end = first_of_month - timedelta(days=1)
            start = last_month_end.replace(day=1)
            end = last_month_end

        elif range_type == "month_last_year":
            # Gleicher Monat letztes Jahr
            last_year = today - relativedelta(years=1)
            start = last_year.replace(day=1)
            # Letzter Tag des Monats
            next_month = start + relativedelta(months=1)
            end = next_month - timedelta(days=1)

        # === JAHR ===
        elif range_type == "year_current_to_date":
            # Aktuelles Jahr bis heute
            start = today.replace(month=1, day=1)
            end = today

        elif range_type == "year_previous":
            # Letztes Jahr (komplett)
            start = date(today.year - 1, 1, 1)
            end = date(today.year - 1, 12, 31)

        # === QUARTAL ===
        elif range_type == "quarter_current_to_date":
            # Aktuelles Quartal bis heute
            quarter = (today.month - 1) // 3
            start = date(today.year, quarter * 3 + 1, 1)
            end = today

        elif range_type == "quarter_previous":
            # Vorheriges Quartal (komplett)
            current_quarter = (today.month - 1) // 3
            if current_quarter == 0:
                # Q4 letztes Jahr
                start = date(today.year - 1, 10, 1)
                end = date(today.year - 1, 12, 31)
            else:
                prev_quarter = current_quarter - 1
                start = date(today.year, prev_quarter * 3 + 1, 1)
                end = date(today.year, current_quarter * 3, 1) - timedelta(days=1)

        elif range_type == "quarter_last_year":
            # Gleiches Quartal im Vorjahr
            current_quarter = (today.month - 1) // 3
            start = date(today.year - 1, current_quarter * 3 + 1, 1)
            if current_quarter == 3:
                end = date(today.year - 1, 12, 31)
            else:
                end = date(today.year - 1, (current_quarter + 1) * 3, 1) - timedelta(days=1)

        else:
            # Fallback: Letztes Jahr
            start = date(today.year - 1, 1, 1)
            end = date(today.year - 1, 12, 31)

        # Füge ausgewähltes Datumsfeld hinzu
        date_field = DateFieldType.BOOKING_DATE if self.booking_date_radio.isChecked() else DateFieldType.VALUE_DATE
        return DateRange(start, end, date_field)

    def get_date_range(self) -> DateRange:
        """
        Retrieves the date range based on the current range type.

        If the current range type is set to "custom", the method extracts the start
        and end dates from the corresponding date editor widgets and returns them as
        a `DateRange` object.

        For other range types, the method calculates the date range dynamically through
        an internal helper method.

        :raises AttributeError: If the `current_range_type` is not properly assigned or
            the required date editors are not initialized.
        :raises TypeError: If the calculated date range is not of the expected type.
        :returns: A `DateRange` object corresponding to the selected range type.
        :rtype: DateRange
        """
        # Ermittle ausgewähltes Datumsfeld
        date_field = DateFieldType.BOOKING_DATE if self.booking_date_radio.isChecked() else DateFieldType.VALUE_DATE

        if self.current_range_type == "custom":
            # Von QDateEdit
            start = self.start_date_edit.date().toPyDate()
            end = self.end_date_edit.date().toPyDate()
            return DateRange(start, end, date_field)
        else:
            # Berechnet
            return self._calculate_range(self.current_range_type)

    def set_date_range(self, date_range: DateRange):
        """
        Sets the date range values in the respective input fields and updates the
        range type combo box to "Freie Auswahl".

        :param date_range: The date range to set, which includes a start date and
            an end date.
        :type date_range: DateRange
        """
        # Setze auf "Freie Auswahl"
        self.range_type_combo.setCurrentText("Freie Auswahl")

        # Setze Daten
        self.start_date_edit.setDate(QDate(
            date_range.start_date.year,
            date_range.start_date.month,
            date_range.start_date.day
        ))
        self.end_date_edit.setDate(QDate(
            date_range.end_date.year,
            date_range.end_date.month,
            date_range.end_date.day
        ))

    def _update_info_label(self, date_range: DateRange):
        """
        Updates the information label with the formatted date range and the number of
        days within the range.

        :param date_range: The date range object containing start and end dates
                           to be displayed.
        :type date_range: DateRange
        """
        days = (date_range.end_date - date_range.start_date).days + 1
        self.info_label.setText(
            f"{date_range.start_date.strftime('%d.%m.%Y')} - "
            f"{date_range.end_date.strftime('%d.%m.%Y')} "
            f"({days} Tage)"
        )


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Erstelle Widget
    widget = QWidget()
    layout = QVBoxLayout(widget)

    date_widget = DateRangeWidget()
    date_widget.range_changed.connect(
        lambda dr: print(f"Zeitraum geändert: {dr}")
    )
    layout.addWidget(date_widget)

    layout.addStretch()

    widget.resize(400, 300)
    widget.show()

    sys.exit(app.exec())
