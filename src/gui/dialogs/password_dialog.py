"""
===============================================================================
Project   : Hibi-BuBe
Module    : password_dialog.py
Created   : 28.02.26
Author    : florian
Purpose   : Dialog to prompt for Jameica Master-Password and H2 file password

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class PasswordDialog(QDialog):
    """
    Dialog to prompt user for H2 database file password.

    This dialog is shown when the application needs the H2 database password.
    The password can be retrieved from Jameica diagnostic info.

    :ivar file_password: The entered H2 database file password
    :type file_password: str
    """

    def __init__(self, parent=None):
        """
        Initialize the password dialog.

        :param parent: Parent widget (optional)
        :type parent: QWidget
        """
        super().__init__(parent)

        self.file_password = None

        self.setWindowTitle("Jameica/H2 Datenbank-Passwort")
        self.setModal(True)
        self.setMinimumWidth(600)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog user interface."""
        layout = QVBoxLayout()

        # Informationstext
        info_label = QLabel(
            "<b>H2-Datenbank-Verschlüsselung</b><br><br>"
            "Die Jameica/Hibiscus H2-Datenbank ist verschlüsselt. "
            "Bitte geben Sie das H2-Datei-Passwort ein:"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # WICHTIGER Hinweis
        warning_label = QLabel(
            "<b>⚠️ WICHTIG:</b> Bitte <b>schließen Sie Jameica/Hibiscus</b> vollständig,<br>"
            "bevor Sie fortfahren. H2-Datenbanken können nicht parallel geöffnet werden."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #d32f2f; background: #ffebee; padding: 10px; border-radius: 4px; border: 2px solid #ef5350; margin: 10px 0;")
        layout.addWidget(warning_label)

        # --- Passwort-Anleitung ---
        file_group = QGroupBox("H2-Datei-Passwort aus Jameica abrufen")
        file_layout = QVBoxLayout()

        file_info = QLabel(
            "<b>So erhalten Sie das Passwort aus Jameica/Hibiscus:</b><br><br>"
            "<b>1.</b> Öffnen Sie Jameica/Hibiscus<br>"
            "<b>2.</b> Menü: <b>Plugins → Hibiscus → Über Hibiscus</b><br>"
            "<b>3.</b> Button: <b>\"Diagnose-Informationen\"</b><br>"
            "<b>4.</b> Suchen Sie: <code>JDBC-Passwort: xxx xxx</code><br>"
            "<b>5.</b> Kopieren Sie <b>nur den ersten Teil</b> (vor dem Leerzeichen)<br><br>"
            "<i>📋 Beispiel:<br>"
            "Angezeigt wird: <code>JDBC-Passwort: /0YSzSo9dao2nqzHJ3Gv0GqKkiY= /0YSzSo9dao2nqzHJ3Gv0GqKkiY=</code><br>"
            "Kopieren Sie: <code>/0YSzSo9dao2nqzHJ3Gv0GqKkiY=</code></i>"
        )
        file_info.setWordWrap(True)
        file_info.setStyleSheet("color: #333; font-size: 11px; background: #f5f5f5; padding: 12px; border-radius: 4px; border: 1px solid #ddd;")
        file_layout.addWidget(file_info)

        # Datei-Passwort Eingabefeld
        file_input_layout = QHBoxLayout()
        file_input_layout.addWidget(QLabel("H2-Datei-Passwort:"))
        self.file_password_input = QLineEdit()
        self.file_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.file_password_input.setPlaceholderText("Passwort aus Jameica Diagnose-Info")
        file_input_layout.addWidget(self.file_password_input)
        file_layout.addLayout(file_input_layout)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _on_accept(self):
        """Handle OK button click - validate and store password."""
        self.file_password = self.file_password_input.text().strip()

        if not self.file_password:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Kein Passwort eingegeben",
                "Bitte geben Sie das H2-Datei-Passwort ein."
            )
            return

        self.accept()

    def get_passwords(self):
        """
        Get the entered password.

        :return: Tuple of (None, file_password) for compatibility
        :rtype: tuple[None, str]
        """
        return None, self.file_password
