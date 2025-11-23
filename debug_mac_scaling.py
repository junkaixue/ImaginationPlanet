"""
Debug Mac Scaling Factor

Tests what pyautogui.position() actually returns on Mac and verifies the scaling factor.
"""

import pyautogui
import platform
from common import get_scaling_factor
try:
    import Quartz
except:
    Quartz = None

print("=" * 70)
print("MAC SCALING FACTOR DEBUG")
print("=" * 70)

print(f"\nPlatform: {platform.system()}")

# Get scaling factor from common.py
sft = get_scaling_factor()
print(f"\nScaling factor from get_scaling_factor(): {sft}")

# Get display info if on Mac
if platform.system() == "Darwin" and Quartz:
    main_display_id = Quartz.CGMainDisplayID()
    display_mode = Quartz.CGDisplayCopyDisplayMode(main_display_id)
    
    pixel_width = Quartz.CGDisplayModeGetPixelWidth(display_mode)
    pixel_height = Quartz.CGDisplayModeGetPixelHeight(display_mode)
    point_width = Quartz.CGDisplayModeGetWidth(display_mode)
    point_height = Quartz.CGDisplayModeGetHeight(display_mode)
    
    print(f"\nDisplay Information:")
    print(f"  Physical pixels: {pixel_width} × {pixel_height}")
    print(f"  Logical points: {point_width} × {point_height}")
    print(f"  Calculated scaling: {pixel_width / point_width:.2f}")

print(f"\n" + "=" * 70)
print("PYAUTOGUI POSITION TEST")
print("=" * 70)
print("\nMove your mouse and watch the output.")
print("We'll test what coordinates pyautogui.position() returns.")
print("Press Ctrl+C to stop.")
print("")
print(f"{'PyAutoGUI Position':<30} | {'Notes':<40}")
print("-" * 70)

import time
import sys

try:
    last_pos = None
    while True:
        pos = pyautogui.position()
        
        if pos != last_pos:
            # Try to determine if these are physical or logical coords
            # by comparing to screen bounds
            if platform.system() == "Darwin" and Quartz:
                main_display_id = Quartz.CGMainDisplayID()
                display_mode = Quartz.CGDisplayCopyDisplayMode(main_display_id)
                pixel_width = Quartz.CGDisplayModeGetPixelWidth(display_mode)
                point_width = Quartz.CGDisplayModeGetWidth(display_mode)
                
                if pos.x > point_width:
                    coord_type = "Physical pixels"
                else:
                    coord_type = "Logical coordinates"
            else:
                coord_type = "Unknown"
            
            output = f"({pos.x:5d}, {pos.y:5d})  |  {coord_type}"
            sys.stdout.write(f"\r{output.ljust(70)}")
            sys.stdout.flush()
            
            last_pos = pos
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\n" + "=" * 70)
    print("CONCLUSIONS")
    print("=" * 70)
    
    if platform.system() == "Darwin" and Quartz:
        print("\nIf pyautogui coordinates are:")
        print(f"  - Less than {point_width}: They are LOGICAL coordinates")
        print(f"  - Up to {pixel_width}: They are PHYSICAL PIXELS")
        print("")
        print("Based on this, adjust coord_helper.py:")
        print("  - If LOGICAL: No conversion needed before calculating delta")
        print("  - If PHYSICAL: Divide by scaling factor first")
    
    print("")
