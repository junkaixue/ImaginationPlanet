"""
Card Matching Game
Extracts cards from a grid image and creates an interactive matching game.
"""
import cv2
import numpy as np
import random
import os
from log_helper import log


class CardMatchingGame:
    def __init__(self, image_path, rows=5, cols=6):
        """
        Initialize the card matching game.
        
        Args:
            image_path: Path to the grid image
            rows: Number of rows in the grid
            cols: Number of columns in the grid
        """
        self.image_path = image_path
        self.rows = rows
        self.cols = cols
        self.cards = []
        self.card_positions = {}
        self.pairs_found = []
        self.selected_cards = []
        self.attempts = 0
        self.matches = 0
        
    def extract_cards(self):
        """Extract individual cards from the grid image."""
        log(f"Loading image from {self.image_path}")
        img = cv2.imread(self.image_path)
        if img is None:
            log(f"Error: Unable to load image from {self.image_path}")
            return False
            
        height, width = img.shape[:2]
        log(f"Image size: {width}x{height}")
        
        # Calculate card dimensions (with some margin)
        card_width = width // self.cols
        card_height = height // self.rows
        
        log(f"Card dimensions: {card_width}x{card_height}")
        log(f"Extracting {self.rows}x{self.cols} = {self.rows * self.cols} cards")
        
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
                    'position': (row, col),
                    'matched': False
                })
                
        log(f"Successfully extracted {len(self.cards)} cards")
        return True
        
    def extract_card_content(self, card_img):
        """
        Extract the central content area of a card (the icon), removing borders.
        
        Args:
            card_img: Card image
            
        Returns:
            Cropped card content
        """
        height, width = card_img.shape[:2]
        # Crop to central area (remove borders)
        margin_x = int(width * 0.15)
        margin_y = int(height * 0.25)
        content = card_img[margin_y:height-margin_y, margin_x:width-margin_x]
        return content
    
    def compute_card_histogram(self, card_img):
        """
        Compute color histogram for card comparison.
        
        Args:
            card_img: Card image
            
        Returns:
            Normalized histogram
        """
        # Convert to HSV for better color matching
        hsv = cv2.cvtColor(card_img, cv2.COLOR_BGR2HSV)
        # Calculate histogram
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
        # Normalize
        hist = cv2.normalize(hist, hist).flatten()
        return hist
    
    def find_matching_pairs(self, similarity_threshold=0.75):
        """
        Find matching pairs using multiple methods: histogram comparison and template matching.
        
        Args:
            similarity_threshold: Threshold for considering cards as matching (0-1)
        """
        log("Finding matching pairs...")
        matches = []
        
        # Extract content areas and compute histograms
        card_contents = []
        card_histograms = []
        
        for card in self.cards:
            content = self.extract_card_content(card['image'])
            hist = self.compute_card_histogram(content)
            card_contents.append(content)
            card_histograms.append(hist)
        
        # Compare all pairs
        for i in range(len(self.cards)):
            for j in range(i + 1, len(self.cards)):
                # Method 1: Histogram comparison
                hist_sim = cv2.compareHist(card_histograms[i], card_histograms[j], cv2.HISTCMP_CORREL)
                
                # Method 2: Template matching on content area
                content1 = card_contents[i]
                content2 = card_contents[j]
                
                # Convert to grayscale
                gray1 = cv2.cvtColor(content1, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(content2, cv2.COLOR_BGR2GRAY)
                
                # Resize to same size if needed
                if gray1.shape != gray2.shape:
                    gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
                
                # Template matching
                result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
                template_sim = result[0][0]
                
                # Combined similarity (weighted average)
                combined_sim = (hist_sim * 0.5 + template_sim * 0.5)
                
                if combined_sim >= similarity_threshold:
                    matches.append((i, j, combined_sim, hist_sim, template_sim))
                    
        log(f"Found {len(matches)} matching pairs")
        
        # Group matches and display
        matched_groups = {}
        for match_data in matches:
            i, j = match_data[0], match_data[1]
            if i not in matched_groups:
                matched_groups[i] = []
            matched_groups[i].append(match_data)
            
        # Display matches
        for card_id, pairs in matched_groups.items():
            if pairs:
                pos = self.cards[card_id]['position']
                log(f"Card at position {pos} (id={card_id}) matches with:")
                for match_data in pairs:
                    pair_id = match_data[1]
                    combined_sim = match_data[2]
                    hist_sim = match_data[3] if len(match_data) > 3 else 0
                    template_sim = match_data[4] if len(match_data) > 4 else 0
                    pair_pos = self.cards[pair_id]['position']
                    log(f"  - Card at position {pair_pos} (id={pair_id}) - Combined: {combined_sim:.3f} (Hist: {hist_sim:.3f}, Template: {template_sim:.3f})")
                    
        return matches
        
    def save_individual_cards(self, output_dir="extracted_cards"):
        """Save each extracted card as a separate image file."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            log(f"Created directory: {output_dir}")
            
        log(f"Saving individual cards to {output_dir}/")
        for card in self.cards:
            filename = f"{output_dir}/card_{card['id']:02d}_r{card['position'][0]}_c{card['position'][1]}.png"
            cv2.imwrite(filename, card['image'])
            
        log(f"Saved {len(self.cards)} card images")
        
    def create_game_visualization(self, output_path="game_board.png"):
        """Create a visualization showing all cards with numbers."""
        if not self.cards:
            log("No cards to visualize")
            return
            
        # Get card dimensions
        card_height, card_width = self.cards[0]['image'].shape[:2]
        
        # Create canvas
        canvas_height = self.rows * card_height + (self.rows + 1) * 10
        canvas_width = self.cols * card_width + (self.cols + 1) * 10
        canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255
        
        # Place cards on canvas
        for card in self.cards:
            row, col = card['position']
            x = col * card_width + (col + 1) * 10
            y = row * card_height + (row + 1) * 10
            
            # Place card image
            canvas[y:y+card_height, x:x+card_width] = card['image']
            
            # Add card number
            text = str(card['id'])
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(text, font, 0.5, 2)[0]
            text_x = x + (card_width - text_size[0]) // 2
            text_y = y + card_height + 8
            cv2.putText(canvas, text, (text_x, text_y), font, 0.5, (0, 0, 0), 2)
            
        cv2.imwrite(output_path, canvas)
        log(f"Game board visualization saved to {output_path}")
        
    def get_best_pairs(self, matches):
        """
        Extract the best unique pairs ensuring each card matches exactly one other card.
        
        Args:
            matches: List of all potential matches
            
        Returns:
            List of best unique pairs
        """
        # Sort matches by similarity (descending)
        sorted_matches = sorted(matches, key=lambda x: x[2], reverse=True)
        
        # Track which cards have been paired
        paired_cards = set()
        best_pairs = []
        
        for match_data in sorted_matches:
            i, j = match_data[0], match_data[1]
            
            # Only add this pair if neither card is already paired
            if i not in paired_cards and j not in paired_cards:
                best_pairs.append(match_data)
                paired_cards.add(i)
                paired_cards.add(j)
                
        # Find unpaired cards
        all_cards = set(range(len(self.cards)))
        unpaired_cards = all_cards - paired_cards
        
        if unpaired_cards:
            log(f"\nWarning: {len(unpaired_cards)} cards remain unpaired:")
            for card_id in sorted(unpaired_cards):
                pos = self.cards[card_id]['position']
                log(f"  - Card {card_id} at position {pos}")
                
        return best_pairs
    
    def display_match_summary(self, matches):
        """Display a summary of all matching pairs."""
        log("\n" + "="*60)
        log("MATCHING PAIRS SUMMARY")
        log("="*60)
        
        unique_pairs = {}
        for match_data in matches:
            i, j = match_data[0], match_data[1]
            pair = tuple(sorted([i, j]))
            if pair not in unique_pairs:
                unique_pairs[pair] = match_data
            
        log(f"Total unique pairs found: {len(unique_pairs)}")
        log("\nPair details:")
        
        for idx, (pair, match_data) in enumerate(sorted(unique_pairs.items()), 1):
            i, j = pair
            pos_i = self.cards[i]['position']
            pos_j = self.cards[j]['position']
            combined_sim = match_data[2]
            log(f"{idx}. Card {i} (row {pos_i[0]}, col {pos_i[1]}) <--> Card {j} (row {pos_j[0]}, col {pos_j[1]}) - Similarity: {combined_sim:.3f}")
            
        log("="*60 + "\n")


def main():
    """Main function to run the card matching analysis."""
    log("Starting Card Matching Game Analysis")
    log("="*60)
    
    # Initialize game
    game = CardMatchingGame("pics/img.png", rows=5, cols=6)
    
    # Extract cards from grid
    if not game.extract_cards():
        log("Failed to extract cards. Exiting.")
        return
        
    # Save individual cards
    game.save_individual_cards()
    
    # Create game board visualization
    game.create_game_visualization()
    
    # Find matching pairs (lower threshold to find more matches)
    matches = game.find_matching_pairs(similarity_threshold=0.55)
    
    # Get best unique pairs
    best_pairs = game.get_best_pairs(matches)
    
    # Display summary
    log(f"\nExtracted {len(best_pairs)} unique best-matching pairs:")
    game.display_match_summary(best_pairs)
    
    log("Analysis complete!")


if __name__ == "__main__":
    main()
