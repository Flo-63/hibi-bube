#!/bin/bash

# ===============================================================================
# Hibi-BuBe Auto-Builder
# Automatisiert den Prozess: PyInstaller -> linuxdeploy -> AppImage
# ===============================================================================

# Fehler abfangen
set -e

# 1. Konfiguration
APP_NAME="Hibi-BuBe"
VENV_PATH="$HOME/.venvs/hibi-bube"
PYTHON_BIN="$VENV_PATH/bin/python3"
LINUXDEPLOY="./build/linuxdeploy"
ASSETS_DIR="./assets"
ICON_NAME="hibi-bube"
ICON_FILE="$ASSETS_DIR/Hibi-BuBe_512x512.png"
DESKTOP_FILE="$ASSETS_DIR/Hibi-BuBe.desktop"

echo "Starte Build-Prozess für $APP_NAME..."

# 2. Umgebung prüfen
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Fehler: Virtual Environment nicht gefunden unter $VENV_PATH"
    exit 1
fi

# 3. Clean-up
echo "Bereinige alte Build-Dateien..."
rm -rf build/ dist/ AppDir/ "${APP_NAME}-x86_64.AppImage"
mkdir -p build

# 4. Werkzeuge prüfen/laden
if [ ! -f "$LINUXDEPLOY" ]; then
    echo "Lade linuxdeploy herunter..."
    wget -O "$LINUXDEPLOY" https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x "$LINUXDEPLOY"
fi

# 5. PyInstaller Build (Der "Deep Scan" mit PyQt6)
echo "Starte PyInstaller..."
$PYTHON_BIN -m PyInstaller --noconfirm --onedir --windowed \
    --name "$APP_NAME" \
    --paths "$VENV_PATH/lib/python3.12/site-packages" \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtGui \
    --hidden-import PyQt6.QtWidgets \
    --hidden-import PyQt6.QtPrintSupport \
    --collect-submodules PyQt6.QtCore \
    --collect-submodules PyQt6.QtGui \
    --collect-submodules PyQt6.QtWidgets \
    --collect-submodules PyQt6.QtPrintSupport \
    --exclude-module PyQt6.QtWebEngine \
    --exclude-module PyQt6.QtWebEngineCore \
    --exclude-module PyQt6.QtMultimedia \
    --exclude-module PyQt6.QtQml \
    --exclude-module PyQt6.QtQuick \
    --exclude-module PyQt6.Qt3D \
    main.py
    

#5b Ungenutzte Qt Komponenten weg
echo "🧹 Stripping unneeded Qt components..."

# Gehe in den dist-Ordner der App
cd "dist/Hibi-BuBe"

# Entferne QML und Quick (die größten Brocken)
find . -name "*Qt6Qml*" -delete
find . -name "*Qt6Quick*" -delete
find . -name "*Qt6VirtualKeyboard*" -delete

# Entferne Multimedia und WebEngine
find . -name "*Qt6WebEngine*" -delete
find . -name "*Qt6Multimedia*" -delete
find . -name "*Qt63D*" -delete

# Entferne die riesigen .pyi Stub-Dateien (nur für IDEs wichtig)
find . -name "*.pyi" -delete

# Entferne ungenutzte Übersetzungen (spart ebenfalls Platz)
if [ -d "PyQt6/Qt6/translations" ]; then
    rm -rf "PyQt6/Qt6/translations"
fi

cd ../..
# 6. AppDir strukturieren
echo "🏗️  Erstelle AppDir..."
mkdir -p AppDir/usr/bin
cp -r dist/$APP_NAME/* AppDir/usr/bin/

# 7. AppImage-Packaging
echo "💎 Schnüre AppImage..."
export PATH=$(pwd)/build:$PATH

$LINUXDEPLOY --appdir AppDir \
    --deploy-deps-only AppDir/usr/bin/$APP_NAME \
    -i "$ICON_FILE" \
    --icon-filename "$ICON_NAME" \
    -d "$DESKTOP_FILE" \
    --output appimage

echo "============================================================"
echo "✅ SUCCESS: $APP_NAME-x86_64.AppImage wurde erstellt!"
echo "📍 Speicherort: $(pwd)/$APP_NAME-x86_64.AppImage"
echo "============================================================"