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
    
    # Check for command line arguments for Run Button coords
    rb_x_logical = None
    rb_y_logical = None
    
    if len(sys.argv) == 3:
        try:
            rb_x_logical = float(sys.argv[1])
            rb_y_logical = float(sys.argv[2])
            print(f"\nUsing provided Run Button coordinates:")
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
                            coords = line.split(':')[1].strip()
                            x, y = coords.split(',')
                            rb_x_logical = float(x.strip())
                            rb_y_logical = float(y.strip())
                            print(f"\nFound run_button in config: ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
                            break
                        except:
                            pass
    
    if rb_x_logical is None or rb_y_logical is None:
        # Find run button
        print("\nLooking for Run Button...")
        retry = 10
        rb_center = None
        
        while retry > 0 and rb_center is None:
            try:
                rb_center = get_center("RunButton", "Main")
                print(f"Found Run Button at: ({rb_center.x}, {rb_center.y}) [pixel coords]")
                # Convert to logical coordinates
                rb_x_logical = rb_center.x / sft
                rb_y_logical = rb_center.y / sft
                print(f"   Logical coordinates: ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
            except:
                print(f"Run Button not found, retrying... ({retry} attempts left)")
                retry -= 1
                time.sleep(1)
        
        if rb_center is None:
            print("Failed to find Run Button. Make sure the game window is visible.")
            print("\nAlternatively, provide Run Button coordinates:")
            print(f"  python coord_helper.py <x> <y>")
            return
    
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
            # Get current mouse position (physical pixels on both Mac and Windows)
            # pyautogui.position() returns screen coordinates that need scaling factor conversion
            current_pos = pyautogui.position()
            
            # Only print if position changed
            if last_pos != current_pos:
                # Convert to logical coordinates (works on both Mac and Windows)
                # Mac: handles Retina display scaling
                # Windows: handles display scaling (125%, 150%, etc.)
                current_x_logical = current_pos.x / sft
                current_y_logical = current_pos.y / sft
                
                # Calculate delta in logical coordinates
                delta_x = current_x_logical - rb_x_logical
                delta_y = current_y_logical - rb_y_logical
                
                # Use sys.stdout for robust cross-platform real-time output
                # Pad output to 70 chars to overwrite previous line completely (Windows compatibility)
                output = f"Mouse: ({current_x_logical:5.0f}, {current_y_logical:5.0f})  |  " \
                         f"Delta: (Δx={delta_x:+6.0f}, Δy={delta_y:+6.0f})"
                # Pad to ensure previous line content is fully overwritten
                output = output.ljust(70)
                sys.stdout.write(f"\r{output}")
                sys.stdout.flush()
                
                last_pos = current_pos
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Coordinate Helper stopped.")
        print("=" * 70)


if __name__ == "__main__":
    main()
