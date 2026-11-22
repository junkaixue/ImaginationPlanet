#!/system/bin/sh
# Run a command inside the Alpine Linux of /data/local/tmp/ip (proot: no real root, no system change).
# The folder itself is /ip inside; the phone's time zone is passed on. --kill-on-exit: what the
# command leaves behind (an adb server it forked, a script of a killed supervisor) ends with it,
# so a short call returns and nothing keeps driving the game unseen.
D=/data/local/tmp/ip
export PROOT_LOADER=$D/root/libexec/proot/loader PROOT_TMP_DIR=$D/tmp
mkdir -p $D/tmp
exec $D/root/bin/proot --kill-on-exit -0 -r $D/alpine -b /dev -b /proc -b /sys -b $D:/ip -w /ip \
  /usr/bin/env -i TZ=$(getprop persist.sys.timezone) HOME=/root TERM=xterm LANG=C.UTF-8 \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "$@"
