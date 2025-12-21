"""
Verify Mac Card Matching

Runs template matching on Mac snapshot and draws the matched pairs
to verify that card detection and pairing logic works correctly.
"""

import cv2
import numpy as np
import os
from template_card_matcher import TemplateCardMatcher
from platform_config import get_image_path


class MacMatchingVerifier:
    def __init__(self, image_path="img.png", template_dir="pics/match"):
        """
        Initialize Mac matching verifier.
        
        Args:
            image_path: Path to Mac snapshot image (relative to pics/mac/)
            template_dir: Directory with template cards
        """
        # get_image_path will add pics/mac/ prefix on Mac
        self.image_path = get_image_path(image_path)
        self.template_dir = template_dir
        self.matcher = None
        self.output_image = None
        
    def run_verification(self, threshold=0.7):
        """
        Run template matching and draw results.
        
        Args:
            threshold: Template matching threshold
            
        Returns:
            True if successful, False otherwise
        """
        print("=" * 70)
        print("MAC MATCHING VERIFICATION")
        print("=" * 70)
        
        # Create matcher instance
        self.matcher = TemplateCardMatcher(self.image_path, self.template_dir)
        
        # Load config
        if not self.matcher.load_config_rectangle():
            print("ERROR: Failed to load config")
            return False
        
        # Load templates
        if not self.matcher.load_templates():
            print("ERROR: Failed to load templates")
            return False
        
        # Find matches (this also loads the image)
        if not self.matcher.find_template_matches(threshold):
            print("ERROR: Failed to find template matches")
            return False
        
        # Map to grid
        if not self.matcher.map_to_grid_positions():
            print("ERROR: Failed to map to grid")
            return False
        
        # Find pairs
        pairs = self.matcher.find_pairs()
        if not pairs:
            print("WARNING: No pairs found")
            return False
        
        # Draw results
        self.draw_matches(pairs)
        
        return True
    
    def draw_matches(self, pairs):
        """
        Draw matched pairs on the image.
        
        Args:
            pairs: List of (template_id, template_name, pos1, pos2)
        """
        print("\nDrawing matched pairs on image...")
        
        # Load original image
        img = cv2.imread(self.image_path)
        if img is None:
            print(f"ERROR: Could not load image: {self.image_path}")
            return
        
        self.output_image = img.copy()
        
        # Define colors for different pairs
        colors = [
            (255, 0, 0),    # Blue
            (0, 255, 0),    # Green
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
            (128, 0, 128),  # Purple
            (255, 128, 0),  # Orange
            (0, 128, 255),  # Light Blue
            (128, 255, 0),  # Lime
            (255, 0, 128),  # Pink
            (0, 255, 128),  # Sea Green
            (128, 128, 255),# Lavender
            (255, 128, 128),# Light Red
            (128, 255, 255),# Light Cyan
        ]
        
        for idx, (template_id, template_name, pos1, pos2) in enumerate(pairs):
            color = colors[idx % len(colors)]
            
            # pos1 and pos2 are (cx, cy, row, col) in IMAGE coordinates
            cx1, cy1, row1, col1 = pos1
            cx2, cy2, row2, col2 = pos2
            
            # Draw circles at card centers
            cv2.circle(self.output_image, (int(cx1), int(cy1)), 8, color, -1)
            cv2.circle(self.output_image, (int(cx2), int(cy2)), 8, color, -1)
            
            # Draw line connecting the pair
            cv2.line(self.output_image, (int(cx1), int(cy1)), (int(cx2), int(cy2)), color, 3)
            
            # Draw rectangles around cards (approximate)
            card_half_width = 40
            card_half_height = 60
            
            # Card 1
            pt1_tl = (int(cx1 - card_half_width), int(cy1 - card_half_height))
            pt1_br = (int(cx1 + card_half_width), int(cy1 + card_half_height))
            cv2.rectangle(self.output_image, pt1_tl, pt1_br, color, 2)
            
            # Card 2
            pt2_tl = (int(cx2 - card_half_width), int(cy2 - card_half_height))
            pt2_br = (int(cx2 + card_half_width), int(cy2 + card_half_height))
            cv2.rectangle(self.output_image, pt2_tl, pt2_br, color, 2)
            
            # Add labels
            cv2.putText(self.output_image, f"{idx+1}", (int(cx1) - 10, int(cy1) + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(self.output_image, f"{idx+1}", (int(cx2) - 10, int(cy2) + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Add grid position labels
            cv2.putText(self.output_image, f"({row1},{col1})", (int(cx1) + 15, int(cy1) - 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.putText(self.output_image, f"({row2},{col2})", (int(cx2) + 15, int(cy2) - 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            print(f"  Pair {idx+1}: {template_name}")
            print(f"    Card 1: grid ({row1},{col1}) at image pixel ({cx1}, {cy1})")
            print(f"    Card 2: grid ({row2},{col2}) at image pixel ({cx2}, {cy2})")
    
    def save_output(self, output_path=None):
        """
        Save the annotated image.
        
        Args:
            output_path: Path to save output image
        """
        if self.output_image is None:
            print("ERROR: No output image to save")
            return False
        
        if output_path is None:
            output_path = get_image_path("mac_matching_verification.png")
        
        cv2.imwrite(output_path, self.output_image)
        print(f"\n✅ Output saved to: {output_path}")
        print(f"   Image size: {self.output_image.shape[1]}x{self.output_image.shape[0]}")
        
        return True


def main():
    print("=" * 70)
    print("MAC CARD MATCHING VERIFICATION")
    print("=" * 70)
    print("\nThis script:")
    print("1. Loads the Mac snapshot (pics/mac/img.png)")
    print("2. Runs template matching (excludes flipback.png)")
    print("3. Draws matched pairs with different colors")
    print("4. Saves result to pics/mac/mac_matching_verification.png")
    print("")
    
    verifier = MacMatchingVerifier()
    
    if verifier.run_verification(threshold=0.7):
        verifier.save_output()
        
        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70)
        print("\nCheck the output image to verify:")
        print("  - Each pair has the same color")
        print("  - Pairs are numbered 1, 2, 3, etc.")
        print("  - Grid positions (row, col) are shown")
        print("  - Lines connect matching cards")
        print("")
    else:
        print("\n" + "=" * 70)
        print("VERIFICATION FAILED")
        print("=" * 70)


if __name__ == "__main__":
    main()
