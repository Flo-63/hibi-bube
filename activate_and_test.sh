#!/bin/bash
# Aktiviert die venv und testet die Anwendung

echo "=== Aktiviere venv ==="
source ~/.venvs/Hibi-BuBe/bin/activate

echo ""
echo "=== Python-Umgebung ==="
which python
python --version
echo "VIRTUAL_ENV: $VIRTUAL_ENV"

echo ""
echo "=== Installierte Packages prüfen ==="
python -m pip list | grep -E "(sqlalchemy|pandas|pymysql|openpyxl|dotenv|customtkinter)" || echo "Keine relevanten Packages gefunden"

echo ""
echo "=== Fehlende Packages installieren ==="
python -m pip install -r requirements.txt

echo ""
echo "=== Test: main.py starten ==="
python main.py
