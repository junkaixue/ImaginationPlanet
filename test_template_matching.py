"""
Test template matching and visualize results
"""
import cv2
import numpy as np
import os
from log_helper import log


class TemplateMatchingTester:
    def __init__(self, image_path="pics/img.png", template_dir="pics/match"):
        self.image_path = image_path
        self.template_dir = template_dir
        self.img = None
        self.templates = []
        self.card_positions = []
        
    def load_templates(self):
        """Load all template card images."""
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
            
            # Find all matches
            matches_found = 0
            temp_result = result.copy()
            template_positions = []
            
            while True:
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(temp_result)
                
                if max_val < threshold:
                    break
                
                x, y = max_loc
                center_x = x + template_data['width'] // 2
                center_y = y + template_data['height'] // 2
                
                # Check for duplicates
                is_duplicate = False
                for _, prev_cx, prev_cy, _, _, _, _ in self.card_positions:
                    if abs(center_x - prev_cx) < 60 and abs(center_y - prev_cy) < 60:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    for prev_cx, prev_cy in template_positions:
                        if abs(center_x - prev_cx) < 60 and abs(center_y - prev_cy) < 60:
                            is_duplicate = True
                            break
                
                if not is_duplicate:
                    template_positions.append((center_x, center_y))
                    # Store: template_id, center_x, center_y, x, y, similarity, template_name
                    self.card_positions.append((template_id, center_x, center_y, x, y, max_val, template_name))
                    matches_found += 1
                
                # Mask out region
                h, w = template_gray.shape
                mask_size = max(h, w) // 2
                cv2.rectangle(temp_result, 
                             (max(0, x - mask_size), max(0, y - mask_size)), 
                             (min(temp_result.shape[1], x + w + mask_size), 
                              min(temp_result.shape[0], y + h + mask_size)), 
                             0, -1)
                
                if matches_found >= 2:
                    break
            
            if matches_found > 0:
                log(f"  Template {template_id} ({template_name}): found {matches_found} matches (max similarity: {max_val:.3f})")
        
        log(f"Total card positions found: {len(self.card_positions)}")
        return True
        
    def create_visual_result(self, output_path="test_template_result.png"):
        """Create a visual representation of the matches."""
        log(f"Creating visual result...")
        
        result_img = self.img.copy()
        
        # Define colors for each template
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
            (0, 255, 255), (128, 0, 0), (0, 128, 0), (0, 0, 128), (128, 128, 0),
            (128, 0, 128), (0, 128, 128), (255, 128, 0), (255, 0, 128), (128, 255, 0)
        ]
        
        # Draw rectangles and labels for each match
        for template_id, cx, cy, x, y, similarity, template_name in self.card_positions:
            template_data = self.templates[template_id]
            w = template_data['width']
            h = template_data['height']
            
            # Get color for this template
            color = colors[template_id % len(colors)]
            
            # Draw rectangle
            cv2.rectangle(result_img, (x, y), (x + w, y + h), color, 3)
            
            # Draw label with template name and similarity
            label = f"{template_id}:{template_name.replace('.png', '')} {similarity:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            
            # Get text size for background
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Draw background rectangle for text
            cv2.rectangle(result_img, (x, y - text_h - 10), (x + text_w + 5, y), color, -1)
            
            # Draw text
            cv2.putText(result_img, label, (x + 2, y - 5), font, font_scale, (255, 255, 255), thickness)
        
        # Save result
        cv2.imwrite(output_path, result_img)
        log(f"Visual result saved to: {output_path}")
        
        return result_img
        
    def save_matched_cards(self, output_dir="test_template_cards"):
        """Save individual matched card images."""
        log(f"Saving matched card images to {output_dir}/...")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        for idx, (template_id, cx, cy, x, y, similarity, template_name) in enumerate(self.card_positions):
            template_data = self.templates[template_id]
            w = template_data['width']
            h = template_data['height']
            
            # Extract card image
            card_img = self.img[y:y+h, x:x+w].copy()
            
            # Save with descriptive name
            filename = f"card_{idx:02d}_t{template_id}_{template_name.replace('.png', '')}_sim{similarity:.2f}.png"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, card_img)
        
        log(f"Saved {len(self.card_positions)} card images")
        
    def show_pairs(self):
        """Show which cards are paired."""
        log("\n" + "="*70)
        log("PAIRS FOUND:")
        log("="*70)
        
        # Group by template ID
        template_groups = {}
        for template_id, cx, cy, x, y, similarity, template_name in self.card_positions:
            if template_id not in template_groups:
                template_groups[template_id] = []
            template_groups[template_id].append((cx, cy, similarity))
        
        pair_count = 0
        for template_id, positions in sorted(template_groups.items()):
            template_name = self.templates[template_id]['filename']
            
            if len(positions) == 2:
                log(f"Pair {pair_count + 1}: Template {template_id} ({template_name})")
                log(f"  Card 1: position ({positions[0][0]}, {positions[0][1]}) - similarity {positions[0][2]:.3f}")
                log(f"  Card 2: position ({positions[1][0]}, {positions[1][1]}) - similarity {positions[1][2]:.3f}")
                pair_count += 1
            else:
                log(f"WARNING: Template {template_id} ({template_name}) has {len(positions)} matches (expected 2)")
                for i, (px, py, sim) in enumerate(positions):
                    log(f"  Match {i+1}: position ({px}, {py}) - similarity {sim:.3f}")
        
        log(f"\nTotal valid pairs: {pair_count}")
        log("="*70)


def main():
    """Main test function."""
    log("Template Matching Tester")
    log("="*70)
    
    tester = TemplateMatchingTester()
    
    # Load templates
    if not tester.load_templates():
        log("Failed to load templates")
        return
    
    # Test with different thresholds
    for threshold in [0.8, 0.75, 0.7, 0.65]:
        log(f"\n\n{'#'*70}")
        log(f"# Testing with threshold = {threshold}")
        log(f"{'#'*70}")
        
        if not tester.find_template_matches(threshold=threshold):
            log("Failed to find matches")
            continue
        
        # Show pairs
        tester.show_pairs()
        
        # Save visual result
        tester.create_visual_result(f"test_template_result_th{threshold:.2f}.png")
        
        # Save individual cards
        tester.save_matched_cards(f"test_template_cards_th{threshold:.2f}")
        
        # Check if we found enough pairs
        template_groups = {}
        for template_id, cx, cy, x, y, similarity, template_name in tester.card_positions:
            if template_id not in template_groups:
                template_groups[template_id] = []
            template_groups[template_id].append((cx, cy))
        
        pair_count = sum(1 for positions in template_groups.values() if len(positions) == 2)
        
        if pair_count >= 15:
            log(f"\nSUCCESS: Found all {pair_count} pairs with threshold {threshold}")
            break
    
    log("\n" + "="*70)
    log("TEST COMPLETE")
    log("Check test_template_result_*.png for visual results")
    log("Check test_template_cards_*/ folders for individual cards")
    log("="*70)


if __name__ == "__main__":
    main()
