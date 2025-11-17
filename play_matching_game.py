"""
Interactive Card Matching Game
Play the card matching game with the extracted cards.
"""
import cv2
import numpy as np
import random
import os
from log_helper import log


class InteractiveMatchingGame:
    def __init__(self, card_dir="extracted_cards"):
        """
        Initialize the interactive matching game.
        
        Args:
            card_dir: Directory containing the extracted card images
        """
        self.card_dir = card_dir
        self.cards = []
        self.card_map = {}  # Maps grid position to card info
        self.revealed = []  # Track revealed cards
        self.matched_pairs = []  # Track matched pairs
        self.attempts = 0
        self.game_grid = None
        self.load_cards()
        
    def load_cards(self):
        """Load all card images from the directory."""
        log("Loading cards...")
        card_files = sorted([f for f in os.listdir(self.card_dir) if f.endswith('.png')])
        
        for idx, filename in enumerate(card_files):
            filepath = os.path.join(self.card_dir, filename)
            img = cv2.imread(filepath)
            if img is not None:
                # Parse position from filename (e.g., card_00_r0_c0.png)
                parts = filename.replace('.png', '').split('_')
                card_id = int(parts[1])
                row = int(parts[2][1:])
                col = int(parts[3][1:])
                
                self.cards.append({
                    'id': card_id,
                    'position': (row, col),
                    'image': img,
                    'filename': filename
                })
                self.card_map[(row, col)] = card_id
                
        log(f"Loaded {len(self.cards)} cards")
        
    def create_game_board(self, hide_all=True):
        """
        Create the game board display.
        
        Args:
            hide_all: If True, show card backs; if False, show all card faces
        """
        if not self.cards:
            log("No cards loaded")
            return None
            
        # Sort cards by position
        self.cards.sort(key=lambda x: (x['position'][0], x['position'][1]))
        
        # Get card dimensions
        card_height, card_width = self.cards[0]['image'].shape[:2]
        
        # Calculate rows and cols
        rows = max([c['position'][0] for c in self.cards]) + 1
        cols = max([c['position'][1] for c in self.cards]) + 1
        
        # Create canvas with margins
        margin = 10
        canvas_height = rows * card_height + (rows + 1) * margin
        canvas_width = cols * card_width + (cols + 1) * margin
        canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 240
        
        # Place cards on canvas
        for card in self.cards:
            row, col = card['position']
            x = col * card_width + (col + 1) * margin
            y = row * card_height + (row + 1) * margin
            
            # Check if card should be revealed or matched
            is_revealed = (row, col) in self.revealed
            is_matched = any((row, col) in pair for pair in self.matched_pairs)
            
            if hide_all and not is_revealed and not is_matched:
                # Draw card back
                card_back = np.ones((card_height, card_width, 3), dtype=np.uint8)
                card_back[:, :] = [200, 150, 100]  # Blue-brown color
                cv2.rectangle(card_back, (5, 5), (card_width-5, card_height-5), (150, 100, 50), 3)
                canvas[y:y+card_height, x:x+card_width] = card_back
                
                # Add card number
                text = str(card['id'])
                font = cv2.FONT_HERSHEY_SIMPLEX
                text_size = cv2.getTextSize(text, font, 1.0, 2)[0]
                text_x = x + (card_width - text_size[0]) // 2
                text_y = y + (card_height + text_size[1]) // 2
                cv2.putText(canvas, text, (text_x, text_y), font, 1.0, (255, 255, 255), 3)
            else:
                # Show card face
                canvas[y:y+card_height, x:x+card_width] = card['image']
                
                # Add green border for matched cards
                if is_matched:
                    cv2.rectangle(canvas, (x, y), (x+card_width, y+card_height), (0, 255, 0), 5)
                    
        # Add game info
        info_text = f"Attempts: {self.attempts} | Matched: {len(self.matched_pairs)}/15"
        cv2.putText(canvas, info_text, (10, canvas_height - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        return canvas
        
    def get_card_by_position(self, row, col):
        """Get card by its grid position."""
        for card in self.cards:
            if card['position'] == (row, col):
                return card
        return None
        
    def check_match(self, card1_pos, card2_pos):
        """
        Check if two cards match using image comparison.
        
        Args:
            card1_pos: (row, col) of first card
            card2_pos: (row, col) of second card
            
        Returns:
            True if cards match, False otherwise
        """
        card1 = self.get_card_by_position(*card1_pos)
        card2 = self.get_card_by_position(*card2_pos)
        
        if not card1 or not card2:
            return False
            
        # Compare using histogram similarity
        hist1 = cv2.calcHist([card1['image']], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([card2['image']], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        # Use lower threshold to account for slight variations
        return similarity > 0.90
        
    def play_turn(self, card1_id, card2_id):
        """
        Play a turn by selecting two cards.
        
        Args:
            card1_id: ID of first card
            card2_id: ID of second card
            
        Returns:
            String message about the result
        """
        # Find cards by ID
        card1 = next((c for c in self.cards if c['id'] == card1_id), None)
        card2 = next((c for c in self.cards if c['id'] == card2_id), None)
        
        if not card1 or not card2:
            return "Invalid card IDs"
            
        if card1['id'] == card2['id']:
            return "Cannot select the same card twice"
            
        # Check if already matched
        if any(card1['position'] in pair for pair in self.matched_pairs):
            return f"Card {card1_id} is already matched"
        if any(card2['position'] in pair for pair in self.matched_pairs):
            return f"Card {card2_id} is already matched"
            
        # Reveal cards
        self.revealed = [card1['position'], card2['position']]
        self.attempts += 1
        
        # Check for match
        if self.check_match(card1['position'], card2['position']):
            self.matched_pairs.append((card1['position'], card2['position']))
            result = f"Match found! Cards {card1_id} and {card2_id} match!"
            
            if len(self.matched_pairs) == 15:
                result += f"\n\nCongratulations! You won in {self.attempts} attempts!"
        else:
            result = f"No match. Cards {card1_id} and {card2_id} are different."
            
        return result
        
    def save_game_state(self, filename="game_state.png"):
        """Save current game state to an image."""
        board = self.create_game_board(hide_all=True)
        if board is not None:
            cv2.imwrite(filename, board)
            log(f"Game state saved to {filename}")
            
    def show_solution(self, filename="solution.png"):
        """Show all cards (solution)."""
        board = self.create_game_board(hide_all=False)
        if board is not None:
            cv2.imwrite(filename, board)
            log(f"Solution saved to {filename}")


def demo_game():
    """Run a demo game with automated moves."""
    log("Starting Card Matching Game Demo")
    log("="*60)
    
    # Initialize game
    game = InteractiveMatchingGame()
    
    # Save initial state
    game.save_game_state("game_initial.png")
    log("Initial game board saved to game_initial.png")
    
    # Known matching pairs from our analysis
    known_pairs = [
        (0, 18), (1, 13), (2, 17), (3, 28), (4, 7),
        (5, 6), (8, 29), (9, 23), (10, 16), (11, 27),
        (12, 19), (14, 21), (15, 26), (20, 24), (22, 25)
    ]
    
    log("\nPlaying through known pairs...")
    for card1, card2 in known_pairs[:5]:  # Play first 5 pairs as demo
        result = game.play_turn(card1, card2)
        log(f"Turn {game.attempts}: {result}")
        game.save_game_state(f"game_turn_{game.attempts}.png")
        
    log(f"\nDemo complete! Matched {len(game.matched_pairs)} out of 15 pairs")
    log(f"Total attempts: {game.attempts}")
    
    # Show solution
    game.show_solution("solution.png")
    log("\nAll game states saved to PNG files")
    

def interactive_play():
    """Play the game interactively via console."""
    log("Starting Interactive Card Matching Game")
    log("="*60)
    
    game = InteractiveMatchingGame()
    game.save_game_state("current_game.png")
    log("Game board saved to current_game.png")
    log("Open current_game.png to see the game board")
    log("\nCard IDs are shown on each card back (0-29)")
    log("Type two card IDs separated by space (e.g., '0 18') to make a guess")
    log("Type 'solution' to see all cards")
    log("Type 'quit' to exit")
    
    while len(game.matched_pairs) < 15:
        print(f"\nMatched pairs: {len(game.matched_pairs)}/15, Attempts: {game.attempts}")
        user_input = input("Enter two card IDs (or 'solution'/'quit'): ").strip().lower()
        
        if user_input == 'quit':
            log("Game ended by user")
            break
        elif user_input == 'solution':
            game.show_solution("solution.png")
            log("Solution saved to solution.png")
            continue
            
        try:
            parts = user_input.split()
            if len(parts) != 2:
                log("Please enter exactly two card IDs")
                continue
                
            card1_id = int(parts[0])
            card2_id = int(parts[1])
            
            result = game.play_turn(card1_id, card2_id)
            log(result)
            
            game.save_game_state("current_game.png")
            log("Game board updated in current_game.png")
            
        except ValueError:
            log("Invalid input. Please enter two numbers")
        except Exception as e:
            log(f"Error: {e}")
            
    if len(game.matched_pairs) == 15:
        log(f"\n{'='*60}")
        log(f"CONGRATULATIONS! You won in {game.attempts} attempts!")
        log(f"{'='*60}")


if __name__ == "__main__":
    # Run demo mode
    demo_game()
    
    # Uncomment to play interactively instead:
    # interactive_play()
