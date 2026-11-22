#!/system/bin/sh
# Restart the supervisor: SIGTERM to the running one, wait until it is gone, then start.sh.
# The old one first lets its script end the step in hand (up to 240 s), and an update under way
# installs a new panel app before that. The SIGTERM goes out again every 10 s: one that lands
# while an update re-execs the supervisor is lost with the old process image.
#   restart.sh [SECONDS]   wait up to SECONDS (600); then the wait goes on in the background, for
#                          an hour at most, and this ends with exit 3: the next supervisor starts
#                          on the phone once the old one is gone
# supervisor.pid is left to start.sh (it removes a stale one itself): one that another start has
# written meanwhile is not taken away. Called by cloudphone/cp.sh restart.
D=/data/local/tmp/ip
p=$(cat $D/supervisor.pid 2>/dev/null)
alive() {   # the pid is a supervisor still (not a pid reused after a reboot)
  [ -n "$p" ] && cat /proc/$p/cmdline 2>/dev/null | tr '\0' ' ' | grep -q supervisor.py
}
find_supervisor() {   # the pid of a running supervisor.py (python itself, not the proot around it)
  for q in $(pgrep -f 'supervisor[.]py' 2>/dev/null); do
    c=$(cat /proc/$q/cmdline 2>/dev/null | tr '\0' ' ')
    case "${c%% *}" in python3|*/python3) echo $q; return ;; esac
  done
}
alive || p=$(find_supervisor)   # (supervisor.pid lost or stale while one runs: start.sh beside it
                                # would only fail on the port, and the old one would go on)
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
setsid sh $D/restart.sh --background < /dev/null >> $D/logs/supervisor.log 2>&1 &
echo "the old supervisor is still ending: a new one starts on the phone once it is gone"
exit 3
