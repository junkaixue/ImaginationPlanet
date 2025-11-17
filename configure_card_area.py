"""
Card Area Configuration Helper
Helps you find and configure the pair_top_left and pair_bottom_right coordinates.

Usage:
    python configure_card_area.py                # Load from config, or auto-scan if not found
    python configure_card_area.py 2624 1169     # Use provided Run Button coordinates
"""
import pyautogui
import time
import sys
from log_helper import log
from config_coords import ConfigCoords


def find_run_button(rb_x_input=None, rb_y_input=None):
    """Find or use provided Run Button position."""
    if rb_x_input is not None and rb_y_input is not None:
        log(f"Using provided Run Button coordinates: ({rb_x_input:.1f}, {rb_y_input:.1f})")
        return (rb_x_input, rb_y_input)
    
    log("Looking for Run Button...")
    config = ConfigCoords()
    
    if config.rb:
        rb_x = config.rb.x / config.sft
        rb_y = config.rb.y / config.sft
        log(f"Run Button found at logical coordinates: ({rb_x:.1f}, {rb_y:.1f})")
        return (rb_x, rb_y)
    else:
        log("ERROR: Could not find Run Button")
        return None


def get_mouse_position_relative_to_rb(rb_pos):
    """
    Get current mouse position relative to Run Button.
    
    Args:
        rb_pos: (x, y) tuple of Run Button logical position
    """
    current_pos = pyautogui.position()
    
    delta_x = current_pos[0] - rb_pos[0]
    delta_y = current_pos[1] - rb_pos[1]
    
    return (delta_x, delta_y)


def main():
    """Interactive helper to configure card area coordinates."""
    log("="*70)
    log("CARD AREA CONFIGURATION HELPER")
    log("="*70)
    log("")
    log("This tool helps you find the coordinates for pair_top_left and")
    log("pair_bottom_right to configure the card matching area.")
    log("")
    
    # Check for command line arguments for Run Button coords
    rb_x_input = None
    rb_y_input = None
    
    if len(sys.argv) == 3:
        try:
            rb_x_input = float(sys.argv[1])
            rb_y_input = float(sys.argv[2])
        except ValueError:
            log("ERROR: Invalid coordinates provided. Must be numbers.")
            log("Usage: python configure_card_area.py <x> <y>")
            return
    elif len(sys.argv) == 1:
        # Try to read run_button from config file first
        import platform
        import os
        is_mac = (platform.system() == "Darwin")
        config_file = "cood_mac.cfg" if is_mac else "cood_win.cfg"
        config_path = os.path.join("configs", config_file)
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('run_button:'):
                        try:
                            coords = line.split(':')[1].strip()
                            x, y = coords.split(',')
                            rb_x_input = float(x.strip())
                            rb_y_input = float(y.strip())
                            log(f"Found run_button in config: ({rb_x_input:.1f}, {rb_y_input:.1f})")
                            break
                        except:
                            pass
    
    log("INSTRUCTIONS:")
    log("1. Make sure the card matching game is visible on screen")
    if rb_x_input is None:
        log("2. The Run Button should be visible (or provide coordinates as args)")
    else:
        log("2. Using provided Run Button coordinates")
    log("3. You will move your mouse to specific corners")
    log("4. The tool will calculate the relative coordinates")
    log("")
    
    # Find Run Button
    rb_pos = find_run_button(rb_x_input, rb_y_input)
    if not rb_pos:
        log("Cannot continue without Run Button. Please make sure game is visible.")
        return
    
    log("")
    log("="*70)
    log("Step 1: Find TOP-LEFT corner of card area")
    log("="*70)
    log("Move your mouse to the TOP-LEFT corner of the first card (card 0)")
    log("This should be the top-left of the entire card grid area")
    log("")
    
    for i in range(5, 0, -1):
        log(f"Recording position in {i} seconds...")
        time.sleep(1)
    
    top_left_delta = get_mouse_position_relative_to_rb(rb_pos)
    log(f"✓ Top-left recorded: Δx={top_left_delta[0]:+.1f}, Δy={top_left_delta[1]:+.1f}")
    
    log("")
    log("="*70)
    log("Step 2: Find BOTTOM-RIGHT corner of card area")
    log("="*70)
    log("Move your mouse to the BOTTOM-RIGHT corner of the last card (card 29)")
    log("This should be the bottom-right of the entire card grid area")
    log("")
    
    for i in range(5, 0, -1):
        log(f"Recording position in {i} seconds...")
        time.sleep(1)
    
    bottom_right_delta = get_mouse_position_relative_to_rb(rb_pos)
    log(f"✓ Bottom-right recorded: Δx={bottom_right_delta[0]:+.1f}, Δy={bottom_right_delta[1]:+.1f}")
    
    log("")
    log("="*70)
    log("CONFIGURATION RESULTS")
    log("="*70)
    log("")
    log("Add these lines to your config file:")
    log("(configs/cood_win.cfg for Windows, configs/cood_mac.cfg for macOS)")
    log("")
    log(f"pair_top_left: {top_left_delta[0]:.0f}, {top_left_delta[1]:.0f}")
    log(f"pair_bottom_right: {bottom_right_delta[0]:.0f}, {bottom_right_delta[1]:.0f}")
    log("")
    log("="*70)
    log("")
    log("Calculated area dimensions:")
    width = bottom_right_delta[0] - top_left_delta[0]
    height = bottom_right_delta[1] - top_left_delta[1]
    log(f"  Width:  {width:.1f} pixels")
    log(f"  Height: {height:.1f} pixels")
    log(f"  Ratio:  {width/height:.2f} (should be approximately 6/5 = 1.2 for 5x6 grid)")
    log("")
    
    # Verify
    if abs(width / height - 1.2) > 0.3:
        log("⚠ WARNING: Area ratio seems unusual for a 5x6 grid")
        log("  Double-check your corner positions")
    else:
        log("✓ Area ratio looks good!")
    
    log("")
    log("="*70)
    log("NEXT STEPS:")
    log("1. Copy the config lines above")
    log("2. Add them to your config file")
    log("3. Take a screenshot and save as pics/img.png")
    log("4. Run: python auto_card_matcher.py --dry-run")
    log("5. Verify the click positions look correct")
    log("6. Run: python auto_card_matcher.py")
    log("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\nConfiguration cancelled by user")
    except Exception as e:
        log(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
