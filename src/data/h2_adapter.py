"""
===============================================================================
Project   : Hibi-BuBe
Module    : h2_adapter.py
Created   : 25.02.26
Author    : florian
Purpose   : SQLAlchemy-compatible adapter for H2 database access via JDBC

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""
import re
import logging
import hashlib
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class H2ResultProxy:
    """Simuliert das SQLAlchemy Result-Objekt für Repositories (row.id, row.name)"""

    def __init__(self, cursor):
        self.cursor = cursor
        # Spaltennamen auslesen und in Kleinbuchstaben wandeln (wie SQLAlchemy)
        # WICHTIG: desc[0] kann ein Java-String sein, daher str() verwenden
        if cursor.description:
            self.columns = [str(desc[0]).lower() for desc in cursor.description]
        else:
            self.columns = []
        self.rows = cursor.fetchall()

    def __iter__(self):
        class Row:
            pass

        for row_data in self.rows:
            row_obj = Row()
            for col_name, val in zip(self.columns, row_data):
                # Konvertiere Java-Objekte zu Python-Typen
                if val is not None and hasattr(val, '__class__'):
                    class_name = str(val.__class__.__name__)
                    if 'java.lang.String' in class_name:
                        val = str(val)
                setattr(row_obj, col_name, val)
            yield row_obj

    def first(self):
        """Gibt die erste Zeile zurück oder None (SQLAlchemy-kompatibel)"""
        if self.rows:
            class Row:
                pass
            row_obj = Row()
            for col_name, val in zip(self.columns, self.rows[0]):
                # Konvertiere Java-Objekte zu Python-Typen
                if val is not None and hasattr(val, '__class__'):
                    class_name = str(val.__class__.__name__)
                    if 'java.lang.String' in class_name:
                        val = str(val)
                setattr(row_obj, col_name, val)
            return row_obj
        return None

    def fetchall(self):
        """Gibt alle Zeilen als Liste zurück"""
        return list(self)


class H2ConnectionProxy:
    """Simuliert die SQLAlchemy Connection (with engine.connect() as conn)"""

    def __init__(self, jdbc_conn):
        self.jdbc_conn = jdbc_conn
        self._cursor: Optional[Any] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cursor:
            try:
                self._cursor.close()
            except Exception:
                pass
        if self.jdbc_conn:
            try:
                self.jdbc_conn.close()
            except Exception:
                pass

    def execute(self, statement: Any, params: Dict[str, Any] = None):
        """
        Führt ein SQL-Statement aus und gibt ein H2ResultProxy zurück.

        :param statement: SQL-Statement (als String oder SQLAlchemy TextClause)
        :param params: Parameter-Dictionary (SQLAlchemy-Style mit :param)
        :return: H2ResultProxy mit den Ergebnissen
        """
        self._cursor = self.jdbc_conn.cursor()
        sql = str(statement)

        # SQLAlchemy nutzt :param, JDBC nutzt ?
        # Wir übersetzen die Parameter dynamisch
        jdbc_params = []
        if params:
            def replace_param(match):
                key = match.group(1)
                if key in params:
                    jdbc_params.append(params[key])
                    return "?"
                else:
                    logger.warning(f"Parameter :{key} nicht in params gefunden")
                    return match.group(0)  # Ursprünglichen Wert behalten

            # Ersetzt alle :variable durch ? und füllt jdbc_params
            sql = re.sub(r':([a-zA-Z0-9_]+)', replace_param, sql)

        try:
            if jdbc_params:
                self._cursor.execute(sql, jdbc_params)
            else:
                self._cursor.execute(sql)
            return H2ResultProxy(self._cursor)
        except Exception as e:
            # Logge SQL-Fehler als DEBUG (können normale User-Fehler sein)
            logger.debug(f"H2 SQL Error: {e} | SQL: {sql} | Params: {params}")
            raise


class H2EngineAdapter:
    """Simuliert die SQLAlchemy Engine für H2-Datenbanken via JDBC"""

    def __init__(self, db_path: str, jar_path: str, file_password: str = None):
        """
        Initialisiert den H2 Engine Adapter für verschlüsselte H2-Datenbanken.

        :param db_path: Pfad zur H2-Datenbankdatei (ohne .mv.db Extension)
        :param jar_path: Pfad zur h2.jar Datei (h2-1.4.199-fork.jar für alte DBs)
        :param file_password: H2-Datei-Passwort (aus Jameica Diagnose-Info)
        """
        try:
            import jaydebeapi
            import jpype
        except ImportError:
            raise ImportError(
                "jaydebeapi oder jpype ist nicht installiert. "
                "Bitte mit 'pip install JayDeBeApi JPype1' nachinstallieren.")

        self.db_path = db_path
        self.file_password = file_password  # Datei-Passwort aus Diagnose-Info
        self.jar_path = jar_path
        # Jameica nutzt AES-Verschlüsselung für die H2-Datenbank
        # AUTO_SERVER=TRUE = Server-Modus für parallelen Zugriff (wie Jameica selbst)
        self.url = f"jdbc:h2:{db_path};CIPHER=AES;AUTO_SERVER=TRUE"
        # Driver Detection: Fork nutzt org.h14199.Driver, Standard nutzt org.h2.Driver
        if "h2-1.4.199-fork.jar" in jar_path:
            self.driver = "org.h14199.Driver"
        else:
            self.driver = "org.h2.Driver"
        self.jaydebeapi = jaydebeapi
        self.jpype = jpype

        # JVM einmalig starten (wenn noch nicht gestartet)
        self._start_jvm_once()


    def _start_jvm_once(self):
        """Startet die JVM einmalig, wenn sie noch nicht läuft"""
        if not self.jpype.isJVMStarted():
            try:
                # WICHTIG: JVM MUSS mit der H2-JAR im Classpath gestartet werden
                # JPype kann nach dem Start keine neuen JARs laden
                import jpype
                jpype.startJVM(
                    jpype.getDefaultJVMPath(),
                    f"-Djava.class.path={self.jar_path}",
                    convertStrings=False
                )
                logger.debug(f"JVM erfolgreich gestartet mit H2-JAR: {self.jar_path}")
            except Exception as e:
                logger.error(f"❌ Fehler beim Starten der JVM: {e}")
                raise
        else:
            # JVM läuft bereits
            logger.warning(
                f"⚠️  JVM läuft bereits. WICHTIG: Wenn die H2-Version geändert wurde, "
                f"muss die Applikation komplett neu gestartet werden! "
                f"Erwartete JAR: {self.jar_path}"
            )

    def connect(self):
        """
        Erstellt eine neue JDBC-Verbindung zur H2-Datenbank.

        H2 mit CIPHER=AES benötigt ein spezielles Passwortformat:
        "<file_password> <user_password>"

        Parameter:
        - JDBC-Username: hibiscus
        - JDBC-Passwort: <file_pw> <user_pw> (beide identisch)
        - CIPHER: AES
        - Driver: org.h2.Driver (bzw. org.h14199.Driver für Fork)

        :return: H2ConnectionProxy-Objekt (Context Manager)
        """
        try:
            if not self.file_password:
                error_msg = (
                    "H2-Verbindung fehlgeschlagen: Kein Datei-Passwort vorhanden.\n\n"
                    "Das H2-Datei-Passwort kann über die Jameica-GUI abgerufen werden:\n"
                    "Hibiscus → Über Hibiscus → Datenbank-Infos\n\n"
                    "Kopiere den Wert von 'JDBC-Passwort' (z.B. '/0YSASo9da02nqzHJ3Gv0GqKkiY= /0YSASo9da02nqzHJ3Gv0GqKkiY=')\n"
                    "und gib nur den ersten Teil (vor dem Leerzeichen) im Password-Dialog ein."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            logger.debug(f"Verbinde zu H2-Datenbank (User: hibiscus, PW-Länge: {len(self.file_password)})")
            logger.debug(f"  Driver: {self.driver}")
            logger.debug(f"  JAR: {self.jar_path}")

            combined_password = f"{self.file_password} {self.file_password}"

            # WICHTIG: H2-Datenbank kann NICHT parallel zu Jameica geöffnet werden
            # Jameica muss vollständig geschlossen sein!
            jdbc_conn = self.jaydebeapi.connect(
                self.driver,
                self.url,
                {"user": "hibiscus", "password": combined_password}
            )
            logger.debug("H2-Verbindung erfolgreich")
            return H2ConnectionProxy(jdbc_conn)

        except Exception as e:
            error_msg = (
                f"H2-Verbindung fehlgeschlagen: {e}\n\n"
                f"⚠️  WICHTIG: Bitte schließen Sie Jameica/Hibiscus vollständig!\n\n"
                f"H2-Datenbanken können NICHT parallel geöffnet werden.\n"
                f"Paralleler Zugriff ist technisch nicht möglich, auch nicht im Read-Only-Modus.\n\n"
                f"Weitere mögliche Ursachen:\n"
                f"1. Falsches H2-Datei-Passwort\n"
                f"   → Abrufen: Hibiscus → Über → Datenbank-Infos\n"
                f"2. Inkompatible H2-Version\n"
                f"   → Für alte DBs: h2-1.4.199-fork.jar verwenden"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def dispose(self):
        """
        Schließt alle Verbindungen und fährt die JVM herunter (SQLAlchemy-kompatibel).

        WICHTIG: JVM-Shutdown ist problematisch in JPype1, da die JVM nicht
        neu gestartet werden kann. Daher wird hier NUR geloggt.
        """
        logger.info("H2 Engine dispose aufgerufen (JVM bleibt aktiv)")
        # NICHT: self.jpype.shutdownJVM()
        # Grund: JVM kann nicht neu gestartet werden in demselben Prozess!