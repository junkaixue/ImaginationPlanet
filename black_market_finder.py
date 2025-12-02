import time
from collections import namedtuple
import platform

import pyautogui

from common import *
from config_coords import ConfigCoords

Point = namedtuple('Point', ['x', 'y'])


class BlackMarketFinder:
    click_point = None
    click_start = None
    offset_unit = 65  # Will be adjusted based on platform
    rb = None
    sft = 0
    
    def __init__(self):
        # Get the actual scaling factor
        self.sft = get_scaling_factor()
        
        # On Windows, the offset might need adjustment
        # For now, keep it at base value and adjust multipliers instead
        self.offset_unit = 65
        
        # Platform-conditional scan parameters (keep Mac original behavior)
        self.is_mac = (platform.system() == "Darwin")
        if self.is_mac:
            # Original aggressive values used on Mac
            self.scroll_right_step = -11
            self.scroll_left_step = 6
            self.scroll_down_step = -7
            self.columns = 3
            self.left_return_iters = 3
        else:
            # Gentler values for Windows to avoid clicking buttons while dragging
            self.scroll_right_step = -7
            self.scroll_left_step = 4
            self.scroll_down_step = -5
            self.columns = 4
            self.left_return_iters = 4
        
        print(f"Platform: {platform.system()}")
        print(f"Scaling factor: {self.sft}")
        print(f"Adjusted offset_unit: {self.offset_unit}")
        print(f"Scan params -> columns: {self.columns}, right_step: {self.scroll_right_step}, left_step: {self.scroll_left_step}, down_step: {self.scroll_down_step}")
        
        # Find run button
        found_rb = False
        retry = 50
        
        # Log the path being used
        from platform_config import IMAGE_DIR
        from common import main_map
        print(f"Image directory: {IMAGE_DIR}")
        print(f"RunButton path: {main_map['RunButton']}")
        
        while not found_rb:
            try:
                self.rb = get_center("RunButton", "Main")
                found_rb = True
            except Exception as e:
                print(f"Run Button was not found! Retry {50-retry}/50")
                print(f"Error: {e}")
                retry -= 1
                if retry == 0:
                    print("No run button, stop!")
                    exit(0)
                time.sleep(1)
        print("Found the Run Button!")
        
        # Update platform-specific config file with run button coordinate
        rb_x_logical = self.rb.x / self.sft
        rb_y_logical = self.rb.y / self.sft
        ConfigCoords.update_run_button_in_config(rb_x_logical, rb_y_logical)
        
        # Enter star entry
        self.enter_star_world()
        
        # Setup click reference points
        self.setup_click_points()
    
    def enter_star_world(self):
        """Enter the star world via star entry button"""
        retry = 10
        while not single_find("SEntry") and retry > 0:
            print("Star entry not found, waiting...")
            time.sleep(2)
            retry -= 1
        
        if retry == 0:
            print("Failed to find star entry!")
            return False
        
        # Click star entry
        retry = 5
        while single_find("SEntry") and retry > 0:
            center = get_center("SEntry", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            print("Clicking star entry button")
            retry -= 1
            time.sleep(2)
        
        # Wait for star world to load
        time.sleep(3)
        return True
    
    def setup_click_points(self):
        """Setup reference points for scrolling"""
        completed = False
        while not completed:
            try:
                loc = pyautogui.locateOnScreen(single_find_map["Shop"])
                self.click_point = Point((loc.left + loc.width) / self.sft, (loc.top - 20) / self.sft)
                self.click_start = Point(loc.left / self.sft, (loc.top - 20) / self.sft)
                print("Found click reference points")
                completed = True
            except:
                print("Cannot find shop reference point, retrying...")
                time.sleep(2)
    
    def scroll_left_right(self, n):
        """Scroll horizontally"""
        pyautogui.moveTo(self.click_point.x, self.click_point.y)
        pyautogui.mouseDown()
        pyautogui.move(n * self.offset_unit, 0)
        pyautogui.mouseUp()
    
    def scroll_start(self, n):
        """Scroll from current position"""
        pyautogui.mouseDown()
        pyautogui.move(n * self.offset_unit, 0)
        pyautogui.mouseUp()
    
    def scroll_down(self, n):
        """Scroll vertically"""
        pyautogui.moveTo(self.click_point.x, self.click_point.y)
        pyautogui.scroll(n * self.offset_unit)
    
    def scan_for_black_market(self):
        """Scan the star world for black market"""
        print("Starting black market scan...")
        
        # Move to top-left corner (like star_pick_up.py)
        print("Getting to top-left corner...")
        pyautogui.moveTo(self.click_start.x, self.click_start.y)
        
        # Scroll up to top
        for i in range(10):
            pyautogui.vscroll(200)
            time.sleep(0.1)
        
        # Scroll left to left edge
        for i in range(5):
            pyautogui.moveTo(self.click_start.x, self.click_start.y)
            self.scroll_start(self.scroll_left_step)
            time.sleep(0.5)
        
        print("At top-left corner, starting grid scan...")
        
        # Scan in a grid pattern: 2 rows, scanning left to right
        for row in range(2):
            print(f"Scanning row {row + 1}/2...")
            
            # Scan this row (platform-conditional number of columns)
            for col in range(self.columns):
                print(f"  Checking position [{row},{col}]...")
                time.sleep(0.5)
                
                # Check for black market at current position
                if single_find("BlackMarket"):
                    print("🎉 BLACK MARKET FOUND!")
                    center = get_center("BlackMarket", "Single")
                    print(f"Black Market location: ({center.x / self.sft}, {center.y / self.sft})")
                    
                    # Click on it
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(2)
                    return True
                
                # Scroll right (except on last column)
                if col < (self.columns - 1):
                    print(f"  Scrolling right {col + 1}/{self.columns - 1}...")
                    self.scroll_left_right(self.scroll_right_step)
                    time.sleep(0.5)
            
            # After completing a row, scroll down and back to left (except last row)
            if row < 1:
                print(f"  Moving to next row...")
                self.scroll_down(self.scroll_down_step)
                time.sleep(0.5)
                
                # Scroll back to left edge
                for i in range(self.left_return_iters):
                    pyautogui.moveTo(self.click_start.x, self.click_start.y)
                    self.scroll_start(self.scroll_left_step)
                    time.sleep(0.5)
        
        print("Black market not found after full scan")
        return False
    
    def find_black_market(self):
        """Main method to find black market"""
        print("=" * 60)
        print("BLACK MARKET FINDER")
        print("=" * 60)
        
        if self.scan_for_black_market():
            print("✅ Successfully found and clicked black market!")
            return True
        else:
            print("❌ Black market not found in this scan")
            return False


if __name__ == "__main__":
    finder = BlackMarketFinder()
    finder.find_black_market()
