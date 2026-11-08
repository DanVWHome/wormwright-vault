#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${ANDROID_SDK_ROOT:?Set ANDROID_SDK_ROOT to your Android SDK folder}"
PLATFORM="$ANDROID_SDK_ROOT/platforms/android-35/android.jar"
TOOLS="${ANDROID_BUILD_TOOLS:-$ANDROID_SDK_ROOT/build-tools/35.0.0}"
BUILD_DIR="${BUILD_DIR:-$PWD/build-preview}"
mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/dex"
python3 - "$BUILD_DIR/AndroidManifest.xml" <<'PY'
import sys,xml.etree.ElementTree as ET
ET.register_namespace('android','http://schemas.android.com/apk/res/android')
tree=ET.parse('app/src/main/AndroidManifest.xml');tree.getroot().set('package','ai.wormwright.notes');tree.write(sys.argv[1],encoding='utf-8')
PY
"$TOOLS/aapt2" compile --dir app/src/main/res -o "$BUILD_DIR/resources.zip"
"$TOOLS/aapt2" link -o "$BUILD_DIR/base.apk" -I "$PLATFORM" -A app/src/main/assets --manifest "$BUILD_DIR/AndroidManifest.xml" "$BUILD_DIR/resources.zip"
find app/src/main/java -name '*.java' > "$BUILD_DIR/java-sources.txt"
javac -encoding UTF-8 -source 17 -target 17 -classpath "$PLATFORM:app/libs/*" -d "$BUILD_DIR/classes" @"$BUILD_DIR/java-sources.txt"
jar cf "$BUILD_DIR/classes.jar" -C "$BUILD_DIR/classes" .
"$TOOLS/d8" --lib "$PLATFORM" --min-api 26 --output "$BUILD_DIR/dex" "$BUILD_DIR/classes.jar" app/libs/*.jar
python3 - "$BUILD_DIR" <<'PY'
from pathlib import Path
import sys,zipfile,shutil
b=Path(sys.argv[1]);shutil.copy2(b/'base.apk',b/'unsigned.apk')
with zipfile.ZipFile(b/'unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:
 for p in (b/'dex').glob('*.dex'): z.write(p,p.name)
PY
"$TOOLS/zipalign" -f 4 "$BUILD_DIR/unsigned.apk" "$BUILD_DIR/aligned.apk"
SIGNING_KEY="${SIGNING_KEY:-$BUILD_DIR/preview.jks}"
if [[ ! -f "$SIGNING_KEY" ]]; then
 keytool -genkeypair -keystore "$SIGNING_KEY" -storepass android -keypass android -alias preview -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=Wormwright Notes Preview' >/dev/null 2>&1
fi
"$TOOLS/apksigner" sign --ks "$SIGNING_KEY" --ks-key-alias preview --ks-pass pass:android --key-pass pass:android --out "$BUILD_DIR/Wormwright-Notes-0.1.0-preview.4.apk" "$BUILD_DIR/aligned.apk"
"$TOOLS/apksigner" verify --verbose "$BUILD_DIR/Wormwright-Notes-0.1.0-preview.4.apk"
printf '\nBuilt: %s\n' "$BUILD_DIR/Wormwright-Notes-0.1.0-preview.4.apk"
