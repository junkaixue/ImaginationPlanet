"""
Test PyAutoGUI Coordinate System

Quick test to understand what coordinate system pyautogui uses.
"""

import pyautogui
import platform
from common import get_scaling_factor

print("=" * 70)
print("PYAUTOGUI COORDINATE SYSTEM TEST")
print("=" * 70)

sft = get_scaling_factor()
print(f"\nPlatform: {platform.system()}")
print(f"Scaling factor: {sft}")

# Get screen size from pyautogui
screen_width, screen_height = pyautogui.size()
print(f"\npyautogui.size(): {screen_width} × {screen_height}")

if platform.system() == "Darwin":
    try:
        import Quartz
        main_display_id = Quartz.CGMainDisplayID()
        display_mode = Quartz.CGDisplayCopyDisplayMode(main_display_id)
        
        pixel_width = Quartz.CGDisplayModeGetPixelWidth(display_mode)
        pixel_height = Quartz.CGDisplayModeGetPixelHeight(display_mode)
        point_width = Quartz.CGDisplayModeGetWidth(display_mode)
        point_height = Quartz.CGDisplayModeGetHeight(display_mode)
        
        print(f"\nActual display:")
        print(f"  Physical pixels: {pixel_width} × {pixel_height}")
        print(f"  Logical points: {point_width} × {point_height}")
        
        print(f"\nComparison:")
        if screen_width == pixel_width:
            print(f"  ✅ pyautogui.size() matches PHYSICAL PIXELS")
            print(f"  → pyautogui.position() likely returns PHYSICAL PIXELS")
            print(f"  → We should NOT divide by scaling factor")
        elif screen_width == point_width:
            print(f"  ✅ pyautogui.size() matches LOGICAL POINTS")
            print(f"  → pyautogui.position() likely returns LOGICAL COORDINATES")
            print(f"  → We SHOULD use scaling for deltas")
        else:
            print(f"  ⚠️  pyautogui.size() doesn't match either!")
            print(f"  → Unclear what coordinate system is being used")
    except:
        print("\n⚠️  Could not get display info from Quartz")

print("\n" + "=" * 70)
