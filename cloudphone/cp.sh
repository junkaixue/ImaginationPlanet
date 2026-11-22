#!/bin/bash
# Set up, update, run and debug the game scripts inside an Android cloud phone, from this Mac,
# over adb (a Tailscale address). See cloudphone/README.md.
#
#   cloudphone/cp.sh [-a ACCOUNT] [-s SERIAL] COMMAND [ARGS]
#
#   all                 a fresh phone: setup + code --github + app + up
#   setup               install proot + Alpine + Python/opencv/tesseract/adb/git (repairs, skips the
#                       rest); with -a it names the phone's account (/ip/account)
#   code [--github]     put the code on the phone: this working tree (default, for testing
#                       unpushed changes) or a git checkout of origin/main fetched by the phone
#   app                 build (if the sources changed) and install the floating panel app
#   up                  start the supervisor and the panel
#   restart             restart the supervisor (after its files changed); the script resumes
#   scripts | status | log [N] | start ID | stop | update [--force]   talk to the supervisor
#   try ARGS...         a test run: stop the supervisor's script, run `python3 -u ARGS --adb
#                       127.0.0.1:5555 --delay 0` in the code folder (timeout $TRY_TIMEOUT s,
#                       default 600), then start the stopped script again
#   peek [SCALE] [OUT]  the phone screen as a JPEG (default 0.5, $SCRATCH/peek.jpg)
#   pull PATH [OUT]     an image file of the phone (e.g. app/pics/mac/zone/debug/X.png) as JPEG
#   sh CMD...           run a shell command inside the phone's Alpine (cwd /ip = the work folder)
#
# SERIAL: -s, else with -a cloudphone/.serial.ACCOUNT, else $CP_SERIAL, else cloudphone/.serial (one
# line, e.g. 100.104.162.101:5555).
# ACCOUNT (-a, e.g. gs): the phone of that game account. An account is a config, picked on the
# phone by the name in /ip/account: phone/scripts.ACCOUNT.json (the panel's list) and
# pics/mac/zone/loadout_standard_ACCOUNT.png. No -a, no name on the phone: the default files.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
D=/data/local/tmp/ip
REPO_URL=https://github.com/junkaixue/ImaginationPlanet
SCRATCH="${SCRATCH:-${TMPDIR:-/tmp}}"
# what the phone checks out (keep in step with SPARSE in phone/supervisor.py)
SPARSE='"/*.py" "/pics/mac/zone/*" "!/pics/mac/zone/pages/" "!/pics/mac/zone/debug/" "/cloudphone/phone/" "/cloudphone/app/panel.apk"'
# what the scripts keep next to them (gitignored): a fresh clone puts them back
STATE_FILES="fortress_busy.json fortress_gear.json"

usage() { sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; }
SERIAL=""; ACCOUNT=""
while :; do
  case "${1:-}" in
    -s) SERIAL="${2:?-s needs HOST:PORT}"; shift 2 ;;
    -a) ACCOUNT="${2:?-a needs an account name}"; shift 2 ;;
    *) break ;;
  esac
done
case "$ACCOUNT" in *[!A-Za-z0-9]*) echo "an account name is letters and digits: $ACCOUNT"; exit 1 ;; esac
if [ -z "$SERIAL" ] && [ -n "$ACCOUNT" ]; then
  [ -f "$HERE/.serial.$ACCOUNT" ] ||
    { echo "no phone for account $ACCOUNT: write HOST:PORT to cloudphone/.serial.$ACCOUNT (or give -s)"; exit 1; }
  SERIAL="$(head -1 "$HERE/.serial.$ACCOUNT")"
fi
[ -n "$SERIAL" ] || SERIAL="${CP_SERIAL:-}"
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
api() {   # METHOD PATH: the supervisor, through the phone's own curl; curl's exit status. (An
  # update may fetch the commit and then the changed files for up to 600 s each, check out and
  # set the file list for 120 s each, wait 240 s for the script to stop and ~75 s for the game;
  # a step that runs out of time takes up to 30 s more to end.)
  local rc=0
  psh "curl -sS -m 2100 -X $1 'http://127.0.0.1:8765$2'" || rc=$?
  echo
  return $rc
}
push() { local out; out="$(adb -s "$SERIAL" push "$1" "$2" 2>&1)" || { echo "adb push $1 failed: $out" >&2; exit 1; }; }
sup_sum() { psh "md5sum $D/supervisor.py 2>/dev/null | cut -d' ' -f1"; }
restart_sh() {   # ARGS: this checkout's phone/restart.sh, run from the phone's tmp/ (cp.sh and it
  # match, and the phone's own copy stays)
  psh "mkdir -p $D/tmp"
  push "$HERE/phone/restart.sh" "$D/tmp/cp.restart.sh"
  psh "sh $D/tmp/cp.restart.sh $*"
}
supervisor_process() {   # 0: a supervisor runs on the phone (whatever supervisor.pid says), 1: none
  # does, 2: the phone did not answer (adb or the link dropped: no word on the supervisor).
  # restart.sh --find prints the pid or "none"; nothing here ends the script.
  local out
  adb -s "$SERIAL" shell "mkdir -p $D/tmp" >/dev/null 2>&1 || return 2
  adb -s "$SERIAL" push "$HERE/phone/restart.sh" "$D/tmp/cp.restart.sh" >/dev/null 2>&1 || return 2
  out="$(adb -s "$SERIAL" shell "sh $D/tmp/cp.restart.sh --find" 2>/dev/null || true)"
  case "$out" in
    none*) return 1 ;;
    [0-9]*) return 0 ;;
    *) return 2 ;;
  esac
}
install_apk() {   # [-r]: adb install of the panel app, its output in $out; tried again when the
  # cloud phone's install check refuses it (INSTALL_FAILED_VERIFICATION_FAILURE, now and then)
  local i
  for i in 1 2 3; do
    if out="$(adb -s "$SERIAL" install "$@" "$HERE/app/panel.apk" 2>&1)"; then return 0; fi
    case "$out" in *VERIFICATION_FAILURE*) ;; *) return 1 ;; esac
    [ $i -lt 3 ] || return 1
    echo "the phone's install check refused the app (try $i); again in 10 s"; sleep 10
  done
}
restart_if_changed() {   # BEFORE: the supervisor.py checksum before new phone files came in
  [ "$(sup_sum)" != "$1" ] || return 0
  local st; st="$(psh "curl -s -m 10 http://127.0.0.1:8765/status" || true)"
  [ -n "$st" ] || return 0                                  # (none running: the next up starts the new one)
  case "$st" in
    *'"stopping":'*)   # (a supervisor with graceful stops: the script ends at a safe point and resumes)
      echo "supervisor.py changed: restarting the supervisor"
      "$0" -s "$SERIAL" restart || [ $? -eq 3 ] ;;       # (3: the phone starts the next one itself)
    *)   # an older one kills its script at once (maybe mid gear swap): leave the moment to the user
      echo "supervisor.py changed, but the running supervisor is an older one that kills its script"
      echo "at once: run 'cloudphone/cp.sh restart' while 'cloudphone/cp.sh log' shows the script waiting" ;;
  esac
}
mark_local_code() {
  # the phone now has code from this working tree: its time (the commit's when nothing that is
  # pushed differs from it, else now). 更新 keeps it while GitHub's main is older (not pushed yet).
  local t h
  local pushed=(':(glob)*.py' pics/mac/zone ':(exclude)pics/mac/zone/pages' ':(exclude)pics/mac/zone/debug'
                cloudphone/phone)
  h="$(git -C "$REPO" log -1 --format=%h)"
  # (tracked files among those pushed. An untracked one goes to the phone as well, and the label
  # says so, but an update does not replace it: it does not make the code newer than the commit.)
  if git -C "$REPO" diff --quiet HEAD -- "${pushed[@]}"; then
    t="$(git -C "$REPO" log -1 --format=%ct)"
    [ -z "$(git -C "$REPO" ls-files --others --exclude-standard -- "${pushed[@]}")" ] || h="$h+untracked"
  else
    t="$(date +%s)"; h="$h+local"
  fi
  psh "echo $t $h > $D/local_code"
}
push_phone_files() {
  local before; before="$(sup_sum)"
  psh "mkdir -p $D"
  for f in "$HERE"/phone/*; do push "$f" "$D/"; done
  psh "chmod 755 $D/*.sh"
  mark_local_code
  restart_if_changed "$before"
}
push_proot() {   # proot comes through this Mac when the phone has none: some phones cannot reach
  # GitHub's raw files (setup.sh uses a proot.tgz that is there, and downloads it itself otherwise)
  if psh "[ -x $D/root/bin/proot ]"; then return 0; fi
  local url tmp
  url="$(sed -n 's/^PROOT_URL=//p' "$HERE/phone/setup.sh")"
  tmp="$(mktemp -d)"
  if curl -fsSL -m 120 -o "$tmp/proot.tgz" "$url"; then
    push "$tmp/proot.tgz" "$D/proot.tgz"
  else
    echo "this Mac could not download proot ($url): the phone tries it itself"
  fi
  rm -rf "$tmp"
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
  # a shallow, sparse checkout: the root .py files, the zone templates, the phone files and the
  # panel app. --no-checkout first: a plain sparse clone fetches every root file (a 94 MB
  # installer) first.
  local before; before="$(sup_sum)"
  # a running supervisor does it itself (/update, also over newer code from the Mac): it is the
  # only one that changes its checkout, and it restarts what changed
  if psh "[ -d $D/app/.git ]"; then
    if [ -n "$(psh "curl -s -m 10 http://127.0.0.1:8765/status" || true)" ]; then
      # (while it is busy with an update of its own or a restart, or silent between two
      # supervisors, the request is made again: for 15 min from the first try, then no more)
      local out rc gone=0 end=$((SECONDS + 900))
      while :; do
        out="$(api POST "/update?force=1" || true)"
        echo "${out:-no answer from the supervisor}"
        case "$out" in
          *'"result": "updated to'*|*'"result": "已是最新'*) return 0 ;;
          *已经在更新了*|*服务正在重启*) [ $SECONDS -lt $end ] || { echo "the supervisor stayed busy: try again later"; exit 1; }
            echo "(the supervisor is busy: again in 20 s)" ;;
          "")   # (silent between two supervisors, for seconds; gone when no process is found twice;
                # a phone that does not answer is a drop of the link and says nothing of it)
            rc=0; supervisor_process || rc=$?
            case $rc in 0) gone=0 ;; 1) gone=$((gone + 1)) ;; esac
            [ $gone -lt 2 ] || { echo "the supervisor is gone: start it (cloudphone/cp.sh up) and run this again"; exit 1; }
            [ $SECONDS -lt $end ] || { echo "no answer from the supervisor for 15 min: giving up"; exit 1; }
            echo "(again in 20 s)" ;;
          *) exit 1 ;;
        esac
        sleep 20
      done
    else
      local rc=0; supervisor_process || rc=$?
      case $rc in
        0) echo "the supervisor runs but does not answer: try again (or cp.sh restart)"; exit 1 ;;
        2) echo "the phone does not answer adb: try again"; exit 1 ;;
      esac
    fi
  fi
  inside "set -e
    if [ -d app/.git ]; then
      cd app && git fetch -q --depth 1 origin main && git reset -q --hard FETCH_HEAD
      git sparse-checkout set --no-cone $SPARSE
    else
      # (into app.new: a clone cut off leaves app/, the scripts' state files in it, as it was)
      rm -rf app.new && git clone -q --depth 1 --filter=blob:none --no-checkout $REPO_URL app.new
      ( cd app.new && git sparse-checkout set --no-cone $SPARSE && git checkout -q main )
      for f in $STATE_FILES; do [ ! -f app/\$f ] || mv app/\$f app.new/; done
      rm -rf app && mv app.new app && cd app
    fi
    git log -1 --format='code %h %s'"
  psh "cp $D/app/cloudphone/phone/* $D/ && chmod 755 $D/*.sh && rm -f $D/local_code"   # (GitHub's code now)
  restart_if_changed "$before"
}

case "$CMD" in
  all)
    connect
    "$0" -s "$SERIAL" ${ACCOUNT:+-a "$ACCOUNT"} setup && "$0" -s "$SERIAL" code --github && "$0" -s "$SERIAL" app && "$0" -s "$SERIAL" up ;;
  setup)
    connect; push_phone_files
    # (the phone's account: the supervisor and the scripts take that account's config from now on)
    if [ -n "$ACCOUNT" ]; then psh "echo $ACCOUNT > $D/account"; echo "this phone is account $ACCOUNT"; fi
    push_proot
    psh "sh $D/setup.sh" ;;
  code)
    connect
    if [ "${1:-}" = "--github" ]; then code_github; else code_local; fi ;;
  app)
    connect
    "$HERE/app/build.sh"
    if ! install_apk -r; then
      case "$out" in
        *UPDATE_INCOMPATIBLE*)   # signed with another machine's debug key: install afresh
          adb -s "$SERIAL" uninstall com.ip.panel >/dev/null ||
            { echo "could not uninstall the panel app that another machine signed"; exit 1; }
          install_apk ||
            { echo "$out"; echo "the old panel app is uninstalled and the new one did not install: run cp.sh app again"; exit 1; } ;;
        *) echo "$out"; exit 1 ;;
      esac
    fi
    psh "appops set com.ip.panel SYSTEM_ALERT_WINDOW allow; pm grant com.ip.panel android.permission.POST_NOTIFICATIONS 2>/dev/null; true"
    # (what 更新 compares the checkout's panel.apk with)
    psh "echo $(shasum "$HERE/app/panel.apk" | cut -d' ' -f1) > $D/panel.apk.sha"
    echo "panel app installed (start it with: cloudphone/cp.sh up)" ;;
  up)
    connect; psh "sh $D/start.sh"; psh "am start -n com.ip.panel/.MainActivity >/dev/null" ;;
  restart)
    connect
    # (phone/restart.sh: SIGTERM, the wait for the script's safe point, start.sh. Exit 3: the
    # old supervisor is still ending after 10 min, the phone starts the next one itself.)
    restart_sh ;;
  scripts) connect; api GET /scripts ;;
  status) connect; api GET /status ;;
  log) connect; api GET "/log?n=${1:-60}" ;;
  start) connect; api POST "/start?id=$1" ;;
  stop) connect; api POST /stop ;;
  update)   # --force: also when the phone has newer code from the Mac than GitHub (it goes back)
    connect; if [ "${1:-}" = "--force" ]; then api POST "/update?force=1"; else api POST /update; fi ;;
  try)
    connect
    st="$(psh "curl -s -m 10 http://127.0.0.1:8765/status" || true)"
    if [ -z "$st" ]; then
      rc=0; supervisor_process || rc=$?
      case $rc in
        0) echo "the supervisor runs but does not answer: no test beside its script (try again, or cp.sh restart)"
           exit 1 ;;
        2) echo "the phone does not answer adb: try again"; exit 1 ;;
      esac
    fi                                                    # (empty and no supervisor: nothing to stop)
    # what the supervisor means to run (state.json): also a script being restarted, or waiting
    # for its automatic restart; nothing when it was stopped by hand
    case "$st" in
      *'"wanted":'*) prev="$(echo "$st" | sed -n 's/.*"wanted": "\([^"]*\)".*/\1/p')" ;;
      *) prev="$(echo "$st" | sed -n 's/.*"running": "\([^"]*\)".*/\1/p')" ;;   # (an older supervisor)
    esac
    if [ -n "$prev" ]; then echo "stopping $prev for the test"; fi
    if [ -n "$st" ]; then
      out="$(api POST /stop || true)"                     # (it also waits for a stop under way)
      case "$out" in
        *'"result": "ok"'*) ;;
        *) echo "the supervisor did not stop its script (${out:-no answer}): no test beside it"; exit 1 ;;
      esac
    fi
    # SIGTERM at the timeout ends the script at its next stop point (exit 143); -k: killed 300 s later
    rc=0; inside "cd app && timeout -k 300 ${TRY_TIMEOUT:-600} python3 -u $* --adb 127.0.0.1:5555 --delay 0" || rc=$?
    case $rc in 124|143) echo "(the test run was stopped at ${TRY_TIMEOUT:-600} s)" ;; esac
    if [ -n "$prev" ]; then
      echo "starting $prev again"
      api POST "/start?id=$prev" || echo "could not start it: cloudphone/cp.sh start $prev"
    fi
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
