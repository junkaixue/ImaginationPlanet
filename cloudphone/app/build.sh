#!/bin/bash
# Build cloudphone/app/panel.apk (the floating panel) without Gradle: aapt2 + javac + d8 +
# zipalign + apksigner. The two SDK parts it needs are downloaded once into cloudphone/app/.sdk
# (git-ignored, ~150 MB); signed with the standard debug key ~/.android/debug.keystore (made if
# missing). Skipped when panel.apk was built from the current sources (panel.apk.src).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SDK="$HERE/.sdk"
OUT="$HERE/.build"
BT_ZIP=build-tools_r34-macosx.zip;  BT_SHA=00e1301387028f33753e38274401694e1a27c62f
PF_ZIP=platform-33-ext3_r03.zip;    PF_SHA=394bc86d8d3452aa4d419b67743025a6fb2cd9d0
REPO_URL=https://dl.google.com/android/repository

src_hash() { cd "$HERE" && cat AndroidManifest.xml $(find src -name '*.java' | sort) | shasum | cut -d' ' -f1; }
if [ "${1:-}" != "-f" ] && [ -f "$HERE/panel.apk" ] && [ "$(cat "$HERE/panel.apk.src" 2>/dev/null)" = "$(src_hash)" ]; then
  echo "panel.apk is up to date"; exit 0
fi

fetch() {   # zip sha1
  [ -f "$SDK/$1.ok" ] && return
  mkdir -p "$SDK"
  echo "downloading $1"
  curl -sSL -o "$SDK/$1" "$REPO_URL/$1"
  [ "$(shasum "$SDK/$1" | cut -d' ' -f1)" = "$2" ] || { echo "$1: checksum mismatch"; exit 1; }
  (cd "$SDK" && unzip -q -o "$1" && rm "$1" && touch "$1.ok")
}
fetch $BT_ZIP $BT_SHA
fetch $PF_ZIP $PF_SHA
BT="$(dirname "$(find "$SDK" -name aapt2 -type f | head -1)")"
JAR="$(find "$SDK" -name android.jar -type f | head -1)"
export JAVA_HOME="${JAVA_HOME:-$(/usr/libexec/java_home -v 11+ 2>/dev/null || /usr/libexec/java_home)}"
JAVA="$JAVA_HOME/bin/java"

KS="$HOME/.android/debug.keystore"
if [ ! -f "$KS" ]; then
  mkdir -p "$HOME/.android"
  "$JAVA_HOME/bin/keytool" -genkeypair -keystore "$KS" -storepass android -keypass android -alias androiddebugkey \
    -dname "CN=Android Debug,O=Android,C=US" -keyalg RSA -keysize 2048 -validity 10000 >/dev/null
fi

rm -rf "$OUT"; mkdir -p "$OUT/classes"
"$BT/aapt2" link -o "$OUT/base.apk" --manifest "$HERE/AndroidManifest.xml" -I "$JAR" \
  --min-sdk-version 24 --target-sdk-version 33
# --release 8 + android.jar on the classpath: java.* (with the lambda factory) from the JDK
"$JAVA_HOME/bin/javac" --release 8 -nowarn -encoding UTF-8 -classpath "$JAR" -d "$OUT/classes" \
  $(find "$HERE/src" -name '*.java')
"$JAVA" -cp "$BT/lib/d8.jar" com.android.tools.r8.D8 --min-api 24 --lib "$JAR" --output "$OUT" \
  $(find "$OUT/classes" -name '*.class')
cp "$OUT/base.apk" "$OUT/unsigned.apk"
(cd "$OUT" && zip -q unsigned.apk classes.dex)
"$BT/zipalign" -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
"$JAVA" -jar "$BT/lib/apksigner.jar" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias androiddebugkey --out "$HERE/panel.apk" "$OUT/aligned.apk"
src_hash > "$HERE/panel.apk.src"
rm -rf "$OUT" "$HERE/panel.apk.idsig"
echo "built $HERE/panel.apk ($(du -h "$HERE/panel.apk" | cut -f1))"
