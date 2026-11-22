#!/bin/bash
# Set up, update, run and debug the game scripts inside an Android cloud phone, from this Mac,
# over adb (a Tailscale address). See cloudphone/README.md.
#
#   cloudphone/cp.sh [-s SERIAL] COMMAND [ARGS]
#
#   all                 a fresh phone: setup + code --github + app + up
#   setup               install proot + Alpine + Python/opencv/tesseract/adb/git (repairs, skips the rest)
#   code [--github]     put the code on the phone: this working tree (default, for testing
#                       unpushed changes) or a git checkout of origin/main fetched by the phone
#   app                 build (if the sources changed) and install the floating panel app
#   up                  start the supervisor and the panel
#   restart             restart the supervisor (after its files changed); the script resumes
#   scripts | status | log [N] | start ID | stop | update      talk to the supervisor
#   try ARGS...         a test run: stop the supervisor's script, run `python3 -u ARGS --adb
#                       127.0.0.1:5555 --delay 0` in the code folder (timeout $TRY_TIMEOUT s,
#                       default 600), then start the stopped script again
#   peek [SCALE] [OUT]  the phone screen as a JPEG (default 0.5, $SCRATCH/peek.jpg)
#   pull PATH [OUT]     an image file of the phone (e.g. app/pics/mac/zone/debug/X.png) as JPEG
#   sh CMD...           run a shell command inside the phone's Alpine (cwd /ip = the work folder)
#
# SERIAL: -s, else $CP_SERIAL, else cloudphone/.serial (one line, e.g. 100.104.162.101:5555).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
D=/data/local/tmp/ip
REPO_URL=https://github.com/junkaixue/ImaginationPlanet
SCRATCH="${SCRATCH:-${TMPDIR:-/tmp}}"
SPARSE='"/*.py" "/pics/mac/zone/*" "!/pics/mac/zone/pages/" "!/pics/mac/zone/debug/" "/cloudphone/phone/"'

usage() { sed -n '2,/^# SERIAL/p' "$0" | sed 's/^# \{0,1\}//'; }
SERIAL="${CP_SERIAL:-}"
if [ "${1:-}" = "-s" ]; then SERIAL="$2"; shift 2; fi
if [ -z "$SERIAL" ] && [ -f "$HERE/.serial" ]; then SERIAL="$(head -1 "$HERE/.serial")"; fi
[ -n "$SERIAL" ] || { echo "no phone: give -s HOST:PORT or write it to cloudphone/.serial"; exit 1; }
CMD="${1:-}"; shift || true

connect() {
  case "$SERIAL" in *:*) adb connect "$SERIAL" >/dev/null ;; esac
  local state; state="$(adb -s "$SERIAL" get-state 2>&1 || true)"
  [ "$state" = "device" ] || { echo "phone $SERIAL: $state (USB debugging on? Tailscale up?)"; exit 1; }
}
psh() { adb -s "$SERIAL" shell "$@"; }
inside() {   # CMD: run in Alpine; single quotes in CMD survive the two shells
  local sq="'\\''"                   # ' -> '\'' (a variable: in "..." the backslashes would stay)
  local q="${1//\'/$sq}"
  psh "cd $D && ./run.sh /bin/sh -c '$q'"
}
api() {   # METHOD PATH: the supervisor, through the phone's own curl
  psh "curl -sS -m 600 -X $1 'http://127.0.0.1:8765$2'"; echo
}
push() { local out; out="$(adb -s "$SERIAL" push "$1" "$2" 2>&1)" || { echo "adb push $1 failed: $out"; exit 1; }; }
push_phone_files() {
  psh "mkdir -p $D"
  for f in "$HERE"/phone/*; do push "$f" "$D/"; done
  psh "chmod 755 $D/*.sh"
}
jpeg() {   # OUT CMD: write the JPEG a phone-side command prints, fail when there is none
  adb -s "$SERIAL" exec-out "cd $D && ./run.sh $2 2>/dev/null" > "$1"
  [ -s "$1" ] || { echo "no image (is the code folder there? cp.sh code)"; exit 1; }
  echo "$1"
}

code_local() {
  local list tgz
  list="$(mktemp)"; tgz="$(mktemp -d)/code.tgz"
  ( cd "$REPO"
    { git ls-files --cached --others --exclude-standard -- '*.py' | grep -v /
      git ls-files --cached --others --exclude-standard -- pics/mac/zone | grep -v -E '^pics/mac/zone/(pages|debug)/'
    } | sort -u | while read -r f; do [ -f "$f" ] && echo "$f"; done > "$list"   # (deleted files left out)
    COPYFILE_DISABLE=1 tar czf "$tgz" -T "$list" )
  echo "pushing $(wc -l < "$list" | tr -d ' ') files ($(du -h "$tgz" | cut -f1))"
  push "$tgz" "$D/code.tgz"
  psh "mkdir -p $D/app && tar xzf $D/code.tgz -C $D/app && rm $D/code.tgz"
  rm -rf "$list" "$(dirname "$tgz")"
  push_phone_files
}

code_github() {
  # a shallow, sparse checkout: the root .py files, the zone templates and the phone files.
  # --no-checkout first: a plain sparse clone fetches every root file (a 94 MB installer) first.
  inside "set -e
    if [ -d app/.git ]; then
      cd app && git fetch -q --depth 1 origin main && git reset -q --hard FETCH_HEAD
    else
      rm -rf app && git clone -q --depth 1 --filter=blob:none --no-checkout $REPO_URL app
      cd app && git sparse-checkout set --no-cone $SPARSE && git checkout -q main
    fi
    git log -1 --format='code %h %s'"
  psh "cp $D/app/cloudphone/phone/* $D/ && chmod 755 $D/*.sh"
}

case "$CMD" in
  all)
    connect
    "$0" -s "$SERIAL" setup && "$0" -s "$SERIAL" code --github && "$0" -s "$SERIAL" app && "$0" -s "$SERIAL" up ;;
  setup)
    connect; push_phone_files; psh "sh $D/setup.sh" ;;
  code)
    connect
    if [ "${1:-}" = "--github" ]; then code_github; else code_local; fi ;;
  app)
    connect
    "$HERE/app/build.sh"
    if ! out="$(adb -s "$SERIAL" install -r "$HERE/app/panel.apk" 2>&1)"; then
      case "$out" in
        *UPDATE_INCOMPATIBLE*)   # signed with another machine's debug key: install afresh
          adb -s "$SERIAL" uninstall com.ip.panel >/dev/null
          adb -s "$SERIAL" install "$HERE/app/panel.apk" ;;
        *) echo "$out"; exit 1 ;;
      esac
    fi
    psh "appops set com.ip.panel SYSTEM_ALERT_WINDOW allow; pm grant com.ip.panel android.permission.POST_NOTIFICATIONS 2>/dev/null; true" ;;
  up)
    connect; psh "sh $D/start.sh"; psh "am start -n com.ip.panel/.MainActivity >/dev/null" ;;
  restart)
    connect
    psh "p=\$(cat $D/supervisor.pid 2>/dev/null); [ -n \"\$p\" ] && kill \$p 2>/dev/null
      for i in \$(seq 1 40); do [ -n \"\$p\" ] && [ -d /proc/\$p ] || break; sleep 1; done
      [ -n \"\$p\" ] && [ -d /proc/\$p ] && { echo 'old supervisor does not stop'; exit 1; }
      rm -f $D/supervisor.pid"
    psh "sh $D/start.sh" ;;
  scripts) connect; api GET /scripts ;;
  status) connect; api GET /status ;;
  log) connect; api GET "/log?n=${1:-60}" ;;
  start) connect; api POST "/start?id=$1" ;;
  stop) connect; api POST /stop ;;
  update) connect; api POST /update ;;
  try)
    connect
    prev="$(psh "curl -sS -m 10 http://127.0.0.1:8765/status" | sed -n 's/.*"running": "\([^"]*\)".*/\1/p')"
    if [ -n "$prev" ]; then echo "stopping $prev for the test"; api POST /stop >/dev/null; fi
    rc=0; inside "cd app && timeout ${TRY_TIMEOUT:-600} python3 -u $* --adb 127.0.0.1:5555 --delay 0" || rc=$?
    if [ -n "$prev" ]; then echo "starting $prev again"; api POST "/start?id=$prev"; fi
    exit $rc ;;
  peek)
    connect; jpeg "${2:-$SCRATCH/peek.jpg}" "/usr/bin/python3 /ip/peek.py ${1:-0.5}" ;;
  pull)
    connect; jpeg "${2:-$SCRATCH/$(basename "${1%.*}").jpg}" "/usr/bin/python3 /ip/jpg.py /ip/$1 0.5" ;;
  sh)
    connect; inside "$*" ;;
  *)
    usage; exit 1 ;;
esac
