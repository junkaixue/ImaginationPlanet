"""
Zone Explore diagnostics.

    python zone_check.py                      # live screen: confidence of every Z template + one dry scan
    python zone_check.py --image pics/mac/zone/_full_xxx.png   # same, against a saved full screenshot

Use it after capturing templates to see which ones match (>= 0.8) before running the bot.
"""
import argparse
import os

import cv2
import numpy as np
import pyautogui
from PIL import Image

import common
from common import single_find_map


def use_image(path):
    """Make every screenshot in the process return this file (physical pixels)."""
    img = Image.open(path).convert("RGB")
    pyautogui.screenshot = lambda *a, **k: img
    common.pyautogui.screenshot = pyautogui.screenshot


def check_templates(gray):
    print(f"{'template':14s} {'file':38s} {'size':9s} conf")
    for key in sorted(k for k in single_find_map if k.startswith("Z")):
        path = single_find_map[key]
        t = cv2.imread(path, 0) if os.path.exists(path) else None
        if t is None:
            print(f"{key:14s} {path:38s} MISSING")
            continue
        r = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        mark = "OK " if mx >= 0.8 else "   "
        print(f"{key:14s} {path:38s} {t.shape[1]}x{t.shape[0]:<5d} {mark}{mx:.3f} at {loc}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", help="Run against this screenshot instead of the live screen")
    args = ap.parse_args()
    if args.image:
        use_image(args.image)
    gray = common.screen_shot()
    print(f"screen {gray.shape[1]}x{gray.shape[0]}")
    check_templates(gray)

    from zone_explore import ZoneExplore
    z = ZoneExplore(dry_run=True)
    z.calibrate_scale()
    print("\n--- dry scan ---")
    print("window scale:", round(z.win_scale, 3), "zone:", z.read_zone())
    print("on_map:", z.on_map())
    z.scan_ships()
    z.read_actions()
    z.scan_resources()
