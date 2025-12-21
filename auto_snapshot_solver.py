"""
Automatic Snapshot and Solver
Automatically takes screenshots and waits for cards to flip back before solving
"""
import cv2
import numpy as np
import time
import os
import platform
import pyautogui
from log_helper import log
from config_coords import ConfigCoords
from template_card_matcher import TemplateCardMatcher
from mac_card_matcher import MacCardMatcher
from common import single_find_with_path
from platform_config import get_image_path


class AutoSnapshotSolver:
    def __init__(self):
        """Initialize the auto snapshot solver."""
        self.config = None
        self.card_area = None
        self.flipback_template = get_image_path("flipback.png")
        
    def load_config(self):
        """Load configuration and calculate card area."""
        log("Loading configuration...")
        
        # Check if run_button absolute coords are in config
        import platform
        config_file = "cood_mac.cfg" if platform.system() == "Darwin" else "cood_win.cfg"
        config_path = os.path.join("configs", config_file)
        
        run_button_abs = None
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('run_button:'):
                        try:
                            coords = line.split(':')[1].strip()
                            x, y = coords.split(',')
                            run_button_abs = (float(x.strip()), float(y.strip()))
                            log(f"Found run_button in config: ({run_button_abs[0]:.1f}, {run_button_abs[1]:.1f})")
                            break
                        except:
                            pass
        
        if run_button_abs:
            self.config = ConfigCoords(mock_rb=(int(run_button_abs[0]), int(run_button_abs[1])))
        else:
            self.config = ConfigCoords()
        
        # Get card area coordinates from config file
        # Works on both Windows and Mac - uses physical pixels throughout
        top_left = self.config.get_coord("pair_top_left")
        bottom_right = self.config.get_coord("pair_bottom_right")
        
        if top_left is None or bottom_right is None:
            log("ERROR: pair_top_left or pair_bottom_right not found in config!")
            log("Make sure these entries exist in your platform config file:")
            log("  Windows: configs/cood_win.cfg")
            log("  Mac: configs/cood_mac.cfg")
            return False
        
        # Get the defined card area boundaries
        tl_x = int(top_left[0])
        tl_y = int(top_left[1])
        br_x = int(bottom_right[0])
        br_y = int(bottom_right[1])
        
        log(f"Defined card area (from config):")
        log(f"  Top-left: ({tl_x}, {tl_y})")
        log(f"  Bottom-right: ({br_x}, {br_y})")
        
        # Calculate the card area dimensions
        card_width = br_x - tl_x
        card_height = br_y - tl_y
        log(f"  Card area size: {card_width}x{card_height}")
        
        # Platform-specific extension
        import platform
        if platform.system() == "Darwin":
            # Mac: Use fixed extension (about 40-50 pixels in each direction)
            # Based on user measurements from coord_helper
            extend_left = 39
            extend_up = 58
            extend_right = 38
            extend_down = 50
            log(f"Mac: Using fixed extension around card area")
        else:
            # Windows: Use half dimensions for extension
            extend_left = card_width // 2
            extend_up = card_height // 2
            extend_right = card_width // 2
            extend_down = card_height // 2
            log(f"Windows: Using half-dimension extension")
        
        log(f"Extension: L={extend_left}, U={extend_up}, R={extend_right}, D={extend_down}")
        
        # Calculate extended snapshot area
        x1 = tl_x - extend_left    # Extend left
        y1 = tl_y - extend_up      # Extend up
        x2 = br_x + extend_right   # Extend right
        y2 = br_y + extend_down    # Extend down
        
        width = x2 - x1
        height = y2 - y1
        
        self.card_area = {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'width': width,
            'height': height
        }
        
        log(f"Extended snapshot area:")
        log(f"  Top-left: ({x1}, {y1})")
        log(f"  Bottom-right: ({x2}, {y2})")
        log(f"  Size: {width}x{height}")
        
        return True
        
    def take_snapshot(self, save_path=None):
        """Take a screenshot of the card area."""
        log(f"Taking snapshot of card area...")
        
        # card_area is already in physical pixels
        # pyautogui.screenshot on Mac:
        #   - Expects logical coordinates as input
        #   - BUT captures at physical resolution (Retina 2x)
        # So we convert physical → logical for the region parameter
        # But the resulting image will be at physical resolution!
        from common import get_scaling_factor
        sft = get_scaling_factor()
        
        region_x = int(self.card_area['x1'] / sft)
        region_y = int(self.card_area['y1'] / sft)
        region_w = int(self.card_area['width'] / sft)
        region_h = int(self.card_area['height'] / sft)
        
        log(f"  Card area (physical pixels): ({self.card_area['x1']}, {self.card_area['y1']}) {self.card_area['width']}x{self.card_area['height']}")
        log(f"  Region param (logical):      ({region_x}, {region_y}) {region_w}x{region_h}")
        
        # Take screenshot of the specific region
        screenshot = pyautogui.screenshot(region=(region_x, region_y, region_w, region_h))
        
        # Convert PIL image to OpenCV format
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # On Mac Retina, pyautogui captures at logical resolution, but templates are physical
        # So we need to scale UP the snapshot to match template resolution
        # Note: On Windows, sft is typically 1.0 (96 DPI), so this won't scale
        #       High-DPI Windows (125%, 150%, 200%) might also need scaling if templates were captured on standard DPI
        if platform.system() == "Darwin" and sft > 1.0:
            log(f"  Mac Retina: Scaling snapshot {sft}x to match template resolution...")
            new_width = int(screenshot_cv.shape[1] * sft)
            new_height = int(screenshot_cv.shape[0] * sft)
            screenshot_cv = cv2.resize(screenshot_cv, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # Save to file (use platform-aware path if not provided)
        if save_path is None:
            save_path = get_image_path("img.png")
        cv2.imwrite(save_path, screenshot_cv)
        log(f"Snapshot saved to {save_path}")
        log(f"  Final size: {screenshot_cv.shape[1]}x{screenshot_cv.shape[0]} pixels")
        if sft > 1.0:
            log(f"  (Scaled {sft}x to match template resolution)")
        
        return screenshot_cv
        
    def check_flipback_exists(self, debug=False):
        """Check if flipback.png exists on screen using single_find_with_path."""
        # Use single_find_with_path to check for flipback.png
        # This checks the screen without taking/storing a new screenshot
        # Parameters: but_path, gs (None = take new screenshot), th (threshold)
        
        # Mac needs lower threshold due to Retina display differences
        import platform
        threshold = 0.5 if platform.system() == "Darwin" else 0.7
        
        # If debug mode, show match confidence
        if debug:
            # Take screenshot and check match value
            screenshot = pyautogui.screenshot()
            screen = np.array(screenshot)
            gray_screen = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
            
            template = cv2.imread(self.flipback_template, 0)
            if template is not None:
                result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                log(f"🔍 Debug: flipback match confidence = {max_val:.3f} (threshold = {threshold})")
        
        found = single_find_with_path(self.flipback_template, None, threshold)
        
        if found:
            log(f"✅ Flipback detected! (threshold: {threshold})")
            return True
        
        return False
        
    def wait_for_flipback(self, check_interval=0.5, timeout=60):
        """
        Monitor the screen and wait for flipback.png to appear.
        
        Args:
            check_interval: Seconds between checks
            timeout: Maximum time to wait (seconds)
        """
        log("Waiting for cards to flip back...")
        log(f"Checking every {check_interval}s (timeout: {timeout}s)")
        
        start_time = time.time()
        check_count = 0
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                log(f"TIMEOUT: Cards did not flip back within {timeout}s")
                return False
            
            check_count += 1
            
            # Enable debug mode every 10 checks (5 seconds) to show match confidence
            debug_mode = (check_count % 10 == 0)
            
            # Check if flipback exists on screen (doesn't save/override img.png)
            if self.check_flipback_exists(debug=debug_mode):
                log(f"Cards flipped back after {elapsed:.1f}s ({check_count} checks)")
                return True
            
            # Progress indicator
            if check_count % 4 == 0:  # Every 2 seconds
                log(f"  Still waiting... ({elapsed:.1f}s elapsed)")
            
            time.sleep(check_interval)
        
    def solve_without_waiting(self, dry_run=False):
        """Solve cards after waiting for flipback.
        
        Used by auto_card_game.py when cards are already revealed.
        Takes snapshot, waits for cards to flip back, then solves.
        
        Args:
            dry_run: If True, don't actually click
            
        Returns:
            True if successful, False otherwise
        """
        # Load configuration
        if not self.load_config():
            log("ERROR: Failed to load configuration")
            return False
        
        # Take snapshot
        log("Taking snapshot...")
        self.take_snapshot()
        
        # Wait for cards to flip back (flipback.png appears)
        log("\nWaiting for cards to flip back...")
        if not self.wait_for_flipback():
            log("ERROR: Failed to detect flipback")
            return False
        
        # Wait a moment after flipback for stability
        log("Waiting 1 second after flip back...")
        time.sleep(1.0)
        
        log("\nRunning card matcher...")
        log("="*70)
        
        # Use platform-specific matcher
        if platform.system() == "Darwin":
            log("Using MacCardMatcher (Mac)")
            snapshot_offset = (self.card_area['x1'], self.card_area['y1'])
            matcher = MacCardMatcher(snapshot_offset=snapshot_offset)
            threshold = 0.75
        else:
            log("Using TemplateCardMatcher (Windows)")
            matcher = TemplateCardMatcher()
            threshold = 0.7
        
        success = matcher.solve_and_click(
            threshold=threshold,
            click_delay_between=0.25,
            click_delay_after=0.45,
            dry_run=dry_run
        )
        
        if success:
            log("\n" + "="*70)
            log("SOLVER COMPLETE - SUCCESS")
            log("="*70)
        else:
            log("\n" + "="*70)
            log("SOLVER FAILED")
            log("="*70)
        
        return success
    
    def run(self, dry_run=False):
        """Main automation flow."""
        log("="*70)
        log("AUTOMATIC SNAPSHOT AND SOLVER")
        log("="*70)
        log("")
        log("This script will:")
        log("1. Take snapshot of card area (save to img.png)")
        log("2. Wait for cards to flip back (flipback.png detected)")
        log("3. Wait 1 second after flip back")
        log("4. Run template card matcher to solve")
        log("")
        log("="*70)
        
        # Load configuration
        if not self.load_config():
            log("ERROR: Failed to load configuration")
            return False
        
        # Take initial snapshot
        log("\nStep 1: Taking initial snapshot...")
        self.take_snapshot()  # Uses platform-aware path by default
        
        # Small delay to ensure cards have time to be clicked/flipped up
        log("\nWaiting 2 seconds for cards to be flipped...")
        time.sleep(1.0)
        
        # Check if cards are already flipped back (they shouldn't be yet)
        if self.check_flipback_exists():
            log("⚠️  WARNING: Cards are already flipped back!")
            log("   Make sure to click on cards to flip them face-up BEFORE running this script.")
            log("   Continuing anyway...")
        
        log("\nStep 2: Waiting for cards to flip back...")
        if not self.wait_for_flipback():
            log("ERROR: Failed to detect flipback")
            return False
        
        log("\nStep 3: Waiting 1 second after flip back...")
        time.sleep(2.0)
        
        log("\nStep 4: Running card matcher...")
        log("="*70)
        
        # Use platform-specific matcher
        if platform.system() == "Darwin":
            log("Using MacCardMatcher (Mac)")
            # Pass snapshot offset so matcher can convert image coords to screen coords
            snapshot_offset = (self.card_area['x1'], self.card_area['y1'])
            matcher = MacCardMatcher(snapshot_offset=snapshot_offset)
            threshold = 0.92  # Mac templates might need slightly lower threshold
        else:
            log("Using TemplateCardMatcher (Windows)")
            matcher = TemplateCardMatcher()
            threshold = 0.7
        
        success = matcher.solve_and_click(
            threshold=threshold,
            click_delay_between=0.2,
            click_delay_after=0.28,
            dry_run=dry_run
        )
        
        if success:
            log("\n" + "="*70)
            log("AUTOMATION COMPLETE - SUCCESS")
            log("="*70)
        else:
            log("\n" + "="*70)
            log("AUTOMATION FAILED")
            log("="*70)
        
        return success


def main():
    """Main entry point."""
    import sys
    
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    log("Automatic Snapshot Solver")
    log("=" * 70)
    log(f"Platform: {platform.system()}")
    log("")
    log("Make sure:")
    log("  - Card matching game is visible")
    log("  - flipback.png exists in pics/mac/match/ (Mac) or pics/match/ (Windows)")
    log("  - run_button configured in config file")
    log("  - Template images are in pics/mac/match/ (Mac) or pics/match/ (Windows)")
    log("  - Card coordinates configured: pair_top_left and pair_bottom_right")
    log("")
    log("Snapshot will be saved to:")
    log(f"  {get_image_path('img.png')}")
    log("")
    
    if dry_run:
        log("*** DRY RUN MODE - Will not actually click ***")
        log("")
    
    input("Press ENTER to start...")
    
    solver = AutoSnapshotSolver()
    solver.run(dry_run=dry_run)


if __name__ == "__main__":
    main()
