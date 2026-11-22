#!/system/bin/sh
# Start the supervisor (supervisor.py, http://127.0.0.1:8765) unless it is running. It is
# detached from the calling shell (adb from the Mac, or the panel app's local adb), so it lives
# on after that shell ends; a reboot of the phone ends it. supervisor.pid is written by the
# supervisor itself (its own pid, not proot's: a SIGTERM to it stops the script first).
D=/data/local/tmp/ip
mkdir -p $D/logs
running() {   # the pid in supervisor.pid is a live supervisor (not a reused pid after a reboot)
  [ -f $D/supervisor.pid ] && tr '\0' ' ' < /proc/$(cat $D/supervisor.pid)/cmdline 2>/dev/null | grep -q supervisor.py
}
if running; then
  echo "supervisor already running (pid $(cat $D/supervisor.pid))"
  exit 0
fi
rm -f $D/supervisor.pid
cd $D
setsid nohup ./run.sh /usr/bin/python3 -u /ip/supervisor.py >> $D/logs/supervisor.log 2>&1 < /dev/null &
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  sleep 1
  if running; then
    echo "supervisor started (pid $(cat $D/supervisor.pid))"
    exit 0
  fi
done
echo "supervisor did not start; see $D/logs/supervisor.log"
tail -5 $D/logs/supervisor.log
exit 1
