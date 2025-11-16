"""
Smart Card Grabber - Uses "again_card" when face appears in last visit boxes

This module checks if FACE_UP_LEFT appears within the coordinate boxes of 
visit_last_c1 through visit_last_c4, and if found, uses the complete card
grabbing flow to click the "again_card".
"""

import time
import pyautogui
from common import get_center, get_scaling_factor, single_find, get_all, simple_single_find
from click import click_at
from config_coords import ConfigCoords
from log_helper import log


class SmartCardGrab:
    """Check for faces in visit boxes and use again_card when available."""

    def __init__(self, sft=0, rb=None):
        """Initialize SmartCardGrab.

        Args:
            sft: Scaling factor (0 = auto-detect)
            rb: Run button center (for getting coordinates)
        """
        if sft == 0:
            self.sft = get_scaling_factor()
        else:
            self.sft = sft

        self.rb = rb

        # Initialize config immediately
        self.config = ConfigCoords()
        if rb:
            self.rb = rb
        else:
            self.rb = self.config.rb

        # Define box size around each visit coordinate (adjust as needed)
        self.box_size = 100  # pixels in each direction from center

    def _init_config(self, mock_rb=None):
        """Initialize or update config with mock rb if needed.

        Args:
            mock_rb: Optional mock run button position for testing
        """
        if mock_rb:
            # Re-initialize with mock rb for testing
            self.config = ConfigCoords(mock_rb=mock_rb)
            from collections import namedtuple
            Point = namedtuple('Point', ['x', 'y'])
            self.rb = Point(mock_rb[0], mock_rb[1])
        # Otherwise config is already initialized in __init__

    def check_face_in_box(self, box_name):
        """Check if FACE_UP_LEFT appears within a specific visit box.

        Args:
            box_name: Name of the visit box (e.g., "visit_last_c1")

        Returns:
            True if face found in box, False otherwise
        """
        # Get the center coordinates of the box
        box_coords = self.config.get_coord(box_name)
        if box_coords is None:
            log(f"Warning: Could not get coordinates for {box_name}")
            return False

        box_x, box_y = box_coords

        # Try to find all FACE_UP_LEFT occurrences
        try:
            faces = get_all("VISIT_FACE_UP_LEFT", "Single")
        except:
            # No faces found at all
            return False

        if len(faces) == 0:
            return False

        # Check if any face is within the box area
        for face in faces:
            face_x = face.x / self.sft
            face_y = face.y / self.sft

            # Check if face is within box bounds
            if (abs(face_x - box_x) <= self.box_size and
                abs(face_y - box_y) <= self.box_size):
                log(f"�?Found VISIT_FACE_UP_LEFT in {box_name} box at ({face_x:.1f}, {face_y:.1f})")
                return True

        return False

    def _check_and_click_card_button(self):
        """Step 1: Click card_button to enter card selection UI."""
        log("Clicking card_button from config...")
        card_button_coords = self.config.get_coord("card_button")
        if not card_button_coords:
            log("ERROR: card_button coordinates not found in config!")
            return False

        click_at(card_button_coords[0], card_button_coords[1])
        log(f"Clicked card_button at ({card_button_coords[0]:.1f}, {card_button_coords[1]:.1f})")
        
        # Wait for UI to transition to card selection mode
        time.sleep(3)
        log("Waiting for card selection UI...")
        
        return True

    def _open_card_mode(self):
        """Step 2: Click RunButton to open card mode."""
        log("Opening card mode by clicking RunButton...")
        click_at(self.rb.x / self.sft, self.rb.y / self.sft)
        log(f"Clicked RunButton at ({self.rb.x / self.sft:.1f}, {self.rb.y / self.sft:.1f})")
        time.sleep(3)  # Wait for card mode to open

        # Check for VisitBusy
        if single_find("VisitBusy"):
            log("Visit busy, clicking confirm...")
            try:
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
            except:
                log("Could not find Confirm button")
            time.sleep(2)

        # Wait for card mode to open
        time.sleep(5)

        # Check if CardMode opened, or if we're still at RunButton (click didn't work)
        retry = 10
        while retry > 0:
            # PRIORITY 1: Check if CardMode opened successfully (success case!)
            if single_find("CardMode"):
                log("✅ Card mode opened successfully!")
                time.sleep(1)
                return True

            # PRIORITY 2: Check if RunButton is still visible (we never left main mode)
            if simple_single_find("RunButton", "Main", 0.8):
                log("⚠️ RunButton still visible - card mode did not open (game was busy)")
                return False


            log(f"Waiting for CardMode... (retry: {retry})")
            time.sleep(1)
            retry -= 1

        log("⚠️ CardMode not detected after retries")
        return False

    def _check_face_in_any_box(self):
        """Check if face is in any visit box at the beginning.

        Returns:
            True if face found in any box, False otherwise
        """
        log("Checking for faces in visit boxes...")

        for i in range(1, 5):
            box_name = f"visit_last_c{i}"
            if self.check_face_in_box(box_name):
                log(f"�?Face detected in {box_name}!")
                return True

        log("No face found in any visit boxes")
        return False

    def _pull_again_card(self):
        """Step 4: Find and pull AgainCard.

        Returns:
            True if card was found and used, False otherwise
        """
        log("Step 4: Looking for AgainCard...")
        time.sleep(1)  # Small delay before searching

        # Check if AgainCard exists
        if not single_find("AgainCard"):
            log("⚠️ AgainCard not found!")
            log("Closing card mode before exiting...")
            # Close card mode if AgainCard not found
            self._close_card_mode()
            return False

        # Pull the AgainCard
        try:
            ac = get_center("AgainCard", "Single")
            log(f"Pulling AgainCard at ({ac.x / self.sft:.1f}, {ac.y / self.sft:.1f})")

            # Drag the card (similar to CatCard drag)
            pyautogui.moveTo(ac.x / self.sft, ac.y / self.sft, duration=0.5)
            time.sleep(0.5)  # Pause before dragging
            pyautogui.dragTo(ac.x / self.sft, ac.y / self.sft - 300, duration=1, button='left')
            log("�?AgainCard pulled!")
            time.sleep(8)  # Wait for card pull animation to complete

            # Handle VisitBusy after pulling (with retry)
            retry = 3
            while single_find("VisitBusy") and retry > 0:
                log("Visit busy, clicking confirm...")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(2)
                retry -= 1

            return True
        except Exception as e:
            log(f"❌ Failed to pull AgainCard: {e}")
            log("Closing card mode before exiting...")
            # Close card mode if pull failed
            self._close_card_mode()
            return False

    def _close_card_mode(self):
        """Step 5: Close card mode by clicking elsewhere with retry."""
        log("Step 5: Closing card mode...")

        retry = 3
        while single_find("CardMode") and retry > 0:
            # Click somewhere to close the card overlay (click above run button)
            click_at(self.rb.x / self.sft, self.rb.y / self.sft - 300)
            log(f"Clicked to close card mode at ({self.rb.x / self.sft:.1f}, {self.rb.y / self.sft - 300:.1f})")
            time.sleep(2)
            retry -= 1

        log("�?Card mode closed")
        time.sleep(1)  # Extra delay after closing

    def _back_to_visit(self):
        """Step 6: Click back_visit and verify RunButton is back."""
        log("Step 6: Returning to visit mode...")

        # First check if RunButton is already visible (we might already be in visit mode)
        try:
            if simple_single_find("RunButton", "Main", 0.8):
                log("�?RunButton already visible - already in visit mode, skipping back_visit click")
                return True
        except Exception as e:
            log(f"Error checking for RunButton: {e}")

        # Click back_visit using config coords
        back_visit_coords = self.config.get_coord("back_visit")
        if not back_visit_coords:
            log("ERROR: back_visit coordinates not found in config!")
            return False

        click_at(back_visit_coords[0], back_visit_coords[1])
        log(f"Clicked back_visit at ({back_visit_coords[0]:.1f}, {back_visit_coords[1]:.1f})")
        time.sleep(3)  # Increased wait time for transition

        # Double check RunButton is back (verify we're in visit mode)
        retry = 5
        while retry > 0:
            try:
                if simple_single_find("RunButton", "Main", 0.8):
                    log("�?RunButton found - back in visit mode!")
                    time.sleep(1)  # Extra delay after confirming back in visit mode
                    return True
            except Exception as e:
                log(f"Error checking for RunButton: {e}")

            log(f"Waiting for RunButton to appear... (retry: {retry})")
            time.sleep(2)
            retry -= 1

        log("⚠️ RunButton not detected after retries, but continuing...")
        return True

    def smart_grab_cat(self, mock_rb=None):
        """Main function: Complete card grab flow with AgainCard.

        New simplified flow without robot detection:
        0. Check for faces in visit boxes FIRST (before starting)
        1. Check RunButton exists, if not click card_button from config
        2. Click card_button once using config coords
        3. Click RunButton to open card mode
        4. Pull AgainCard
        5. Close card mode by clicking elsewhere
        6. Click back_visit and verify RunButton is back

        Args:
            mock_rb: Optional mock run button position for testing

        Returns:
            True if face found and card used, False otherwise
        """
        # Initialize config if needed
        self._init_config(mock_rb)

        log("=" * 70)
        log("SMART CARD GRAB - Starting complete card grab flow")
        log("=" * 70)

        # # Step 0: Check for faces BEFORE starting card grab
        # if not self._check_face_in_any_box():
        #     log("=" * 70)
        #     log("�?No face in visit boxes, skipping card grab")
        #     log("=" * 70)
        #     return False

        # Retry entire card grab flow up to 3 times if any step fails
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            log(f"Card grab attempt {attempt}/{max_retries}")
            
            try:

                # PRIORITY 3: Check if visit already completed (rolling finished naturally)
                if simple_single_find("VisitComplete", "Visit", 0.8):
                    log("✅ Visit already completed - no card mode needed!")
                    log("Visit finished naturally, skipping card grab")
                    return False

                # Step 1-2: Check RunButton and click card_button
                if not self._check_and_click_card_button():
                    raise Exception("Failed to click card_button")

                # Step 3: Open card mode
                if not self._open_card_mode():
                    raise Exception("Failed to open card mode")

                # Step 4: Pull AgainCard
                if not single_find("CardMode"):
                    raise Exception("CardMode not detected")
                
                pull_result = self._pull_again_card()
                if not pull_result:
                    # AgainCard not found or pull failed - card mode already closed in _pull_again_card
                    log("AgainCard not available, returning to visit mode...")
                    # Return to visit mode
                    if not self._back_to_visit():
                        log("⚠️ Failed to return to visit mode, but continuing...")
                    log("=" * 70)
                    log("✅ Card grab completed (no AgainCard used)")
                    log("=" * 70)
                    return False  # Exit gracefully without retry

                # Step 5: Close card mode
                self._close_card_mode()

                # Step 6: Back to visit mode
                if not self._back_to_visit():
                    raise Exception("Failed to return to visit mode")

                # Success! Card was used
                log("=" * 70)
                log("✅ Successfully used AgainCard!")
                log("=" * 70)
                return True
                
            except Exception as e:
                log(f"�?Attempt {attempt} failed: {e}")
                
                # Special case: If visit completed naturally, just exit gracefully
                # Let the visiting() loop handle the VisitComplete logic
                if single_find("VisitComplete"):
                    log("=" * 70)
                    log("�?Visit completed naturally during card grab attempt")
                    log("Exiting card grab, letting visiting() handle completion")
                    log("=" * 70)
                    return False  # Exit immediately, no recovery needed
                
                # Try to recover - close card mode if open, then go back to visit
                try:
                    # If we're in CardMode, close it first
                    if single_find("CardMode"):
                        log("CardMode still open, closing it before recovery...")
                        self._close_card_mode()
                        time.sleep(2)
                    
                    # Now try to go back to visit mode if not at RunButton
                    if not simple_single_find("RunButton", "Main", 0.8):
                        log("Not at RunButton, attempting recovery...")
                        self._back_to_visit()
                except Exception as recovery_error:
                    log(f"Recovery failed: {recovery_error}")
                
                if attempt < max_retries:
                    log(f"Waiting 5 seconds before retry {attempt + 1}...")
                    time.sleep(5)
                else:
                    log("�?All retry attempts exhausted")
                    log("=" * 70)
                    log("�?Card grab failed, continuing with normal visit")
                    log("=" * 70)
                    return False


# Convenience function
def check_and_use_again_card(mock_rb=None):
    """Quick function to check faces and use again_card.

    Args:
        mock_rb: Optional mock run button position for testing

    Returns:
        True if successful, False otherwise
    """
    grabber = SmartCardGrab()
    return grabber.smart_grab_cat(mock_rb=mock_rb)


if __name__ == "__main__":
    # Test the smart card grabber
    log("Testing Smart Card Grab...")
    
    # Use mock mode for testing without game window
    grabber = SmartCardGrab()
    grabber.smart_grab_cat(mock_rb=(2667, 1164))
