"""Play on an Android device over adb instead of the emulator window on the Mac: from the Mac
(MuMu's adb port, a cloud phone through Tailscale) or from the Linux inside the cloud phone,
which reaches its own adbd at 127.0.0.1:5555 (cloudphone/). Templates come from pics/mac.

Every template and layout was captured on the Mac emulator window (physical px, REF_SFT physical
px per logical px). A device screenshot is scaled down to that reference size before anyone looks
at it, and taps are scaled back up, so the rest of the code does not see the difference. The
window-scale calibration (zone_explore.calibrate_scale) corrects what REF_WIDTH leaves over.

    device = AdbDevice("127.0.0.1:16384")    # MuMu's adb port; a cloud phone: "100.x.y.z:5555"
    click.use_device(device)                 # before ZoneExplore is created
"""
import io
import subprocess
import time

import cv2
import numpy as np
from PIL import Image

from log_helper import log

# Game width in physical px on the Mac window the templates come from: the ZBase->ZTeam distance
# on a 1440 px wide device is 1.449 x REFERENCE_ANCHOR_DIST, 1440 / 1.449 = 993.8.
REF_WIDTH = 993.8
REF_SFT = 2                 # physical px per logical px on that Mac; layouts are in logical px
ADB_TIMEOUT = 20            # seconds for one adb call ...
SHOT_TIMEOUT = 90           # ... and for one screenshot (a whole PNG over a slow link)
RETRY_WAITS = (2, 5, 10, 30, 60)    # seconds between attempts while the device is unreachable; the
                                    # last one repeats: a cloud phone that drops out is waited for
SLOW_SWIPE_SPEED = 300      # device px/s of a drag without motionevent: `input swipe` lets go at
                            # full speed, slowly enough that the page should not fling on
PNG_MAGIC = b"\x89PNG"
TAP_HOLD_MS = 80            # a tap is held this long: the game misses some `input tap`s, whose down
                            # and up come at the same instant


class AdbLost(RuntimeError):
    """A tap or drag may not have reached the device; it answers again now, so the pass starts
    again from a fresh look at the screen (FortressFight.run does not count it as an error)."""


class AdbDevice:
    def __init__(self, serial):
        self.serial = serial
        self.ref_sft = REF_SFT
        self._connect(must=True)
        shot = self._capture()
        self.size = (shot.shape[1], shot.shape[0])
        self.k = min(self.size) / REF_WIDTH      # device px per reference physical px
        t = time.time()
        self._call(["shell", "true"])
        t_shell = time.time() - t
        t = time.time()
        usage = subprocess.run(["adb", "-s", serial, "shell", "input"], capture_output=True,
                               timeout=ADB_TIMEOUT)
        # the start-up time of one `input` process; it paces the moves of a drag
        self.input_start = max(0.0, time.time() - t - t_shell)
        usage = usage.stdout + usage.stderr
        sdk = self._call(["shell", "getprop", "ro.build.version.sdk"]).strip()
        # `input motionevent` exists from Android 10 (whose usage text names it "event"); CANCEL
        # only from about 12, so a finger is lifted with UP before
        self.motion = sdk.isdigit() and int(sdk) >= 29
        self.lift = "CANCEL" if b"CANCEL" in usage else "UP"
        log(f"adb device {serial}: screen {self.size[0]}x{self.size[1]}, scale {self.k:.3f}, "
            f"round trip {t_shell:.2f} s, input start {self.input_start:.2f} s, "
            f"drag by {'motionevent' if self.motion else 'slow swipe (may overshoot: check the scrolls)'}")

    # ------------------------------------------------------------------ adb calls
    def _connect(self, must=False):
        """`adb connect` for a network serial (host:port); a USB serial needs none. A transport
        that went offline is dropped first: `adb connect` alone answers "already connected"."""
        if ":" not in self.serial:
            return
        if not must:
            subprocess.run(["adb", "disconnect", self.serial], capture_output=True, timeout=ADB_TIMEOUT)
        out = subprocess.run(["adb", "connect", self.serial], capture_output=True,
                             timeout=ADB_TIMEOUT).stdout.decode("utf-8", "replace").strip()
        if "connected" not in out:      # "connected to" / "already connected to"
            if must:
                raise RuntimeError(f"adb connect {self.serial}: {out}")
            log(f"adb reconnect: {out}")

    def _reconnect(self, attempt, what):
        wait = RETRY_WAITS[min(attempt - 1, len(RETRY_WAITS) - 1)]
        log(f"{what}; trying again in {wait} s")
        time.sleep(wait)
        try:
            self._connect()
        except Exception as e:          # (adb itself hung)
            log(f"adb reconnect failed: {e}")

    def _call(self, args, tries=None, timeout=ADB_TIMEOUT):
        """stdout of `adb -s serial <args>`; on a failure it reconnects and tries again, `tries`
        times in all (None: until the device answers). None when every try failed."""
        attempt = 0
        while True:
            try:
                r = subprocess.run(["adb", "-s", self.serial] + args, capture_output=True, timeout=timeout)
                if r.returncode == 0:
                    return r.stdout
                err = (r.stderr or r.stdout).decode("utf-8", "replace").strip()
            except subprocess.TimeoutExpired:
                err = f"no answer in {timeout} s"
            attempt += 1
            if tries is not None and attempt >= tries:
                log(f"adb {' '.join(args[:3])} failed ({err})")
                return None
            self._reconnect(attempt, f"adb {' '.join(args[:3])} failed ({err})")

    def _wait_online(self):
        """Return once the device state is "device" again (not offline / unauthorized)."""
        attempt = 0
        while True:
            try:
                r = subprocess.run(["adb", "-s", self.serial, "get-state"], capture_output=True,
                                   timeout=ADB_TIMEOUT)
                state = (r.stdout.strip() or r.stderr.strip()).decode("utf-8", "replace")
            except subprocess.TimeoutExpired:
                state = f"no answer in {ADB_TIMEOUT} s"
            if state == "device":
                return
            attempt += 1
            self._reconnect(attempt, f"adb device state: {state}")

    def _input(self, cmd, cancel=None):
        """Run an input command once. It is never sent again: a call that timed out may have
        run on the device all the same, and after an outage the screen may be another one.
        On a failure wait for the device, lift a finger the gesture may have left down
        (`cancel`), and raise AdbLost."""
        if self._call(["shell", cmd], tries=1) is not None:
            return
        self._wait_online()
        if cancel:
            self._call(["shell", cancel], tries=1)
        raise AdbLost(f"may not have been delivered: {cmd.split(';')[0]}")

    def _capture(self):
        """Full-resolution RGB array of the device screen."""
        attempt = 0
        while True:
            out = self._call(["exec-out", "screencap", "-p"], timeout=SHOT_TIMEOUT)
            # exec-out mixes screencap's stderr into the stream: with several displays a
            # warning comes ahead of the image
            start = out.find(PNG_MAGIC)
            try:
                if start < 0:
                    raise ValueError(out[:80])
                return np.array(Image.open(io.BytesIO(out[start:])).convert("RGB"))
            except Exception as e:
                # a broken PNG (the connection dropped mid-transfer): take it again
                attempt += 1
                self._reconnect(attempt, f"adb screenshot unreadable ({e})")

    # ------------------------------------------------------------------ screen
    def screenshot(self, *args, region=None, **kwargs):
        """Stand-in for pyautogui.screenshot: the device screen at the reference size.
        `region` (left, top, width, height) crops it, in reference physical px."""
        shot = self._capture()
        h, w = shot.shape[:2]
        img = cv2.resize(shot, (round(w / self.k), round(h / self.k)), interpolation=cv2.INTER_AREA)
        if region is not None:
            left, top, width, height = (int(round(v)) for v in region)
            img = img[top:top + height, left:left + width]
        return Image.fromarray(img)

    # ------------------------------------------------------------------ input
    def to_device(self, x, y):
        """Reference logical px -> device px."""
        f = REF_SFT * self.k
        return int(round(x * f)), int(round(y * f))

    def tap(self, x, y):
        """Down, held TAP_HOLD_MS, up (like click_at on the Mac): a swipe that does not move,
        one `input` process on every Android version."""
        dx, dy = self.to_device(x, y)
        self._input(f"input swipe {dx} {dy} {dx} {dy} {TAP_HOLD_MS}",
                    cancel=f"input motionevent {self.lift} {dx} {dy}" if self.motion else None)

    def drag(self, x1, y1, x2, y2, duration=0.7, steps=14, hold=0.3, press=0.1):
        """Press at (x1, y1), move to (x2, y2) in about `duration` s and release; like
        click.drag, it rests before the release so that the map does not fling on."""
        ax, ay = self.to_device(x1, y1)
        bx, by = self.to_device(x2, y2)
        if not self.motion:
            # Android 9 and older: `input swipe` cannot pause before the release; slow enough
            # that the release speed stays low
            dist = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            ms = int(max(press + duration + hold, dist / SLOW_SWIPE_SPEED) * 1000)
            self._input(f"input swipe {ax} {ay} {bx} {by} {ms}")
            return
        # one shell for the whole gesture. Each `input` call starts a new process
        # (input_start s), so the moves are few and the pause between them is what is left of
        # duration / n.
        n = max(2, min(steps, 6))
        gap = max(0.0, duration / n - self.input_start)
        cmds = [f"input motionevent DOWN {ax} {ay}", f"sleep {press:.2f}"]
        for i in range(1, n + 1):
            t = i / n
            cmds.append(f"input motionevent MOVE {round(ax + (bx - ax) * t)} {round(ay + (by - ay) * t)}")
            if gap > 0.01 and i < n:
                cmds.append(f"sleep {gap:.2f}")
        cmds += [f"sleep {hold:.2f}", f"input motionevent UP {bx} {by}"]
        self._input("; ".join(cmds), cancel=f"input motionevent {self.lift} {bx} {by}")
