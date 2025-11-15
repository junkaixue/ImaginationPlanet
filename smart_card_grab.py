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
            print(f"Warning: Could not get coordinates for {box_name}")
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
                print(f"✅ Found VISIT_FACE_UP_LEFT in {box_name} box at ({face_x:.1f}, {face_y:.1f})")
                return True
        
        return False
    
    def _check_and_click_card_button(self):
        """Step 1-2: Check for RunButton, if not click card_button from config, then click card_button once."""
        # Step 1: Check if RunButton exists
        if not simple_single_find("RunButton", "Main", 0.8):
            print("RunButton not visible, clicking card_button from config...")
            card_button_coords = self.config.get_coord("card_button")
            if card_button_coords:
                click_at(card_button_coords[0], card_button_coords[1])
                print(f"Clicked card_button at config position ({card_button_coords[0]:.1f}, {card_button_coords[1]:.1f})")
                time.sleep(2)
        
        # Step 2: RunButton found (or should be visible now), click card_button using config coords
        print("Clicking card_button from config...")
        card_button_coords = self.config.get_coord("card_button")
        if not card_button_coords:
            print("ERROR: card_button coordinates not found in config!")
            return False
        
        click_at(card_button_coords[0], card_button_coords[1])
        print(f"Clicked card_button at ({card_button_coords[0]:.1f}, {card_button_coords[1]:.1f})")
        time.sleep(1)
        return True
    
    def _open_card_mode(self):
        """Step 3: Click RunButton to open card mode."""
        print("Opening card mode by clicking RunButton...")
        click_at(self.rb.x / self.sft, self.rb.y / self.sft)
        print(f"Clicked RunButton at ({self.rb.x / self.sft:.1f}, {self.rb.y / self.sft:.1f})")
        time.sleep(5)  # Wait for card mode to open
        
        # Verify card mode is open
        if single_find("CardMode"):
            print("✅ Card mode opened successfully!")
            return True
        else:
            print("⚠️ CardMode not detected, but continuing...")
            return True
    
    def _check_face_in_any_box(self):
        """Check if face is in any visit box at the beginning.
        
        Returns:
            True if face found in any box, False otherwise
        """
        print("Checking for faces in visit boxes...")
        
        for i in range(1, 5):
            box_name = f"visit_last_c{i}"
            if self.check_face_in_box(box_name):
                print(f"✅ Face detected in {box_name}!")
                return True
        
        print("No face found in any visit boxes")
        return False
    
    def _pull_again_card(self):
        """Step 4: Find and pull AgainCard.
        
        Returns:
            True if card was found and used, False otherwise
        """
        print("Step 4: Looking for AgainCard...")
        
        # Check if AgainCard exists
        if not single_find("AgainCard"):
            print("AgainCard not found")
            return False
        
        # Pull the AgainCard
        try:
            ac = get_center("AgainCard", "Single")
            print(f"Pulling AgainCard at ({ac.x / self.sft:.1f}, {ac.y / self.sft:.1f})")
            
            # Drag the card (similar to CatCard drag)
            pyautogui.moveTo(ac.x / self.sft, ac.y / self.sft, duration=0.5)
            pyautogui.dragTo(ac.x / self.sft, ac.y / self.sft - 300, duration=1, button='left')
            print("✅ AgainCard pulled!")
            time.sleep(8)
            
            # Handle VisitBusy after pulling
            if single_find("VisitBusy"):
                print("Visit busy, clicking confirm...")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            
            return True
        except Exception as e:
            print(f"Failed to pull AgainCard: {e}")
            return False
    
    def _close_card_mode(self):
        """Step 5: Close card mode by clicking elsewhere."""
        print("Step 5: Closing card mode...")
        
        # Click somewhere to close the card overlay (click above run button)
        click_at(self.rb.x / self.sft, self.rb.y / self.sft - 300)
        print(f"Clicked to close card mode at ({self.rb.x / self.sft:.1f}, {self.rb.y / self.sft - 300:.1f})")
        time.sleep(2)
        
        print("✅ Card mode closed")
    
    def _back_to_visit(self):
        """Step 6: Click back_visit and verify RunButton is back."""
        print("Step 6: Returning to visit mode...")
        
        # Click back_visit using config coords
        back_visit_coords = self.config.get_coord("back_visit")
        if not back_visit_coords:
            print("ERROR: back_visit coordinates not found in config!")
            return False
        
        click_at(back_visit_coords[0], back_visit_coords[1])
        print(f"Clicked back_visit at ({back_visit_coords[0]:.1f}, {back_visit_coords[1]:.1f})")
        time.sleep(2)
        
        # Double check RunButton is back (verify we're in visit mode)
        retry = 3
        while retry > 0:
            if single_find("RunButton"):
                print("✅ RunButton found - back in visit mode!")
                return True
            print("Waiting for RunButton to appear...")
            time.sleep(1)
            retry -= 1
        
        print("⚠️ RunButton not detected, but continuing...")
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
        
        print("=" * 70)
        print("SMART CARD GRAB - Starting complete card grab flow")
        print("=" * 70)
        
        # Step 0: Check for faces BEFORE starting card grab
        if not self._check_face_in_any_box():
            print("=" * 70)
            print("❌ No face in visit boxes, skipping card grab")
            print("=" * 70)
            return False
        
        # Step 1-2: Check RunButton and click card_button
        if not self._check_and_click_card_button():
            print("❌ Failed to click card_button")
            return False
        
        # Step 3: Open card mode
        if not self._open_card_mode():
            print("❌ Failed to open card mode")
            return False
        
        # Step 4: Pull AgainCard
        card_used = self._pull_again_card()
        
        # Step 5: Close card mode
        self._close_card_mode()
        
        # Step 6: Back to visit mode
        if not self._back_to_visit():
            print("❌ Failed to return to visit mode")
            return False
        
        if card_used:
            print("=" * 70)
            print("✅ Successfully used AgainCard!")
            print("=" * 70)
            return True
        else:
            print("=" * 70)
            print("❌ AgainCard not available")
            print("=" * 70)
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
    print("Testing Smart Card Grab...")
    
    # Use mock mode for testing without game window
    grabber = SmartCardGrab()
    grabber.smart_grab_cat(mock_rb=(2667, 1164))
