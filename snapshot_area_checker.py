"""
Test Snapshot Area

Takes a test snapshot and shows exactly what coordinates are being used.
Helps debug if the card area is captured correctly.
"""

import cv2
import numpy as np
import pyautogui
import platform
import time
import os
from common import get_scaling_factor
from platform_config import get_image_path


def main():
    print("=" * 70)
    print("SNAPSHOT AREA TEST")
    print("=" * 70)
    
    platform_name = platform.system()
    print(f"\nPlatform: {platform_name}")
    
    # Get scaling factor
    sft = get_scaling_factor()
    is_mac = (platform_name == "Darwin")
    print(f"Scaling factor: {sft}")
    
    # Read run button from config file
    config_file = "cood_mac.cfg" if is_mac else "cood_win.cfg"
    config_path = os.path.join("configs", config_file)
    
    print(f"\nStep 1: Reading from config: {config_path}")
    
    coords = {}
    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                name, values = line.split(':')
                name = name.strip()
                values = values.strip().rstrip('.')
                x, y = values.split(',')
                coords[name] = (float(x.strip()), float(y.strip()))
            except:
                pass
    
    if 'run_button' not in coords:
        print("❌ ERROR: run_button not found in config!")
        return
    
    # Get run button (physical pixels from config)
    rb_x, rb_y = coords['run_button']
    
    print(f"\nRun Button (from config):")
    print(f"  Coordinates: ({rb_x:.0f}, {rb_y:.0f}) [physical pixels]")
    
    # Get card area from config
    print("\nStep 2: Getting card area coordinates from config...")
    
    if 'pair_top_left' not in coords or 'pair_bottom_right' not in coords:
        print("❌ ERROR: pair_top_left or pair_bottom_right not found in config!")
        return
    
    # Get deltas from config (physical pixels)
    delta_tl_x, delta_tl_y = coords['pair_top_left']
    delta_br_x, delta_br_y = coords['pair_bottom_right']
    
    # Calculate absolute coordinates (no scaling - all physical pixels)
    tl_x_abs = rb_x + delta_tl_x
    tl_y_abs = rb_y + delta_tl_y
    br_x_abs = rb_x + delta_br_x
    br_y_abs = rb_y + delta_br_y
    
    top_left = (tl_x_abs, tl_y_abs)
    bottom_right = (br_x_abs, br_y_abs)
    
    # Get the defined card area boundaries
    tl_x = int(top_left[0])
    tl_y = int(top_left[1])
    br_x = int(bottom_right[0])
    br_y = int(bottom_right[1])
    
    print(f"\nDefined card area (from config):")
    print(f"  Top-left: ({tl_x}, {tl_y})")
    print(f"  Bottom-right: ({br_x}, {br_y})")
    
    # Calculate the card area dimensions
    card_width = br_x - tl_x
    card_height = br_y - tl_y
    print(f"  Card area size: {card_width}x{card_height}")
    
    if card_width <= 0 or card_height <= 0:
        print("❌ ERROR: Invalid card area size!")
        print("   Width and height must be positive.")
        print("   Check your pair_top_left and pair_bottom_right coordinates.")
        return
    
    # Platform-specific extension
    if is_mac:
        # Mac: Use fixed extension (based on coord_helper measurements)
        extend_left = 39
        extend_up = 58
        extend_right = 38
        extend_down = 50
        print(f"\nMac: Using fixed extension around card area")
    else:
        # Windows: Use half dimensions for extension
        extend_left = card_width // 2
        extend_up = card_height // 2
        extend_right = card_width // 2
        extend_down = card_height // 2
        print(f"\nWindows: Using half-dimension extension")
    
    print(f"Extension: L={extend_left}, U={extend_up}, R={extend_right}, D={extend_down}")
    
    # Calculate extended snapshot area
    x1 = tl_x - extend_left    # Extend left
    y1 = tl_y - extend_up      # Extend up
    x2 = br_x + extend_right   # Extend right
    y2 = br_y + extend_down    # Extend down
    
    width = x2 - x1
    height = y2 - y1
    
    print(f"\nExtended snapshot area:")
    print(f"  Top-left: ({x1}, {y1})")
    print(f"  Bottom-right: ({x2}, {y2})")
    print(f"  Size: {width}x{height}")
    
    # Take screenshot
    print("\nStep 3: Taking screenshot in 3 seconds...")
    print("Make sure the card matching game is visible!")
    time.sleep(3)
    
    print("Taking screenshot...")
    
    try:
        screenshot = pyautogui.screenshot(region=(x1, y1, width, height))
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Save to debug location
        debug_path = get_image_path("test_card_area.png")
        cv2.imwrite(debug_path, screenshot_cv)
        
        print(f"✅ Screenshot saved to: {debug_path}")
        print(f"   Size: {screenshot_cv.shape[1]}x{screenshot_cv.shape[0]} pixels")
        
    except Exception as e:
        print(f"❌ ERROR taking screenshot: {e}")
        return
    
    # Also take a full screenshot with rectangle overlay for reference
    print("\nStep 4: Taking full screenshot with areas marked...")
    time.sleep(1)
    
    full_screenshot = pyautogui.screenshot()
    full_cv = cv2.cvtColor(np.array(full_screenshot), cv2.COLOR_RGB2BGR)
    
    # Draw original card area in blue (what's in config)
    cv2.rectangle(full_cv, (tl_x, tl_y), (br_x, br_y), (255, 0, 0), 2)
    cv2.putText(full_cv, f"Card Area ({card_width}x{card_height})", (tl_x, tl_y - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    
    # Draw extended snapshot area in green (what gets captured)
    cv2.rectangle(full_cv, (x1, y1), (x2, y2), (0, 255, 0), 3)
    cv2.putText(full_cv, f"Snapshot Area ({width}x{height})", (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Also mark run button
    rb_x_display = int(rb_x)
    rb_y_display = int(rb_y)
    cv2.circle(full_cv, (rb_x_display, rb_y_display), 10, (0, 0, 255), -1)
    cv2.putText(full_cv, "Run Button", (rb_x_display + 15, rb_y_display),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    full_debug_path = get_image_path("test_full_screen_marked.png")
    cv2.imwrite(full_debug_path, full_cv)
    
    print(f"✅ Full screenshot saved to: {full_debug_path}")
    print(f"   Blue (inner) = Card area from config")
    print(f"   Green (outer) = Extended snapshot area")
    print(f"   Red dot = Run button")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nWhat to check:")
    print(f"1. Open {debug_path}")
    print("   - This shows the extended snapshot area (with extra context)")
    print("   - Should contain all the cards plus some surrounding area")
    print("")
    print(f"2. Open {full_debug_path}")
    print("   - Shows the entire screen with areas marked:")
    print("     • Blue (inner) = Card area from config (pair_top_left to pair_bottom_right)")
    print("     • Green (outer) = Extended snapshot area (blue area + half width/height on each side)")
    print("     • Red dot = Run button")
    print("")
    print("The snapshot is extended to capture context around the cards.")
    print("Extension = half of card width left/right, half of card height up/down")
    print("")
    print("If the areas are wrong:")
    print("  - Update pair_top_left and pair_bottom_right in configs/cood_mac.cfg")
    print("  - Use coord_helper.py to find the correct delta coordinates")
    print("=" * 70)


if __name__ == "__main__":
    main()
