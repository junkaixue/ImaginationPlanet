#!/system/bin/sh
# Restart the supervisor: SIGTERM to the running one, wait until it is gone, then start.sh.
# The old one first lets its script end the step in hand (up to 240 s), and an update under way
# installs a new panel app before that. The SIGTERM goes out again every 10 s: one that lands
# while an update re-execs the supervisor is lost with the old process image.
#   restart.sh [SECONDS]   wait up to SECONDS (600); then the wait goes on in the background, for
#                          an hour at most, and this ends with exit 3: the next supervisor starts
#                          on the phone once the old one is gone
#   restart.sh --find      only tell whether a supervisor runs: its pid and exit 0, or exit 1
# supervisor.pid is left to start.sh (it removes a stale one itself): one that another start has
# written meanwhile is not taken away. cloudphone/cp.sh restart runs its own copy of this file
# (pushed to tmp/, so that cp.sh and this logic match); the one here is the phone's.
D=/data/local/tmp/ip
p=$(cat $D/supervisor.pid 2>/dev/null)
alive() {   # the pid is a supervisor still (not a pid reused after a reboot)
  [ -n "$p" ] && cat /proc/$p/cmdline 2>/dev/null | tr '\0' ' ' | grep -q supervisor.py
}
find_supervisor() {   # the pid of a running supervisor: a python whose last argument is
  # supervisor.py (`python3 -u /ip/supervisor.py`, also started by hand with other options), not
  # the proot around it, nor a python that runs something else on the file (-c: an update's
  # load check, -m: a py_compile)
  if command -v pgrep >/dev/null 2>&1; then
    cand=$(pgrep -f 'supervisor[.]py')
  else
    cand=$(ls /proc | grep '^[0-9][0-9]*$')
  fi
  set -f                                      # (no file names for a * in a command line)
  for q in $cand; do
    set -- $(cat /proc/$q/cmdline 2>/dev/null | tr '\0' ' ')
    case "${1:-}" in python*|*/python*) ;; *) continue ;; esac
    last=; other=
    for w in "$@"; do
      last=$w
      case "$w" in -c|-m) other=1 ;; esac
    done
    [ -z "$other" ] || continue
    case "$last" in *supervisor.py) set +f; echo $q; return ;; esac
  done
  set +f
}
alive || p=$(find_supervisor)   # (supervisor.pid lost or stale while one runs: start.sh beside it
                                # would only fail on the port, and the old one would go on)
if [ "$1" = "--find" ]; then
  if alive; then echo $p; exit 0; fi
  exit 1
fi
gone_within() {   # SECONDS [quiet]: 0 once the old supervisor is gone, 1 when it outlasts SECONDS
  i=0
  while alive; do
    [ $i -lt $1 ] || return 1
    [ $((i % 10)) -ne 0 ] || kill $p 2>/dev/null
    [ -n "$2" ] || [ $i -eq 0 ] || [ $((i % 60)) -ne 0 ] ||
      echo "waiting for the old supervisor (its script ends the step in hand)"
    sleep 1
    i=$((i + 1))
  done
  return 0
}
if [ "$1" = "--background" ]; then
  if gone_within 3600 quiet; then
    exec sh $D/start.sh
  fi
  echo "restart: the old supervisor (pid $p) did not end in an hour; no new one was started"
  exit 1
fi
if gone_within ${1:-600}; then
  exec sh $D/start.sh
fi
setsid sh "$0" --background < /dev/null >> $D/logs/supervisor.log 2>&1 &
echo "the old supervisor is still ending: a new one starts on the phone once it is gone"
exit 3
