#!/system/bin/sh
# Install the script environment on the phone, as the adb shell user (no root, no app):
# proot + an Alpine Linux in /data/local/tmp/ip, with Python, opencv, tesseract, adb and git.
# Downloads go straight to the phone (Alpine and PyPI from mirrors in China; proot, 180 KB, from
# GitHub). Safe to run again: done steps are skipped, the package step repairs a partial
# install. Called by cloudphone/cp.sh setup (which pushes this folder first).
set -e
D=/data/local/tmp/ip
ALPINE_MIRROR=https://mirrors.aliyun.com/alpine
PYPI=https://mirrors.aliyun.com/pypi/simple
PROOT_URL=https://raw.githubusercontent.com/green-green-avk/build-proot-android/master/packages/proot-android-aarch64.tar.gz
PACKAGES="python3 py3-numpy py3-opencv py3-pillow py3-pip tesseract-ocr tesseract-ocr-data-eng android-tools git tzdata"
cd $D
mkdir -p tmp logs

if [ ! -x root/bin/proot ]; then
  echo "== proot"
  # (a proot.tgz already here was pushed from the Mac: some phones cannot reach GitHub's raw files)
  [ -s proot.tgz ] || curl -fsSL -m 300 -o proot.tgz $PROOT_URL || {
    rm -f proot.tgz
    echo "proot could not be downloaded: $PROOT_URL"
    echo "on the Mac: download that file, adb push it to $D/proot.tgz, and run setup again"
    exit 1
  }
  tar xzf proot.tgz || { rm -f proot.tgz; echo "proot.tgz does not unpack (removed): run setup again"; exit 1; }
  rm proot.tgz
fi
export PROOT_LOADER=$D/root/libexec/proot/loader PROOT_TMP_DIR=$D/tmp

if [ ! -f alpine/etc/alpine-release ]; then
  echo "== alpine"
  REL=$(curl -fsSL -m 60 $ALPINE_MIRROR/latest-stable/releases/aarch64/latest-releases.yaml | grep -m1 'file: alpine-minirootfs' | sed 's/.*file: //')
  [ -n "$REL" ]
  curl -fsSL -m 300 -o rootfs.tgz $ALPINE_MIRROR/latest-stable/releases/aarch64/$REL
  rm -rf alpine
  mkdir -p alpine
  ./root/bin/proot -0 -l /system/bin/tar xzf rootfs.tgz -C alpine
  rm rootfs.tgz
fi
printf "nameserver 223.5.5.5\nnameserver 114.114.114.114\n" > alpine/etc/resolv.conf
sed -i "s#https://dl-cdn.alpinelinux.org/alpine#$ALPINE_MIRROR#" alpine/etc/apk/repositories
chmod 755 run.sh start.sh

echo "== packages"
# (every time: quick when all are there, and it completes an install that was cut off)
./run.sh /sbin/apk add -q --no-progress $PACKAGES || { ./run.sh /sbin/apk update -q; ./run.sh /sbin/apk add -q --no-progress $PACKAGES; }
if ! ./run.sh /usr/bin/python3 -c "import pytesseract" 2>/dev/null; then
  echo "== pytesseract"
  ./run.sh /usr/bin/pip install -q --break-system-packages --root-user-action=ignore -i $PYPI pytesseract
fi
./run.sh /usr/bin/python3 -c "import cv2, numpy, PIL, pytesseract, sys; print('python', sys.version.split()[0], 'opencv', cv2.__version__)"
echo "setup done"
