"""
Mac Card Matcher using common.py template finding

Uses the same template matching logic as running.py (which works on Mac).
Works with saved snapshot image (pics/mac/img.png).
"""

import os
import time
import cv2
import numpy as np
import platform
from log_helper import log
from click import click_at
from common import find_all_with_path, get_scaling_factor
from platform_config import get_image_path


class MacCardMatcher:
    def __init__(self, image_path="img.png", template_dir=None, snapshot_offset=(0, 0)):
        """Initialize Mac card matcher.
        
        Args:
            image_path: Path to snapshot image (relative, gets pics/mac/ prefix on Mac)
            template_dir: Directory with template images (defaults to platform-specific)
            snapshot_offset: (x, y) offset of snapshot top-left corner on screen (for coordinate conversion)
        """
        self.image_path = get_image_path(image_path)
        
        # Use platform-specific template directory if not specified
        if template_dir is None:
            if platform.system() == "Darwin":
                template_dir = "pics/mac/match"
            else:
                template_dir = "pics/match"
        
        self.template_dir = template_dir
        self.templates = []
        self.card_positions = []  # List of (template_id, cx, cy, template_name)
        self.gray_screen = None
        self.snapshot_offset = snapshot_offset
        self.scaling_factor = get_scaling_factor()
        
    def load_templates(self):
        """Load all card template paths."""
        log(f"Platform: {platform.system()}")
        log(f"Loading templates from {self.template_dir}...")
        
        skip_files = {'flipback.png'}
        template_files = sorted([f for f in os.listdir(self.template_dir)
                                if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                                and f not in skip_files])
        
        for filename in template_files:
            filepath = os.path.join(self.template_dir, filename)
            template_id = len(self.templates)
            
            self.templates.append({
                'id': template_id,
                'filename': filename,
                'path': filepath
            })
            log(f"  Template {template_id}: {filename}")
        
        log(f"Loaded {len(self.templates)} card templates")
        return len(self.templates) > 0
    
    def find_all_cards(self, threshold=0.7):
        """Find all cards in snapshot image using template matching.
        
        NOTE: Snapshot is scaled 2x in auto_snapshot_solver to match template resolution.
        So image coordinates are already in physical pixels matching templates.
        """
        log(f"Loading snapshot and finding cards (threshold={threshold})...")
        log(f"Snapshot path: {self.image_path}")
        log(f"Snapshot offset: ({self.snapshot_offset[0]}, {self.snapshot_offset[1]})")
        log(f"Scaling factor: {self.scaling_factor}")
        log(f"Coordinate conversion: Image(physical) → +offset → Screen(physical) → ÷{self.scaling_factor} → Logical")
        
        # Load snapshot image (already scaled to physical resolution in auto_snapshot_solver)
        img = cv2.imread(self.image_path)
        if img is None:
            log(f"ERROR: Could not load image from {self.image_path}")
            return False
        
        log(f"Image size: {img.shape[1]}x{img.shape[0]} (physical pixels)")
        
        # Convert to grayscale (same as common.py screen_shot())
        self.gray_screen = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        self.card_positions = []
        
        for template_data in self.templates:
            template_id = template_data['id']
            template_name = template_data['filename']
            template_path = template_data['path']
            
            # Use find_all_with_path from common.py
            matches = find_all_with_path(template_path, self.gray_screen, threshold)
            
            for cx_img, cy_img, confidence in matches:
                # Convert image coordinates to screen coordinates for clicking
                # 1. Add snapshot offset to get physical screen pixels
                cx_physical = cx_img + self.snapshot_offset[0]
                cy_physical = cy_img + self.snapshot_offset[1]
                
                # 2. Convert to logical coordinates for clicking (Mac Quartz expects logical coords)
                cx_logical = cx_physical / self.scaling_factor
                cy_logical = cy_physical / self.scaling_factor
                
                self.card_positions.append((template_id, cx_logical, cy_logical, template_name))
                log(f"  Found {template_name}:")
                log(f"    Image coords: ({cx_img}, {cy_img})")
                log(f"    Physical screen: ({cx_physical}, {cy_physical})")
                log(f"    Logical coords: ({cx_logical:.1f}, {cy_logical:.1f})")
                log(f"    Confidence: {confidence:.3f}")
        
        log(f"Found {len(self.card_positions)} total cards")
        return True
    
    def find_pairs(self):
        """Group cards by template to find matching pairs."""
        log("Finding matching pairs...")
        
        # Group by template ID
        template_groups = {}
        for template_id, cx, cy, template_name in self.card_positions:
            if template_id not in template_groups:
                template_groups[template_id] = []
            template_groups[template_id].append((cx, cy, template_name))
        
        pairs = []
        for template_id, positions in template_groups.items():
            if len(positions) == 2:
                pos1 = positions[0]
                pos2 = positions[1]
                template_name = pos1[2]
                pairs.append((template_id, template_name, pos1, pos2))
                log(f"  Pair: {template_name}")
                log(f"    Card 1: ({pos1[0]}, {pos1[1]})")
                log(f"    Card 2: ({pos2[0]}, {pos2[1]})")
            elif len(positions) != 2:
                template_name = positions[0][2] if positions else "unknown"
                log(f"  WARNING: {template_name} has {len(positions)} matches (expected 2)")
        
        log(f"Found {len(pairs)} valid pairs")
        return pairs
    
    def click_pair(self, pos1, pos2, delay_between=0.2, delay_after=0.0):
        """Click a pair of cards.
        
        Coordinates are already in logical format (scaled for Mac Retina).
        """
        cx1, cy1, name1 = pos1
        cx2, cy2, name2 = pos2
        
        log(f"  Click 1: {name1} at ({cx1:.1f}, {cy1:.1f})")
        click_at(cx1, cy1)
        time.sleep(delay_between)
        
        log(f"  Click 2: {name2} at ({cx2:.1f}, {cy2:.1f})")
        click_at(cx2, cy2)
        time.sleep(delay_after)
    
    def solve_and_click(self, threshold=0.7, click_delay_between=0.2, click_delay_after=0.35, dry_run=False):
        """Main function to find and click all pairs."""
        log("="*70)
        log("MAC CARD MATCHER - Starting")
        log("="*70)
        
        # Load templates
        if not self.load_templates():
            log("ERROR: No templates loaded")
            return False
        
        # Find all cards
        if not self.find_all_cards(threshold):
            log("ERROR: Failed to find cards")
            return False
        
        # Find pairs
        pairs = self.find_pairs()
        
        if not pairs:
            log("WARNING: No pairs found")
            return False
        
        log("="*70)
        if dry_run:
            log("DRY RUN MODE - Will not actually click")
        
        # Click each pair
        for idx, (template_id, template_name, pos1, pos2) in enumerate(pairs, 1):
            log(f"\n[{idx}/{len(pairs)}] Clicking pair: {template_name}")
            
            if dry_run:
                log(f"  [DRY RUN] Would click ({pos1[0]:.1f}, {pos1[1]:.1f})")
                log(f"  [DRY RUN] Would click ({pos2[0]:.1f}, {pos2[1]:.1f})")
            else:
                self.click_pair(pos1, pos2, click_delay_between, click_delay_after)
        
        log("\n" + "="*70)
        log(f"COMPLETE - Processed {len(pairs)} pairs")
        log("="*70)
        
        return True


def main():
    import sys
    
    print("=" * 70)
    print("MAC CARD MATCHER TEST")
    print("=" * 70)
    print("\nUsing template matching from common.py")
    print("(Same logic as running.py - Mac compatible)")
    print("")
    print("Coordinate conversion:")
    print("  Image pixels → + snapshot_offset → Physical screen pixels")
    print("  Physical pixels → ÷ scaling_factor → Logical coords for clicking")
    print("")
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    if dry_run:
        print("*** DRY RUN MODE - Will not actually click ***")
        print("(Remove --dry-run flag to enable clicking)")
    else:
        print("*** LIVE MODE - Will click cards ***")
        print("(Add --dry-run flag to test without clicking)")
    print("")
    
    matcher = MacCardMatcher()
    matcher.solve_and_click(
        threshold=0.75,
        click_delay_between=0.3,
        click_delay_after=0.5,
        dry_run=dry_run
    )


if __name__ == "__main__":
    main()
