"""
Automated Card Matching Game Player

Fully automates the card matching game:
1. Clicks run button to start game
2. Validates cards are shown (flipback.png detected)
3. Waits for cards to be revealed (flipback.png gone)
4. Solves the card matching automatically
5. Clicks run button to end game
"""

import time
import platform
from log_helper import log
from click import click_at
from common import get_center, single_find_with_path, get_scaling_factor
from platform_config import get_image_path
from auto_snapshot_solver import AutoSnapshotSolver


class AutoCardGame:
    """Fully automated card matching game player."""
    
    def __init__(self):
        """Initialize the automated game player."""
        self.run_button_pos = None
        self.flipback_template = get_image_path("flipback.png")
        self.start_match_template = get_image_path("start_match.png")
        self.solver = AutoSnapshotSolver()
        self.sft = get_scaling_factor()
        
    def find_run_button(self):
        """Find the run button position from config or template matching."""
        log("Looking for Run Button...")
        
        # First try to load from config file
        import os
        config_file = "cood_mac.cfg" if platform.system() == "Darwin" else "cood_win.cfg"
        config_path = os.path.join("configs", config_file)
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('run_button:'):
                        try:
                            coords = line.split(':')[1].strip()
                            x, y = coords.split(',')
                            rb_x = float(x.strip())
                            rb_y = float(y.strip())
                            
                            # Config stores logical coordinates, use directly
                            self.run_button_pos = (rb_x, rb_y)
                            log(f"✅ Found Run Button in config: ({rb_x:.1f}, {rb_y:.1f})")
                            return True
                        except Exception as e:
                            log(f"Could not parse run_button from config: {e}")
                            break
        
        # Fallback to template matching
        log("Run Button not in config, trying template matching...")
        retry = 10
        
        while retry > 0:
            try:
                # get_center returns logical coordinates
                self.run_button_pos = get_center("RunButton", "Main")
                log(f"✅ Found Run Button via template: ({self.run_button_pos[0]:.1f}, {self.run_button_pos[1]:.1f})")
                return True
            except:
                log(f"Run Button not found, retrying... ({retry} attempts left)")
                retry -= 1
                time.sleep(1)
        
        log("❌ Failed to find Run Button")
        return False
    
    def click_run_button(self, action="start"):
        """Click the run button.
        
        Args:
            action: Description of the action (for logging)
        """
        if not self.run_button_pos:
            log("ERROR: Run Button position not set")
            return False
        
        x, y = self.run_button_pos
        log(f"Clicking Run Button to {action} game at ({x:.1f}, {y:.1f})")
        click_at(x, y)
        return True
    
    def check_start_match_visible(self):
        """Check if start_match.png is visible on screen.
        
        Returns:
            True if start_match is visible, False otherwise
        """
        threshold = 0.7
        return single_find_with_path(self.start_match_template, None, threshold)
    
    def check_flipback_visible(self):
        """Check if flipback.png is visible on screen.
        
        Returns:
            True if flipback is visible, False otherwise
        """
        threshold = 0.7 if platform.system() == "Darwin" else 0.7
        return single_find_with_path(self.flipback_template, None, threshold)
    
    def wait_for_start_match_gone(self, timeout=10.0):
        """Wait until start_match.png disappears (game started).
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if start_match disappeared, False if timeout
        """
        log("Waiting for start_match.png to disappear (game starting)...")
        start_time = time.time()
        check_interval = 0.5
        check_count = 0
        
        while (time.time() - start_time) < timeout:
            elapsed = time.time() - start_time
            check_count += 1
            
            if not self.check_start_match_visible():
                log(f"✅ Game started after {elapsed:.1f}s ({check_count} checks)")
                return True
            
            # Progress indicator
            if check_count % 4 == 0:  # Every 2 seconds
                log(f"  Still waiting for game to start... ({elapsed:.1f}s elapsed)")
            
            time.sleep(check_interval)
        
        log(f"⚠️  Timeout: Game not started after {timeout}s")
        return False
    
    def wait_for_flipback_visible(self, timeout=10.0):
        """Wait until flipback.png becomes visible.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if flipback appeared, False if timeout
        """
        log("Waiting for cards to be shown (flipback.png visible)...")
        start_time = time.time()
        check_interval = 0.5
        check_count = 0
        
        while (time.time() - start_time) < timeout:
            elapsed = time.time() - start_time
            check_count += 1
            
            if self.check_flipback_visible():
                log(f"✅ Cards shown after {elapsed:.1f}s ({check_count} checks)")
                return True
            
            # Progress indicator
            if check_count % 4 == 0:  # Every 2 seconds
                log(f"  Still waiting for cards... ({elapsed:.1f}s elapsed)")
            
            time.sleep(check_interval)
        
        log(f"⚠️  Timeout: Cards not shown after {timeout}s")
        return False
    
    def wait_for_flipback_gone(self, timeout=30.0):
        """Wait until flipback.png disappears (cards revealed).
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if flipback disappeared, False if timeout
        """
        log("Waiting for cards to be revealed (flipback.png gone)...")
        start_time = time.time()
        check_interval = 0.5
        check_count = 0
        
        while (time.time() - start_time) < timeout:
            elapsed = time.time() - start_time
            check_count += 1
            
            # Check if flipback is gone
            if not self.check_flipback_visible():
                log(f"✅ Cards revealed after {elapsed:.1f}s ({check_count} checks)")
                return True
            
            # Progress indicator
            if check_count % 4 == 0:  # Every 2 seconds
                log(f"  Still waiting for reveal... ({elapsed:.1f}s elapsed)")
            
            time.sleep(check_interval)
        
        log(f"⚠️  Timeout: Cards not revealed after {timeout}s")
        return False
    
    def run_full_game(self, dry_run=False, skip_start_click=False, skip_end_click=False):
        """Run the complete automated game workflow.
        
        Args:
            dry_run: If True, don't actually click cards (for testing)
            skip_start_click: If True, skip clicking Run Button at start (game already started)
            skip_end_click: If True, skip clicking Run Button at end
            
        Returns:
            True if game completed successfully, False otherwise
        """
        log("="*70)
        log("AUTOMATED CARD MATCHING GAME")
        log("="*70)
        log("")
        log("Workflow:")
        if not skip_start_click:
            log("  Step 1: Click Run Button (verify start_match.png gone, retry if needed)")
            log("  Step 2: Wait for flipback.png showing (cards displayed)")
            log("  Step 3: Wait for flipback.png gone (cards revealed)")
            log("  Step 4: Auto snapshot and solve immediately")
        else:
            log("  Step 1: (Skipped - game already started)")
            log("  Step 2: Wait for flipback.png showing (cards displayed)")
            log("  Step 3: Wait for flipback.png gone (cards revealed)")
            log("  Step 4: Auto snapshot and solve immediately")
        if not skip_end_click:
            log("  Step 5: Click Run Button to end game")
        else:
            log("  Step 5: (Skipped - manual end)")
        log("")
        log("="*70)
        
        # Find run button first
        log("\nFinding Run Button...")
        if not self.find_run_button():
            log("ERROR: Cannot proceed without Run Button")
            return False
        
        # Step 1: Click run button to start game (optional)
        if not skip_start_click:
            log("\n[Step 1] Clicking Run Button to start game...")
            
            # Try up to 3 times to start the game
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                if attempt > 1:
                    log(f"\nRetrying (attempt {attempt}/{max_retries})...")
                
                if not self.click_run_button("start"):
                    log("ERROR: Failed to click Run Button")
                    return False
                
                # Wait a moment for game to initialize
                time.sleep(1.0)
                
                # Check if start_match.png disappeared
                if not self.wait_for_start_match_gone(timeout=5.0):
                    if attempt < max_retries:
                        log("⚠️  start_match.png still visible, clicking Run Button again...")
                        continue
                    else:
                        log("❌ ERROR: Game failed to start after 3 attempts")
                        return False
                else:
                    # Success - game started
                    break
        else:
            log("\n[Step 1] Skipping start click (game already started)")
        
        # Step 2: Wait for flipback showing (cards displayed)
        log("\n[Step 2] Waiting for flipback.png showing (cards displayed)...")
        if not self.wait_for_flipback_visible(timeout=10.0):
            log("ERROR: Cards not shown - game may not have started")
            return False
        
        # Step 3: Wait for flipback gone (cards revealed)
        log("\n[Step 3] Waiting for flipback.png gone (cards revealed)...")
        if not self.wait_for_flipback_gone(timeout=10.0):
            log("ERROR: Cards not revealed - game may have stalled")
            return False
        
        # Step 4: Auto snapshot and solve immediately
        log("\n[Step 4] Auto snapshot and solve immediately...")
        log("="*70)
        
        # Use solver's solve_without_waiting method
        # This takes snapshot immediately and solves without user input
        success = self.solver.run(dry_run=dry_run)
        
        if not success:
            log("\n❌ Card matching failed")
            return False
        
        # Wait a moment for game to process the solution
        log("\nWaiting 2 seconds for game to process solution...")
        time.sleep(2.0)
        
        # Step 5: Click run button to end game (optional)
        if not skip_end_click:
            log("\n[Step 5] Clicking Run Button to end game...")
            if not self.click_run_button("end"):
                log("WARNING: Failed to click Run Button to end game")
                # Not a critical failure - game might auto-end
        else:
            log("\n[Step 5] Skipping end click")
        
        log("\n" + "="*70)
        log("🎉 AUTOMATED GAME COMPLETE!")
        log("="*70)
        
        return True


def main():
    """Main entry point."""
    import sys
    
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    log("Automated Card Matching Game Player")
    log("=" * 70)
    log("")
    log("This script will FULLY AUTOMATE the card matching game:")
    log("  1. Click Run Button to start")
    log("  2. Validate cards shown")
    log("  3. Wait for cards revealed")
    log("  4. Solve card matching")
    log("  5. Click Run Button to end")
    log("")
    log("Make sure:")
    log("  - Card matching game is visible")
    log("  - Run Button is visible")
    log("  - Templates exist in pics/mac/match/ (Mac) or pics/match/ (Windows)")
    log("  - Config file has pair_top_left, pair_bottom_right coordinates")
    log("")
    
    if dry_run:
        log("*** DRY RUN MODE - Will not actually click cards ***")
        log("")
    
    input("Press ENTER to start automated game...")
    
    game = AutoCardGame()
    success = game.run_full_game(dry_run=dry_run)
    
    if success:
        log("\n✅ Game completed successfully!")
    else:
        log("\n❌ Game failed - check logs above")
    
    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
