"""
Coordinate Helper Tool

This tool helps you find relative coordinates from the Run Button.
Continuously prints the delta (x, y) from the run button to current mouse position.
Useful for finding where to take screenshots of game elements.

Usage:
    python coord_helper.py
    
Then move your mouse to the element you want to capture and read the delta coordinates.
Press Ctrl+C to exit.
"""

import time
import pyautogui
from common import get_center, get_scaling_factor
import platform


def main():
    print("=" * 70)
    print("COORDINATE HELPER - Find Delta from Run Button")
    print("=" * 70)
    
    # Get scaling factor
    sft = get_scaling_factor()
    platform_name = platform.system()
    
    print(f"\nPlatform: {platform_name}")
    print(f"Scaling Factor: {sft}")
    
    # Find run button
    print("\nLooking for Run Button...")
    retry = 10
    rb_center = None
    
    while retry > 0 and rb_center is None:
        try:
            rb_center = get_center("RunButton", "Main")
            print(f"✅ Found Run Button at: ({rb_center.x}, {rb_center.y}) [pixel coords]")
            # Convert to logical coordinates
            rb_x = rb_center.x / sft
            rb_y = rb_center.y / sft
            print(f"   Logical coordinates: ({rb_x:.1f}, {rb_y:.1f})")
        except:
            print(f"Run Button not found, retrying... ({retry} attempts left)")
            retry -= 1
            time.sleep(1)
    
    if rb_center is None:
        print("❌ Failed to find Run Button. Make sure the game window is visible.")
        return
    
    # Convert to logical coordinates for run button
    rb_x_logical = rb_center.x / sft
    rb_y_logical = rb_center.y / sft
    
    print("\n" + "=" * 70)
    print("READY! Move your mouse to any element in the game.")
    print("The tool will show you the relative position from the Run Button.")
    print("Press Ctrl+C to exit.")
    print("=" * 70 + "\n")
    
    print(f"{'Current Mouse Position':<30} | {'Delta from RunButton':<30}")
    print("-" * 70)
    
    try:
        last_pos = None
        while True:
            # Get current mouse position
            current_pos = pyautogui.position()
            
            # Only print if position changed
            if last_pos != current_pos:
                # Calculate delta
                delta_x = current_pos.x - rb_x_logical
                delta_y = current_pos.y - rb_y_logical
                
                # Print position info
                print(f"Mouse: ({current_pos.x:5.0f}, {current_pos.y:5.0f})  |  "
                      f"Delta: (Δx={delta_x:+6.0f}, Δy={delta_y:+6.0f})", end="\r")
                
                last_pos = current_pos
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Coordinate Helper stopped.")
        print("=" * 70)


if __name__ == "__main__":
    main()
