"""
Automatic Card Matching Game Solver
Analyzes cards in img.png and automatically clicks matching pairs.
Uses rectangle coordinates from config file to map card positions to screen clicks.
"""
import cv2
import numpy as np
import time
import os
from log_helper import log
from config_coords import ConfigCoords
from click import click_at


class AutoCardMatcher:
    def __init__(self, image_path="pics/img.png", rows=5, cols=6):
        """
        Initialize the automatic card matcher.
        
        Args:
            image_path: Path to the screenshot image
            rows: Number of rows in the card grid
            cols: Number of columns in the card grid
        """
        self.image_path = image_path
        self.rows = rows
        self.cols = cols
        self.cards = []
        self.config = None
        self.pair_rect = None  # Rectangle bounds for the card area
        
    def load_config_rectangle(self):
        """Load the card area rectangle from config file."""
        log("Loading rectangle coordinates from config...")
        
        # Check if run_button absolute coords are in config
        import platform
        import os
        is_mac = (platform.system() == "Darwin")
        config_file = "cood_mac.cfg" if is_mac else "cood_win.cfg"
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
            # Use absolute coords from config, create mock ConfigCoords
            from collections import namedtuple
            from common import get_scaling_factor
            Point = namedtuple('Point', ['x', 'y'])
            self.config = ConfigCoords(mock_rb=(int(run_button_abs[0]), int(run_button_abs[1])))
        else:
            # Auto-detect Run Button
            self.config = ConfigCoords()
        
        # Get rectangle corners (relative to Run Button)
        top_left = self.config.get_coord("pair_top_left")
        bottom_right = self.config.get_coord("pair_bottom_right")
        
        if not top_left or not bottom_right:
            log("ERROR: Rectangle coordinates not found in config file!")
            log("Please ensure pair_top_left and pair_bottom_right are defined in the config.")
            return False
            
        self.pair_rect = {
            'x1': top_left[0],
            'y1': top_left[1],
            'x2': bottom_right[0],
            'y2': bottom_right[1],
            'width': bottom_right[0] - top_left[0],
            'height': bottom_right[1] - top_left[1]
        }
        
        log(f"Rectangle area loaded:")
        log(f"  Top-left: ({self.pair_rect['x1']:.1f}, {self.pair_rect['y1']:.1f})")
        log(f"  Bottom-right: ({self.pair_rect['x2']:.1f}, {self.pair_rect['y2']:.1f})")
        log(f"  Size: {self.pair_rect['width']:.1f} x {self.pair_rect['height']:.1f}")
        
        return True
        
    def extract_cards(self):
        """Extract individual cards from the grid image."""
        log(f"Loading image from {self.image_path}")
        img = cv2.imread(self.image_path)
        if img is None:
            log(f"ERROR: Unable to load image from {self.image_path}")
            log("Please ensure you have saved a screenshot as pics/img.png")
            return False
            
        height, width = img.shape[:2]
        log(f"Image size: {width}x{height}")
        
        # Calculate card dimensions
        card_width = width // self.cols
        card_height = height // self.rows
        
        log(f"Card dimensions: {card_width}x{card_height}")
        total_cards = self.rows * self.cols
        expected_pairs = total_cards // 2
        log(f"Extracting {self.rows}x{self.cols} = {total_cards} cards ({expected_pairs} pairs expected)")
        
        # Extract each card
        for row in range(self.rows):
            for col in range(self.cols):
                # Calculate card boundaries
                x1 = col * card_width
                y1 = row * card_height
                x2 = x1 + card_width
                y2 = y1 + card_height
                
                # Extract card image
                card = img[y1:y2, x1:x2]
                card_id = row * self.cols + col
                
                # Store card
                self.cards.append({
                    'id': card_id,
                    'image': card,
                    'grid_position': (row, col),
                    'matched': False
                })
                
        log(f"Successfully extracted {len(self.cards)} cards")
        return True
        
    def extract_card_content(self, card_img):
        """Extract the central content area of a card (the icon)."""
        height, width = card_img.shape[:2]
        margin_x = int(width * 0.15)
        margin_y = int(height * 0.25)
        content = card_img[margin_y:height-margin_y, margin_x:width-margin_x]
        return content
    
    def compute_card_histogram(self, card_img):
        """Compute color histogram for card comparison."""
        hsv = cv2.cvtColor(card_img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        return hist
    
    def find_matching_pairs(self, similarity_threshold=0.50):
        """Find matching pairs using histogram and template matching."""
        log("Analyzing cards to find matching pairs...")
        log("Pre-computing card features...")
        
        # Extract content areas and compute histograms (pre-compute once)
        card_contents = []
        card_histograms = []
        card_grays = []
        
        for idx, card in enumerate(self.cards):
            content = self.extract_card_content(card['image'])
            hist = self.compute_card_histogram(content)
            gray = cv2.cvtColor(content, cv2.COLOR_BGR2GRAY)
            
            card_contents.append(content)
            card_histograms.append(hist)
            card_grays.append(gray)
            
            if (idx + 1) % 10 == 0:
                log(f"  Processed {idx + 1}/{len(self.cards)} cards...")
        
        log(f"Comparing {len(self.cards)} cards (this may take a moment)...")
        matches = []
        total_comparisons = len(self.cards) * (len(self.cards) - 1) // 2
        comparison_count = 0
        
        # Compare all pairs
        for i in range(len(self.cards)):
            for j in range(i + 1, len(self.cards)):
                comparison_count += 1
                
                # Progress update every 100 comparisons
                if comparison_count % 100 == 0:
                    log(f"  Compared {comparison_count}/{total_comparisons} pairs...")
                
                # Histogram comparison (fast)
                hist_sim = cv2.compareHist(card_histograms[i], card_histograms[j], cv2.HISTCMP_CORREL)
                
                # Skip template matching if histogram similarity is too low
                if hist_sim < 0.85:
                    continue
                
                # Template matching on content area (slower)
                gray1 = card_grays[i]
                gray2 = card_grays[j]
                
                if gray1.shape != gray2.shape:
                    gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
                
                result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
                template_sim = result[0][0]
                
                # Combined similarity
                combined_sim = (hist_sim * 0.5 + template_sim * 0.5)
                
                if combined_sim >= similarity_threshold:
                    matches.append((i, j, combined_sim))
                    
        log(f"Found {len(matches)} potential matches")
        return matches
        
    def get_best_pairs(self, matches):
        """Extract best unique pairs ensuring each card matches exactly one other."""
        sorted_matches = sorted(matches, key=lambda x: x[2], reverse=True)
        
        paired_cards = set()
        best_pairs = []
        
        for i, j, similarity in sorted_matches:
            if i not in paired_cards and j not in paired_cards:
                best_pairs.append((i, j, similarity))
                paired_cards.add(i)
                paired_cards.add(j)
                
        # Check for unpaired cards
        all_cards = set(range(len(self.cards)))
        unpaired_cards = all_cards - paired_cards
        
        if unpaired_cards:
            log(f"WARNING: {len(unpaired_cards)} cards remain unpaired:")
            for card_id in sorted(unpaired_cards):
                pos = self.cards[card_id]['grid_position']
                log(f"  - Card {card_id} at grid position {pos}")
            log(f"TIP: Try lowering similarity_threshold if cards are missing")
                
        return best_pairs
    
    def calculate_screen_position(self, grid_row, grid_col):
        """
        Calculate the screen click position for a card based on its grid position.
        
        Args:
            grid_row: Row in the 5x6 grid (0-4)
            grid_col: Column in the 5x6 grid (0-5)
            
        Returns:
            (x, y) tuple of screen coordinates
        """
        # Card spacing: horizontal +123, vertical +170 from card center to card center
        horizontal_spacing = 123
        vertical_spacing = 170
        
        # pair_top_left is the center of the first card (row 0, col 0)
        # Calculate position by adding offset based on grid position
        abs_x = self.pair_rect['x1'] + (grid_col * horizontal_spacing)
        abs_y = self.pair_rect['y1'] + (grid_row * vertical_spacing)
        
        return (abs_x, abs_y)
    
    def click_pair(self, card1_id, card2_id, delay_between=0.5, delay_after=2.0):
        """
        Click a pair of matching cards.
        
        Args:
            card1_id: ID of first card
            card2_id: ID of second card
            delay_between: Delay between clicking first and second card (seconds)
            delay_after: Delay after clicking the pair (seconds)
        """
        card1 = self.cards[card1_id]
        card2 = self.cards[card2_id]
        
        row1, col1 = card1['grid_position']
        row2, col2 = card2['grid_position']
        
        # Calculate screen positions
        x1, y1 = self.calculate_screen_position(row1, col1)
        x2, y2 = self.calculate_screen_position(row2, col2)
        
        log(f"Clicking pair: Card {card1_id} (grid {row1},{col1}) <-> Card {card2_id} (grid {row2},{col2})")
        
        # Click first card
        log(f"  Click 1: ({x1:.1f}, {y1:.1f})")
        click_at(x1, y1)
        time.sleep(delay_between)
        
        # Click second card
        log(f"  Click 2: ({x2:.1f}, {y2:.1f})")
        click_at(x2, y2)
        time.sleep(delay_after)
        
    def solve_and_click(self, click_delay_between=0.5, click_delay_after=2.0, dry_run=False, similarity_threshold=0.50):
        """
        Main function: analyze cards and automatically click all matching pairs.
        
        Args:
            click_delay_between: Delay between clicking two cards in a pair (seconds)
            click_delay_after: Delay after completing a pair before next pair (seconds)
            dry_run: If True, only print what would be clicked (don't actually click)
            similarity_threshold: Threshold for matching (0-1, lower = more lenient)
        """
        log("="*70)
        log("AUTOMATIC CARD MATCHER - Starting")
        log("="*70)
        
        # Load rectangle coordinates
        if not self.load_config_rectangle():
            return False
            
        # Extract cards from image
        if not self.extract_cards():
            return False
            
        # Find matching pairs
        matches = self.find_matching_pairs(similarity_threshold)
        best_pairs = self.get_best_pairs(matches)
        
        total_cards = self.rows * self.cols
        expected_pairs = total_cards // 2
        log(f"\nFound {len(best_pairs)} matching pairs (expected {expected_pairs})")
        if len(best_pairs) < expected_pairs:
            log(f"WARNING: Missing {expected_pairs - len(best_pairs)} pairs. Consider lowering threshold.")
        log("="*70)
        
        if dry_run:
            log("DRY RUN MODE - Will not actually click")
            
        # Click each pair
        for idx, (card1_id, card2_id, similarity) in enumerate(best_pairs, 1):
            card1 = self.cards[card1_id]
            card2 = self.cards[card2_id]
            
            progress = f"[{idx}/{len(best_pairs)}]"
            log(f"\n{progress} Pair similarity: {similarity:.3f}")
            
            if dry_run:
                row1, col1 = card1['grid_position']
                row2, col2 = card2['grid_position']
                x1, y1 = self.calculate_screen_position(row1, col1)
                x2, y2 = self.calculate_screen_position(row2, col2)
                log(f"  [DRY RUN] Would click Card {card1_id} at ({x1:.1f}, {y1:.1f})")
                log(f"  [DRY RUN] Would click Card {card2_id} at ({x2:.1f}, {y2:.1f})")
            else:
                self.click_pair(card1_id, card2_id, click_delay_between, click_delay_after)
                
        # Final timing report
        if not dry_run and len(best_pairs) > 0:
            total_time = len(best_pairs) * (click_delay_between + click_delay_after)
            log(f"\nTotal click time: ~{total_time:.1f} seconds for {len(best_pairs)} pairs")
                
        log("="*70)
        log(f"COMPLETE - Processed {len(best_pairs)} pairs")
        log("="*70)
        
        return True


def main():
    """Main entry point."""
    import sys
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    log("Automatic Card Matcher")
    log("=" * 70)
    log("INSTRUCTIONS:")
    log("1. Take a screenshot of the card matching game")
    log("2. Save it as pics/img.png")
    log("3. Run this script")
    log("4. The script will automatically click all matching pairs")
    log("")
    log("Make sure:")
    log("  - The game window is visible and in focus")
    log("  - pair_top_left and pair_bottom_right are correctly configured")
    log("  - You have saved the screenshot as pics/img.png")
    log("=" * 70)
    
    if dry_run:
        log("\n*** DRY RUN MODE - Will not actually click ***\n")
    
    # Wait a moment before starting
    log("\nStarting in 2 seconds...")
    time.sleep(2)
    
    # Create matcher and run
    matcher = AutoCardMatcher()
    matcher.solve_and_click(
        click_delay_between=0.0,   # 0.2 seconds between cards in a pair
        click_delay_after=0.2,     # No delay after pair (immediate next pair)
        similarity_threshold=0.30, # Threshold 0.45 catches all 15 pairs
        dry_run=dry_run
    )


if __name__ == "__main__":
    main()
