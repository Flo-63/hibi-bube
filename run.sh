#!/bin/bash
# Startet die Hibi-BuBe App mit PyQt6

VENV_PATH="$HOME/.venvs/Hibi-BuBe/lib/python3.12/site-packages"
export PYTHONPATH="$VENV_PATH"

echo "=== Hibi-BuBe Report-App ==="
echo "Python Path: $PYTHONPATH"
echo ""

python3 main.py
