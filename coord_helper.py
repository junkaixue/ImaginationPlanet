"""
Coordinate Helper Tool

This tool helps you find relative coordinates from the Run Button.
Continuously prints the delta (x, y) from the run button to current mouse position.
Useful for finding where to take screenshots of game elements.

Usage:
    python coord_helper.py                    # Load from config, or auto-scan if not found
    python coord_helper.py 2624 1169          # Use provided Run Button coordinates
    
Then move your mouse to the element you want to capture and read the delta coordinates.
Press Ctrl+C to exit.
"""

import time
import sys
import pyautogui
import platform
from common import get_center, get_scaling_factor


def main():
    print("=" * 70)
    print("COORDINATE HELPER - Find Delta from Run Button")
    print("=" * 70)
    
    # Get scaling factor
    sft = get_scaling_factor()
    platform_name = platform.system()
    
    print(f"\nPlatform: {platform_name}")
    print(f"Scaling Factor: {sft}")
    
    # Check for command line arguments for Run Button coords
    rb_x_logical = None
    rb_y_logical = None
    
    if len(sys.argv) == 3:
        try:
            # Command line args are in logical coordinates
            rb_x_logical = float(sys.argv[1])
            rb_y_logical = float(sys.argv[2])
            print(f"\nUsing provided Run Button coordinates (logical):")
            print(f"   ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
        except ValueError:
            print("\nERROR: Invalid coordinates provided. Must be numbers.")
            print(f"Usage: python coord_helper.py <x> <y>")
            return
    elif len(sys.argv) == 1:
        # Try to read run_button from config file first
        import os
        config_file = "cood_mac.cfg" if platform_name == "Darwin" else "cood_win.cfg"
        config_path = os.path.join("configs", config_file)
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('run_button:'):
                        try:
                            coords = line.split(':')[1].strip().rstrip('.')
                            x, y = coords.split(',')
                            rb_x_physical = float(x.strip())
                            rb_y_physical = float(y.strip())
                            
                            # Config stores physical pixels
                            # Convert to logical for pyautogui.position() comparison
                            rb_x_logical = rb_x_physical / sft
                            rb_y_logical = rb_y_physical / sft
                            
                            print(f"\nFound run_button in config:")
                            print(f"  Physical pixels: ({rb_x_physical:.1f}, {rb_y_physical:.1f})")
                            print(f"  Logical coords:  ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
                            break
                        except:
                            pass
    
    if rb_x_logical is None or rb_y_logical is None:
        # Find run button using template matching
        print("\nLooking for Run Button...")
        retry = 10
        rb_center = None
        
        while retry > 0 and rb_center is None:
            try:
                rb_center = get_center("RunButton", "Main")
                # get_center now returns logical coordinates (after scaling factor division)
                rb_x_logical = rb_center[0]
                rb_y_logical = rb_center[1]
                
                rb_x_physical = rb_x_logical * sft
                rb_y_physical = rb_y_logical * sft
                
                print(f"Found Run Button:")
                print(f"  Logical coords:  ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
                print(f"  Physical pixels: ({rb_x_physical:.1f}, {rb_y_physical:.1f})")
            except:
                print(f"Run Button not found, retrying... ({retry} attempts left)")
                retry -= 1
                time.sleep(1)
        
        if rb_center is None:
            print("Failed to find Run Button. Make sure the game window is visible.")
            print("\nAlternatively, provide Run Button coordinates (logical):")
            print(f"  python coord_helper.py <x> <y>")
            return
    
    print("\n" + "=" * 70)
    print("READY! Move your mouse to any element in the game.")
    print("The tool will show you the relative position from the Run Button.")
    print("Press Ctrl+C to exit.")
    print("=" * 70 + "\n")
    
    is_mac = (platform_name == "Darwin")
    print(f"{'Mouse Position':<30} | {'Delta for Config':<30}")
    print("-" * 70)
    
    try:
        last_pos = None
        while True:
            # Get current mouse position
            # pyautogui.position() returns logical coordinates on Mac (e.g., 1280, 832)
            current_pos = pyautogui.position()
            
            # Only print if position changed
            if last_pos != current_pos:
                # Current position in logical coordinates
                current_x_logical = current_pos.x
                current_y_logical = current_pos.y
                
                # Calculate delta in logical coordinates
                delta_x_logical = current_x_logical - rb_x_logical
                delta_y_logical = current_y_logical - rb_y_logical
                
                # Convert delta to physical pixels for config file
                # Config file stores physical pixel deltas
                delta_x_config = int(delta_x_logical * sft)
                delta_y_config = int(delta_y_logical * sft)
                
                # Show both logical position and physical delta for config
                output = f"Logical: ({current_x_logical:6.1f}, {current_y_logical:6.1f})  |  " \
                         f"Config: (Δx={delta_x_config:+6d}, Δy={delta_y_config:+6d})"
                
                # Pad to ensure previous line content is fully overwritten
                output = output.ljust(80)
                sys.stdout.write(f"\r{output}")
                sys.stdout.flush()
                
                last_pos = current_pos
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Coordinate Helper stopped.")
        print("=" * 70)
        print("\n📝 How to use the Delta values:")
        print("")
        print("   The 'Config' delta values are in PHYSICAL PIXELS")
        print("   Add them to your config file (cood_mac.cfg or cood_win.cfg)")
        print("")
        if platform_name == "Darwin":
            print(f"   Mac Resolution: 2560×1664 logical ({int(2560*sft)}×{int(1664*sft)} physical)")
            print(f"   Scaling Factor: {sft}")
        print("")


if __name__ == "__main__":
    main()
