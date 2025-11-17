"""
Test and debug card matching functionality
"""
import cv2
import numpy as np
import os
from log_helper import log


class MatchingTester:
    def __init__(self, image_path="pics/img.png", rows=5, cols=6):
        self.image_path = image_path
        self.rows = rows
        self.cols = cols
        self.cards = []
        
    def extract_cards(self):
        """Extract individual cards from the grid image."""
        log(f"Loading image from {self.image_path}")
        img = cv2.imread(self.image_path)
        if img is None:
            log(f"ERROR: Unable to load image from {self.image_path}")
            return False
            
        height, width = img.shape[:2]
        log(f"Image size: {width}x{height}")
        
        card_width = width // self.cols
        card_height = height // self.rows
        
        log(f"Card dimensions: {card_width}x{card_height}")
        log(f"Extracting {self.rows}x{self.cols} = {self.rows * self.cols} cards")
        
        for row in range(self.rows):
            for col in range(self.cols):
                x1 = col * card_width
                y1 = row * card_height
                x2 = x1 + card_width
                y2 = y1 + card_height
                
                card = img[y1:y2, x1:x2]
                card_id = row * self.cols + col
                
                # Save individual card for inspection
                card_filename = f"test_cards/card_{card_id:02d}_r{row}_c{col}.png"
                os.makedirs("test_cards", exist_ok=True)
                cv2.imwrite(card_filename, card)
                
                self.cards.append({
                    'id': card_id,
                    'image': card,
                    'grid_position': (row, col),
                    'filename': card_filename
                })
                
        log(f"Successfully extracted {len(self.cards)} cards to test_cards/ folder")
        return True
        
    def extract_card_content(self, card_img):
        """Extract the central content area of a card."""
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
    
    def test_pair(self, card1_id, card2_id):
        """Test if two specific cards match."""
        card1 = self.cards[card1_id]
        card2 = self.cards[card2_id]
        
        log(f"\n{'='*70}")
        log(f"Testing Card {card1_id} vs Card {card2_id}")
        log(f"Card {card1_id}: grid position {card1['grid_position']}")
        log(f"Card {card2_id}: grid position {card2['grid_position']}")
        
        # Extract content
        content1 = self.extract_card_content(card1['image'])
        content2 = self.extract_card_content(card2['image'])
        
        # Compute histograms
        hist1 = self.compute_card_histogram(content1)
        hist2 = self.compute_card_histogram(content2)
        
        # Histogram similarity
        hist_sim = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        log(f"Histogram similarity: {hist_sim:.4f}")
        
        # Template matching
        gray1 = cv2.cvtColor(content1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(content2, cv2.COLOR_BGR2GRAY)
        
        if gray1.shape != gray2.shape:
            gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
        
        result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
        template_sim = result[0][0]
        log(f"Template similarity: {template_sim:.4f}")
        
        # Combined
        combined_sim = (hist_sim * 0.5 + template_sim * 0.5)
        log(f"Combined similarity: {combined_sim:.4f}")
        
        # Verdict
        if combined_sim >= 0.45:
            log(f"✓ MATCH (threshold: 0.45)")
        else:
            log(f"✗ NO MATCH (threshold: 0.45)")
        
        # Save comparison image
        comparison = np.hstack([card1['image'], card2['image']])
        comp_filename = f"test_cards/compare_{card1_id}_vs_{card2_id}.png"
        cv2.imwrite(comp_filename, comparison)
        log(f"Comparison saved to: {comp_filename}")
        
        return combined_sim
    
    def find_all_matches(self, threshold=0.45):
        """Find all matching pairs."""
        log(f"\n{'='*70}")
        log(f"Finding all matches (threshold={threshold})")
        log(f"{'='*70}")
        
        matches = []
        
        # Pre-compute features
        card_contents = []
        card_histograms = []
        card_grays = []
        
        for card in self.cards:
            content = self.extract_card_content(card['image'])
            hist = self.compute_card_histogram(content)
            gray = cv2.cvtColor(content, cv2.COLOR_BGR2GRAY)
            
            card_contents.append(content)
            card_histograms.append(hist)
            card_grays.append(gray)
        
        # Compare all pairs
        for i in range(len(self.cards)):
            for j in range(i + 1, len(self.cards)):
                hist_sim = cv2.compareHist(card_histograms[i], card_histograms[j], cv2.HISTCMP_CORREL)
                
                if hist_sim < 0.85:
                    continue
                
                gray1 = card_grays[i]
                gray2 = card_grays[j]
                
                if gray1.shape != gray2.shape:
                    gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
                
                result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
                template_sim = result[0][0]
                
                combined_sim = (hist_sim * 0.5 + template_sim * 0.5)
                
                if combined_sim >= threshold:
                    matches.append((i, j, combined_sim))
        
        log(f"\nFound {len(matches)} potential matches:")
        for i, j, sim in sorted(matches, key=lambda x: x[2], reverse=True):
            pos_i = self.cards[i]['grid_position']
            pos_j = self.cards[j]['grid_position']
            log(f"  Card {i} (grid {pos_i}) <-> Card {j} (grid {pos_j}) - Similarity: {sim:.4f}")
        
        # Get best unique pairs
        sorted_matches = sorted(matches, key=lambda x: x[2], reverse=True)
        paired_cards = set()
        best_pairs = []
        
        for i, j, similarity in sorted_matches:
            if i not in paired_cards and j not in paired_cards:
                best_pairs.append((i, j, similarity))
                paired_cards.add(i)
                paired_cards.add(j)
        
        total_cards = len(self.cards)
        expected_pairs = total_cards // 2
        log(f"\n{'='*70}")
        log(f"Best unique pairs: {len(best_pairs)} (expected {expected_pairs})")
        log(f"{'='*70}")
        
        for idx, (i, j, sim) in enumerate(best_pairs, 1):
            pos_i = self.cards[i]['grid_position']
            pos_j = self.cards[j]['grid_position']
            log(f"{idx}. Card {i} (grid {pos_i}) <-> Card {j} (grid {pos_j}) - {sim:.4f}")
        
        # Check for unpaired cards
        all_cards = set(range(len(self.cards)))
        unpaired_cards = all_cards - paired_cards
        
        if unpaired_cards:
            log(f"\nWARNING: {len(unpaired_cards)} cards remain unpaired:")
            for card_id in sorted(unpaired_cards):
                pos = self.cards[card_id]['grid_position']
                log(f"  - Card {card_id} at grid position {pos}")
        
        return best_pairs
    
    def create_visual_result(self, best_pairs, output_file="test_result.png"):
        """Create a visual representation of matching results."""
        if not self.cards:
            return
        
        card_height, card_width = self.cards[0]['image'].shape[:2]
        
        # Create canvas
        margin = 5
        canvas_height = self.rows * card_height + (self.rows + 1) * margin
        canvas_width = self.cols * card_width + (self.cols + 1) * margin
        canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 240
        
        # Track paired cards
        paired_map = {}
        for idx, (i, j, sim) in enumerate(best_pairs):
            paired_map[i] = (idx, j, sim)
            paired_map[j] = (idx, i, sim)
        
        # Place cards
        for card in self.cards:
            row, col = card['grid_position']
            x = col * card_width + (col + 1) * margin
            y = row * card_height + (row + 1) * margin
            
            canvas[y:y+card_height, x:x+card_width] = card['image']
            
            # Draw border based on pairing
            if card['id'] in paired_map:
                pair_idx, partner_id, sim = paired_map[card['id']]
                # Use color based on pair index
                colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), 
                         (255, 0, 255), (0, 255, 255), (128, 255, 0), (255, 128, 0)]
                color = colors[pair_idx % len(colors)]
                cv2.rectangle(canvas, (x, y), (x+card_width, y+card_height), color, 3)
                
                # Add pair number
                text = f"P{pair_idx+1}"
                cv2.putText(canvas, text, (x+5, y+15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            else:
                # Unpaired - red X
                cv2.rectangle(canvas, (x, y), (x+card_width, y+card_height), (0, 0, 255), 2)
                cv2.line(canvas, (x, y), (x+card_width, y+card_height), (0, 0, 255), 2)
                cv2.line(canvas, (x+card_width, y), (x, y+card_height), (0, 0, 255), 2)
            
            # Add card ID
            text = str(card['id'])
            cv2.putText(canvas, text, (x+card_width-20, y+card_height-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        cv2.imwrite(output_file, canvas)
        log(f"\nVisual result saved to: {output_file}")


def main():
    log("="*70)
    log("CARD MATCHING TEST")
    log("="*70)
    
    tester = MatchingTester()
    
    if not tester.extract_cards():
        log("Failed to extract cards")
        return
    
    # Test all matches with different thresholds
    for threshold in [0.45, 0.40, 0.35, 0.30]:
        log(f"\n\n{'#'*70}")
        log(f"# Testing with threshold = {threshold}")
        log(f"{'#'*70}")
        best_pairs = tester.find_all_matches(threshold=threshold)
        tester.create_visual_result(best_pairs, f"test_result_th{threshold:.2f}.png")
        
        if len(best_pairs) >= 15:
            log(f"\nSUCCESS: Found all pairs with threshold {threshold}")
            break
    
    log("\n" + "="*70)
    log("TEST COMPLETE")
    log("Check test_cards/ folder for individual cards")
    log("Check test_result_*.png for visual results")
    log("="*70)


if __name__ == "__main__":
    main()
