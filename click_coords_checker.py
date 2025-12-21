"""
Test Click Coordinates

Tests the card area coordinates from Mac config by:
1. Reading run button and card area from config
2. Moving mouse to top-left, then bottom-right
3. Clicking at each position to verify they're correct
"""

import time
import pyautogui
import os
import platform
from common import get_scaling_factor

def main():
    print("=" * 70)
    print("TEST CLICK COORDINATES")
    print("=" * 70)
    
    # Get scaling factor
    sft = get_scaling_factor()
    is_mac = (platform.system() == "Darwin")
    
    print(f"\n✅ Platform: {platform.system()}")
    print(f"✅ Scaling factor: {sft}")
    
    # Read run button and card area from config file
    config_file = "cood_mac.cfg" if is_mac else "cood_win.cfg"
    config_path = os.path.join("configs", config_file)
    
    print(f"\nReading from: {config_path}")
    
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
    
    # Get run button from config (physical pixels)
    rb_x, rb_y = coords['run_button']
    
    print(f"\nRun Button (from config):")
    print(f"  Coordinates: ({rb_x:.0f}, {rb_y:.0f}) [physical pixels]")
    
    # Get card area coordinates from config
    if 'pair_top_left' not in coords or 'pair_bottom_right' not in coords:
        print("❌ ERROR: pair_top_left or pair_bottom_right not found in config!")
        print("Make sure they exist in configs/cood_mac.cfg")
        return
    
    # Get deltas from config (physical pixels)
    delta_tl_x, delta_tl_y = coords['pair_top_left']
    delta_br_x, delta_br_y = coords['pair_bottom_right']
    
    print(f"\nCard Area from config:")
    print(f"  Top-left delta: ({delta_tl_x:+.0f}, {delta_tl_y:+.0f})")
    print(f"  Bottom-right delta: ({delta_br_x:+.0f}, {delta_br_y:+.0f})")
    
    # Calculate absolute coordinates (no scaling needed - all physical pixels)
    tl_x = rb_x + delta_tl_x
    tl_y = rb_y + delta_tl_y
    br_x = rb_x + delta_br_x
    br_y = rb_y + delta_br_y
    
    print(f"  Absolute coordinates:")
    print(f"    Top-left: ({tl_x:.1f}, {tl_y:.1f})")
    print(f"    Bottom-right: ({br_x:.1f}, {br_y:.1f})")
    
    width = br_x - tl_x
    height = br_y - tl_y
    print(f"  Size: {width:.0f} × {height:.0f} pixels")
    
    print("\n" + "=" * 70)
    print("INTERACTIVE TEST")
    print("=" * 70)
    print("\nThis will move your mouse and click at the card area corners.")
    print("Watch your screen to verify the mouse goes to the right places.")
    print("")
    
    input("Press ENTER to start test...")
    
    # Test 1: Click top-left
    print("\n1. Testing TOP-LEFT corner...")
    print(f"   Moving to ({tl_x:.1f}, {tl_y:.1f})...")
    time.sleep(1)
    
    pyautogui.moveTo(tl_x, tl_y, duration=0.5)
    print("   Mouse moved. Clicking in 1 second...")
    time.sleep(1)
    pyautogui.click()
    print("   ✓ Clicked top-left")
    
    time.sleep(1)
    
    # Test 2: Click bottom-right
    print("\n2. Testing BOTTOM-RIGHT corner...")
    print(f"   Moving to ({br_x:.1f}, {br_y:.1f})...")
    time.sleep(1)
    
    pyautogui.moveTo(br_x, br_y, duration=0.5)
    print("   Mouse moved. Clicking in 1 second...")
    time.sleep(1)
    pyautogui.click()
    print("   ✓ Clicked bottom-right")
    
    time.sleep(1)
    
    # Test 3: Draw the rectangle by moving around it
    print("\n3. Tracing card area rectangle...")
    print("   (Watch the mouse outline the card area)")
    time.sleep(2)
    
    # Top-left
    pyautogui.moveTo(tl_x, tl_y, duration=0.5)
    time.sleep(0.3)
    
    # Top-right
    pyautogui.moveTo(br_x, tl_y, duration=0.5)
    time.sleep(0.3)
    
    # Bottom-right
    pyautogui.moveTo(br_x, br_y, duration=0.5)
    time.sleep(0.3)
    
    # Bottom-left
    pyautogui.moveTo(tl_x, br_y, duration=0.5)
    time.sleep(0.3)
    
    # Back to top-left
    pyautogui.moveTo(tl_x, tl_y, duration=0.5)
    print("   ✓ Rectangle traced")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nDid the mouse clicks and rectangle match your card area?")
    print("")
    print("✅ YES - Your coordinates are correct!")
    print("❌ NO  - Run card_area_finder.py to get correct coordinates")
    print("")
    print("=" * 70)


if __name__ == "__main__":
    main()
