"""
Template Capture Tool

Captures small template images directly from the live screen so they match
the runtime resolution and scaling factor exactly.

Usage:
    python capture_template.py zone                 # interactive loop, saves to pics/<platform>/zone/
    python capture_template.py zone idle building   # capture these names in order
    python capture_template.py zone --full          # also save a full screenshot for reference

Flow for each template:
    1. Keep keyboard focus on this terminal, move the MOUSE over the game window.
    2. Hover the TOP-LEFT corner of the element, press Enter.
    3. Hover the BOTTOM-RIGHT corner of the element, press Enter.
    4. The crop is saved and its size printed.

Tip: capture a tight box around the element, excluding the changing background
where possible. Numbers and text that vary should be left out of the crop.
"""

import os
import sys
import time

import cv2
import numpy as np
import pyautogui

from common import get_scaling_factor
from platform_config import IMAGE_DIR


def grab_full():
    """Return a BGR screenshot in physical pixels."""
    shot = pyautogui.screenshot()
    return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)


def wait_point(prompt):
    input(prompt)
    pos = pyautogui.position()
    return pos.x, pos.y


def capture_one(name, out_dir, sft):
    x1, y1 = wait_point(f"[{name}] Hover TOP-LEFT corner, then press Enter... ")
    x2, y2 = wait_point(f"[{name}] Hover BOTTOM-RIGHT corner, then press Enter... ")

    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    if right - left < 4 or bottom - top < 4:
        print("  Box too small, skipped.")
        return None

    time.sleep(0.3)
    full = grab_full()
    px1, py1 = int(left * sft), int(top * sft)
    px2, py2 = int(right * sft), int(bottom * sft)
    crop = full[py1:py2, px1:px2]

    path = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(path, crop)
    print(f"  Saved {path}  size={crop.shape[1]}x{crop.shape[0]} px  "
          f"logical box=({left},{top})-({right},{bottom})  "
          f"center logical=({(left + right) / 2:.0f},{(top + bottom) / 2:.0f})")
    return path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if not args:
        print(__doc__)
        return

    sub_dir = args[0]
    names = args[1:]
    out_dir = os.path.join(IMAGE_DIR, sub_dir)
    os.makedirs(out_dir, exist_ok=True)
    sft = get_scaling_factor()

    print("=" * 70)
    print(f"TEMPLATE CAPTURE  ->  {out_dir}   (scaling factor {sft})")
    print("=" * 70)

    if "--full" in flags:
        path = os.path.join(out_dir, f"_full_{int(time.time())}.png")
        cv2.imwrite(path, grab_full())
        print(f"Full screenshot saved to {path}")

    if names:
        for name in names:
            capture_one(name, out_dir, sft)
        return

    print("Interactive mode. Enter a template name, or empty line to quit.")
    while True:
        name = input("\nTemplate name: ").strip()
        if not name:
            break
        capture_one(name, out_dir, sft)


if __name__ == "__main__":
    main()
