"""
Template-Based Card Matcher
Uses pre-saved card templates from pics/match/ to find matching pairs in img.png
"""
import cv2
import numpy as np
import os
import time
from log_helper import log
from config_coords import ConfigCoords
from click import click_at


class TemplateCardMatcher:
    def __init__(self, image_path="pics/img.png", template_dir="pics/match"):
        """
        Initialize template-based matcher.
        
        Args:
            image_path: Path to the screenshot with all cards
            template_dir: Directory containing template card images
        """
        self.image_path = image_path
        self.template_dir = template_dir
        self.img = None
        self.templates = []
        self.card_positions = []  # List of (template_idx, center_x, center_y, row, col)
        self.config = None
        self.pair_top_left = None
        
    def load_config_rectangle(self):
        """Load the card area coordinates from config file."""
        log("Loading rectangle coordinates from config...")
        
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
            from collections import namedtuple
            Point = namedtuple('Point', ['x', 'y'])
            self.config = ConfigCoords(mock_rb=(int(run_button_abs[0]), int(run_button_abs[1])))
        else:
            self.config = ConfigCoords()
        
        # Get pair_top_left (center of first card)
        top_left = self.config.get_coord("pair_top_left")
        
        if not top_left:
            log("ERROR: pair_top_left not found in config file!")
            return False
            
        self.pair_top_left = top_left
        log(f"Card grid top-left (card 0,0 center): ({self.pair_top_left[0]:.1f}, {self.pair_top_left[1]:.1f})")
        
        return True
        
    def load_templates(self):
        """Load all template card images from the template directory."""
        log(f"Loading card templates from {self.template_dir}...")
        
        if not os.path.exists(self.template_dir):
            log(f"ERROR: Template directory not found: {self.template_dir}")
            return False
        
        template_files = sorted([f for f in os.listdir(self.template_dir) 
                                if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        
        if not template_files:
            log(f"ERROR: No template images found in {self.template_dir}")
            return False
        
        for idx, filename in enumerate(template_files):
            filepath = os.path.join(self.template_dir, filename)
            template = cv2.imread(filepath, cv2.IMREAD_COLOR)
            
            if template is None:
                log(f"WARNING: Could not load {filename}")
                continue
            
            # Store template info
            h, w = template.shape[:2]
            self.templates.append({
                'id': idx,
                'filename': filename,
                'image': template,
                'height': h,
                'width': w
            })
            log(f"  Loaded template {idx}: {filename} ({w}x{h})")
        
        log(f"Loaded {len(self.templates)} card templates")
        return len(self.templates) > 0
        
    def find_template_matches(self, threshold=0.8):
        """Find all instances of each template in the main image."""
        log(f"Loading main image from {self.image_path}...")
        self.img = cv2.imread(self.image_path)
        
        if self.img is None:
            log(f"ERROR: Could not load image from {self.image_path}")
            return False
        
        log(f"Image size: {self.img.shape[1]}x{self.img.shape[0]}")
        
        # Convert main image to grayscale
        gray_screen = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        log(f"Searching for card matches (threshold={threshold})...")
        
        self.card_positions = []
        
        for template_data in self.templates:
            template_id = template_data['id']
            template_name = template_data['filename']
            
            # Convert template to grayscale
            template_gray = cv2.cvtColor(template_data['image'], cv2.COLOR_BGR2GRAY)
            
            # Perform template matching
            result = cv2.matchTemplate(gray_screen, template_gray, cv2.TM_CCOEFF_NORMED)
            
            # Find all matches by iterating and masking found regions
            matches_found = 0
            temp_result = result.copy()
            template_positions = []  # Track positions for this template
            
            while True:
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(temp_result)
                
                if max_val < threshold:
                    break
                
                # Found a match
                x, y = max_loc
                center_x = x + template_data['width'] // 2
                center_y = y + template_data['height'] // 2
                
                # Check if this position is too close to ANY previous match (global dedup)
                is_duplicate = False
                
                # Check against all previously found cards
                for _, prev_cx, prev_cy, _, _ in self.card_positions:
                    if abs(center_x - prev_cx) < 60 and abs(center_y - prev_cy) < 60:
                        is_duplicate = True
                        break
                
                # Also check within this template's matches
                if not is_duplicate:
                    for prev_cx, prev_cy in template_positions:
                        if abs(center_x - prev_cx) < 60 and abs(center_y - prev_cy) < 60:
                            is_duplicate = True
                            break
                
                if not is_duplicate:
                    template_positions.append((center_x, center_y))
                    self.card_positions.append((template_id, center_x, center_y, -1, -1))
                    matches_found += 1
                
                # Mask out this region to find next match
                h, w = template_gray.shape
                mask_size = max(h, w) // 2  # Use larger mask to avoid nearby duplicates
                cv2.rectangle(temp_result, 
                             (max(0, x - mask_size), max(0, y - mask_size)), 
                             (min(temp_result.shape[1], x + w + mask_size), 
                              min(temp_result.shape[0], y + h + mask_size)), 
                             0, -1)
                
                # Only expect 2 matches per template
                if matches_found >= 2:
                    break
            
            if matches_found > 0:
                log(f"  Template {template_id} ({template_name}): found {matches_found} matches")
        
        log(f"Total card positions found: {len(self.card_positions)}")
        return True
        
    def map_to_grid_positions(self):
        """Map image pixel positions to grid coordinates."""
        log("Mapping positions to grid coordinates...")
        
        # These are IMAGE coordinates, not screen coordinates
        # We need to cluster them into a 5x6 grid
        
        # Sort all positions by y first, then by x
        sorted_positions = sorted(self.card_positions, key=lambda p: (p[2], p[1]))
        
        # Extract all y and x coordinates
        all_y = sorted([p[2] for p in sorted_positions])
        all_x = sorted([p[1] for p in sorted_positions])
        
        # Cluster Y coordinates into 5 rows
        # Group Y values that are within tolerance of each other
        row_clusters = []
        tolerance = 30  # pixels
        
        for y in all_y:
            # Find if this y belongs to existing cluster
            found = False
            for cluster in row_clusters:
                if abs(y - cluster[0]) < tolerance:
                    cluster.append(y)
                    found = True
                    break
            if not found:
                row_clusters.append([y])
        
        # Take average of each cluster as the row position
        row_positions = sorted([sum(cluster) / len(cluster) for cluster in row_clusters])
        
        # Cluster X coordinates into 6 columns
        col_clusters = []
        for x in all_x:
            found = False
            for cluster in col_clusters:
                if abs(x - cluster[0]) < tolerance:
                    cluster.append(x)
                    found = True
                    break
            if not found:
                col_clusters.append([x])
        
        col_positions = sorted([sum(cluster) / len(cluster) for cluster in col_clusters])
        
        log(f"Clustered into {len(row_positions)} rows and {len(col_positions)} columns")
        log(f"Row Y positions: {[int(y) for y in row_positions]}")
        log(f"Col X positions: {[int(x) for x in col_positions]}")
        
        updated_positions = []
        for template_id, cx, cy, _, _ in sorted_positions:
            # Find closest row
            row = min(range(len(row_positions)), key=lambda i: abs(cy - row_positions[i]))
            
            # Find closest column
            col = min(range(len(col_positions)), key=lambda i: abs(cx - col_positions[i]))
            
            updated_positions.append((template_id, cx, cy, row, col))
            log(f"  Template {template_id}: image pixel ({cx}, {cy}) -> grid ({row}, {col})")
        
        self.card_positions = updated_positions
        return True
        
    def find_pairs(self):
        """Find matching pairs from the detected cards."""
        log("Finding matching pairs...")
        
        # Group cards by template ID
        template_groups = {}
        for template_id, cx, cy, row, col in self.card_positions:
            if template_id not in template_groups:
                template_groups[template_id] = []
            template_groups[template_id].append((cx, cy, row, col))
        
        pairs = []
        for template_id, positions in template_groups.items():
            if len(positions) == 2:
                template_name = self.templates[template_id]['filename']
                pos1 = positions[0]
                pos2 = positions[1]
                pairs.append((template_id, template_name, pos1, pos2))
                log(f"  Pair found: Template {template_id} ({template_name})")
                log(f"    Card 1: grid ({pos1[2]}, {pos1[3]}) at ({pos1[0]}, {pos1[1]})")
                log(f"    Card 2: grid ({pos2[2]}, {pos2[3]}) at ({pos2[0]}, {pos2[1]})")
            elif len(positions) != 2:
                template_name = self.templates[template_id]['filename']
                log(f"  WARNING: Template {template_id} ({template_name}) has {len(positions)} matches (expected 2)")
        
        log(f"Found {len(pairs)} valid pairs")
        return pairs
        
    def calculate_click_position(self, row, col):
        """Calculate click position from grid coordinates."""
        horizontal_spacing = 123
        vertical_spacing = 170
        
        abs_x = self.pair_top_left[0] + (col * horizontal_spacing)
        abs_y = self.pair_top_left[1] + (row * vertical_spacing)
        
        return (abs_x, abs_y)
        
    def click_pair(self, pos1, pos2, delay_between=0.2, delay_after=0.0):
        """Click a pair of cards."""
        row1, col1 = pos1[2], pos1[3]
        row2, col2 = pos2[2], pos2[3]
        
        x1, y1 = self.calculate_click_position(row1, col1)
        x2, y2 = self.calculate_click_position(row2, col2)
        
        log(f"  Click 1: grid ({row1},{col1}) at ({x1:.1f}, {y1:.1f})")
        click_at(x1, y1)
        time.sleep(delay_between)
        
        log(f"  Click 2: grid ({row2},{col2}) at ({x2:.1f}, {y2:.1f})")
        click_at(x2, y2)
        time.sleep(delay_after)
        
    def solve_and_click(self, threshold=0.8, click_delay_between=0.2, click_delay_after=0.0, dry_run=False):
        """Main function to solve and click all pairs."""
        log("="*70)
        log("TEMPLATE-BASED CARD MATCHER - Starting")
        log("="*70)
        
        # Load config
        if not self.load_config_rectangle():
            return False
        
        # Load templates
        if not self.load_templates():
            return False
        
        # Find matches
        if not self.find_template_matches(threshold):
            return False
        
        # Map to grid
        if not self.map_to_grid_positions():
            return False
        
        # Find pairs
        pairs = self.find_pairs()
        
        if len(pairs) == 0:
            log("ERROR: No pairs found!")
            return False
        
        log("="*70)
        if dry_run:
            log("DRY RUN MODE - Will not actually click")
        
        # Click each pair
        for idx, (template_id, template_name, pos1, pos2) in enumerate(pairs, 1):
            log(f"\n[{idx}/{len(pairs)}] Clicking pair: Template {template_id} ({template_name})")
            
            if dry_run:
                row1, col1 = pos1[2], pos1[3]
                row2, col2 = pos2[2], pos2[3]
                x1, y1 = self.calculate_click_position(row1, col1)
                x2, y2 = self.calculate_click_position(row2, col2)
                log(f"  [DRY RUN] Would click grid ({row1},{col1}) at ({x1:.1f}, {y1:.1f})")
                log(f"  [DRY RUN] Would click grid ({row2},{col2}) at ({x2:.1f}, {y2:.1f})")
            else:
                self.click_pair(pos1, pos2, click_delay_between, click_delay_after)
        
        log("\n" + "="*70)
        log(f"COMPLETE - Processed {len(pairs)} pairs")
        log("="*70)
        
        return True


def main():
    """Main entry point."""
    import sys
    
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    log("Template-Based Card Matcher")
    log("=" * 70)
    log("INSTRUCTIONS:")
    log("1. Save template card images in pics/match/")
    log("2. Take a screenshot of the game and save as pics/img.png")
    log("3. Run this script")
    log("4. The script will find and click matching pairs")
    log("")
    log("Make sure:")
    log("  - Template images are in pics/match/")
    log("  - Screenshot saved as pics/img.png")
    log("  - pair_top_left configured in config file")
    log("  - Game window is visible and in focus")
    log("=" * 70)
    
    if dry_run:
        log("\n*** DRY RUN MODE - Will not actually click ***\n")
    
    log("\nStarting in 2 seconds...")
    #time.sleep(2)
    
    matcher = TemplateCardMatcher()
    matcher.solve_and_click(
        threshold=0.7,              # Template match threshold
        click_delay_between=0.5,    # Delay between cards in pair
        click_delay_after=1,      # Delay after pair
        dry_run=dry_run
    )


if __name__ == "__main__":
    main()
