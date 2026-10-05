#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/HP 117w Manual Duplex.app"
SERVICE="$HOME/Library/PDF Services/HP 117w Manual Duplex"
BUILD="$(/usr/bin/mktemp -d -t hp117w-install)"
NEW_APP="$BUILD/HP 117w Manual Duplex.app"
BACKUP=""

if /usr/bin/pgrep -f "^$APP/Contents/MacOS/droplet$" >/dev/null 2>&1; then
  echo "Quit HP 117w Manual Duplex before installing, then run this script again."
  exit 1
fi

mkdir -p "$HOME/Applications" "$HOME/Library/PDF Services" "$HOME/Documents"
PYTHON="$(command -v python3)"
"$PYTHON" - "$ROOT/main.applescript" "$BUILD/main.applescript" "$APP" "$PYTHON" <<'PYCODE'
import pathlib,re,subprocess,sys
source=pathlib.Path(sys.argv[1]).read_text()
installed=pathlib.Path(sys.argv[3])/'Contents/Resources/Scripts/main.scpt'
if installed.exists():
    old=subprocess.check_output(['/usr/bin/osadecompile',str(installed)],text=True)
    for key,placeholder in [('queueName','REPLACE_WITH_YOUR_CUPS_QUEUE_NAME'),('printerLabel','Your Printer Name')]:
        match=re.search(r'property '+key+r' : ("[^"\n]*")',old)
        if match and ('"'+placeholder+'"') in source:
            source=source.replace('property '+key+' : "'+placeholder+'"','property '+key+' : '+match[1])
source=re.sub(r'property mobilePython : "[^"\n]*"','property mobilePython : "'+sys.argv[4]+'"',source)
pathlib.Path(sys.argv[2]).write_text(source)
PYCODE
/usr/bin/osacompile -o "$NEW_APP" "$BUILD/main.applescript"
cp "$ROOT/mobile.py" "$NEW_APP/Contents/Resources/mobile.py"
cp "$ROOT/duplex.js" "$NEW_APP/Contents/Resources/duplex.js"
cp "$ROOT/Info.plist" "$NEW_APP/Contents/Info.plist"
/usr/bin/codesign --force --deep --sign - "$NEW_APP"

if [ -e "$APP" ]; then
  BACKUP="$APP.backup.$(/bin/date +%Y%m%d%H%M%S)"
  mv "$APP" "$BACKUP"
fi
mv "$NEW_APP" "$APP"
cp "$ROOT/pdf-service/HP 117w Manual Duplex" "$SERVICE"
chmod 755 "$SERVICE"

if [ ! -f "$HOME/Documents/HP 117w Manual Duplex Print Log.xlsx" ]; then
  echo "Create an Excel workbook named HP 117w Manual Duplex Print Log.xlsx in Documents."
  echo "Add a sheet named Print Log with these headers in A1:G1: Printed at, PDF, Pages, Sheets, Printer, Status, Notes."
fi

rm -rf "$BUILD"
echo "Installed app: $APP"
echo "Installed PDF service: $SERVICE"
if [ -n "$BACKUP" ]; then echo "Previous app backup: $BACKUP"; fi
