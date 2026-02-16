#!/bin/bash
# make_release.sh - Erstellt das fertige Hibi-BuBe Jameica-Plugin Paket

NAME="Hibi-BuBe"
DIR_NAME="hibi-bube"
RELEASE_DIR="releases"
VERSION=$(python3 -c "from src.main_window import MainWindow; print('0.8')") # Oder statisch setzen

echo "Starte Release-Prozess für $NAME v$VERSION..."

# 1. AppImage bauen (ruft dein existierendes Script auf)
echo "📦 Baue AppImage..."
chmod +x build.sh
./build.sh

# 2. Release-Struktur vorbereiten
echo "Bereite Jameica-Plugin Struktur vor..."
rm -rf "$RELEASE_DIR/$DIR_NAME"
mkdir -p "$RELEASE_DIR/$DIR_NAME/bin"

# 3. Dateien kopieren
# Wir nehmen das frisch gebaute AppImage (Passe den Namen ggf. an dein build.sh an)
APPIMAGE_SRC="Hibi-BuBe-x86_64.AppImage"
if [ ! -f "$APPIMAGE_SRC" ]; then
    # Fallback falls es im dist/ Ordner liegt
    APPIMAGE_SRC=$(find dist -name "*.AppImage" | head -n 1)
fi

cp "$APPIMAGE_SRC" "$RELEASE_DIR/$DIR_NAME/Hibi-BuBe-x86_64.AppImage"

# 4. plugin.xml erzeugen
cat <<EOF > "$RELEASE_DIR/$DIR_NAME/plugin.xml"
<?xml version="1.0" encoding="ISO-8859-1"?>
<plugin>
    <name>$NAME</name>
    <description>Moderner Report-Generator für Hibiscus</description>
    <version>$VERSION</version>
    <vendor>Florian Mösch</vendor>
    <menuitem
        id="hibi-bube.start"
        name="$NAME starten"
        action="sh \${plugin.dir}/bin/hibi-bube.sh"
    />
</plugin>
EOF

# 5. Starter-Script erzeugen
cat <<EOF > "$RELEASE_DIR/$DIR_NAME/bin/hibi-bube.sh"
#!/bin/bash
PLUGIN_DIR="\$(cd "\$(dirname "\$0")/.." && pwd)"
APPIMAGE="\$PLUGIN_DIR/Hibi-BuBe-x86_64.AppImage"
chmod +x "\$APPIMAGE"
"\$APPIMAGE" --d "\$HOME/.jameica" &
EOF
chmod +x "$RELEASE_DIR/$DIR_NAME/bin/hibi-bube.sh"

# 6. Alles zippen
echo "Erstelle ZIP-Archiv..."
cd "$RELEASE_DIR"
zip -r "${DIR_NAME}-jameica-plugin.zip" "$DIR_NAME"
cd ..

echo "✅ Fertig! Das Release liegt in $RELEASE_DIR/${DIR_NAME}-jameica-plugin.zip"