"""
Automatic Snapshot and Solver
Automatically takes screenshots and waits for cards to flip back before solving
"""
import cv2
import numpy as np
import time
import os
import pyautogui
from log_helper import log
from config_coords import ConfigCoords
from template_card_matcher import TemplateCardMatcher
from common import single_find_with_path


class AutoSnapshotSolver:
    def __init__(self):
        """Initialize the auto snapshot solver."""
        self.config = None
        self.card_area = None
        self.flipback_template = "pics/match/flipback.png"
        
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
        
        # Calculate card area coordinates (relative to run button)
        rb_x = self.config.rb.x
        rb_y = self.config.rb.y
        
        # Card area: top-left (-370, -1000), bottom-right (450, 110)
        x1 = int(rb_x - 370)
        y1 = int(rb_y - 1000)
        x2 = int(rb_x + 450)
        y2 = int(rb_y + 110)
        
        self.card_area = {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'width': x2 - x1,
            'height': y2 - y1
        }
        
        log(f"Card area: ({x1}, {y1}) to ({x2}, {y2})")
        log(f"Size: {self.card_area['width']}x{self.card_area['height']}")
        
        return True
        
    def take_snapshot(self, save_path="pics/img.png"):
        """Take a screenshot of the card area."""
        log(f"Taking snapshot of card area...")
        
        # Take screenshot of the specific region
        screenshot = pyautogui.screenshot(region=(
            self.card_area['x1'],
            self.card_area['y1'],
            self.card_area['width'],
            self.card_area['height']
        ))
        
        # Convert PIL image to OpenCV format
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Save to file
        cv2.imwrite(save_path, screenshot_cv)
        log(f"Snapshot saved to {save_path}")
        
        return screenshot_cv
        
    def check_flipback_exists(self):
        """Check if flipback.png exists on screen using single_find_with_path."""
        # Use single_find_with_path to check for flipback.png
        # This checks the screen without taking/storing a new screenshot
        # Parameters: but_path, gs (None = take new screenshot), th (threshold)
        found = single_find_with_path(self.flipback_template, None, 0.7)
        
        if found:
            log(f"Flipback detected!")
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
            
            # Check if flipback exists on screen (doesn't save/override img.png)
            if self.check_flipback_exists():
                log(f"Cards flipped back after {elapsed:.1f}s ({check_count} checks)")
                return True
            
            # Progress indicator
            if check_count % 4 == 0:  # Every 2 seconds
                log(f"  Still waiting... ({elapsed:.1f}s elapsed)")
            
            time.sleep(check_interval)
        
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
        self.take_snapshot("pics/img.png")
        
        log("\nStep 2: Waiting for cards to flip back...")
        if not self.wait_for_flipback():
            log("ERROR: Failed to detect flipback")
            return False
        
        log("\nStep 3: Waiting 1 second after flip back...")
        time.sleep(2.0)
        
        log("\nStep 4: Running template card matcher...")
        log("="*70)
        
        # Run the template matcher
        matcher = TemplateCardMatcher()
        success = matcher.solve_and_click(
            threshold=0.7,
            click_delay_between=0.1,
            click_delay_after=0.35,
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
    log("")
    log("Make sure:")
    log("  - Card matching game is visible")
    log("  - flipback.png exists in pics/match/")
    log("  - run_button configured in config file")
    log("  - Template images are in pics/match/")
    log("")
    
    if dry_run:
        log("*** DRY RUN MODE - Will not actually click ***")
        log("")
    
    input("Press ENTER to start...")
    
    solver = AutoSnapshotSolver()
    solver.run(dry_run=dry_run)


if __name__ == "__main__":
    main()
