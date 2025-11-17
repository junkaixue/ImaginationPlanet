================================================================================
AUTOMATIC CARD MATCHER - README
================================================================================

OVERVIEW:
---------
Auto_card_matcher.py is an improved version that automatically solves and clicks
card matching pairs in the game. It reads the card area rectangle from the
config file and maps card positions to actual screen coordinates for clicking.

KEY IMPROVEMENTS:
-----------------
1. ✓ Works with any screenshot - no need to extract cards beforehand
2. ✓ Automatically clicks matching pairs in the game window
3. ✓ Uses config file coordinates (pair_top_left, pair_bottom_right)
4. ✓ Maps grid positions to screen coordinates
5. ✓ Handles all 30 cards from a single screenshot
6. ✓ Cross-platform compatible (Windows/macOS)

SETUP:
------
1. Configure the card area rectangle in your platform-specific config:
   
   Windows: configs/cood_win.cfg
   macOS:   configs/cood_mac.cfg
   
   Required entries:
   pair_top_left: -357, 829      # Top-left corner (relative to Run Button)
   pair_bottom_right: 363, 61    # Bottom-right corner (relative to Run Button)

2. These coordinates define the rectangle containing all 30 cards (5x6 grid)
   The coordinates are relative to the Run Button position

HOW TO USE:
-----------
Step 1: Take a screenshot of the card matching game
        - Make sure all cards are visible in the game
        - The cards should be in a 5x6 grid

Step 2: Save the screenshot as: pics/img.png
        - Replace any existing img.png file
        - The script expects the file at this exact location

Step 3: Make sure the game window is visible and in focus
        - The script will click on the actual game window
        - Do not cover the game window

Step 4: Run the script:
        python auto_card_matcher.py

Step 5: The script will:
        - Load the rectangle coordinates from config
        - Extract and analyze all 30 cards
        - Find all 15 matching pairs
        - Automatically click each pair in sequence
        - Wait between clicks to allow game animations

TESTING (DRY RUN):
------------------
To test without actually clicking:
  python auto_card_matcher.py --dry-run

This will:
- Show which coordinates would be clicked
- Not perform any actual mouse clicks
- Useful for verifying the card positions

TIMING CONFIGURATION:
---------------------
In auto_card_matcher.py, you can adjust timing in the main() function:

  click_delay_between=0.5   # Delay between two cards in a pair (seconds)
  click_delay_after=2.0     # Delay after completing a pair (seconds)

Increase these if the game needs more time to process clicks.

COORDINATE SYSTEM:
-----------------
The script uses a coordinate mapping system:

1. Grid Position: (row, col) in the 5x6 card grid
   - Rows: 0-4 (top to bottom)
   - Cols: 0-5 (left to right)

2. Rectangle Position: Coordinates within the card area rectangle
   - Calculated from grid position
   - Relative to rectangle corners

3. Screen Position: Absolute screen coordinates for clicking
   - Calculated from: Run Button + rectangle offset + card position
   - These are the actual click coordinates

CONFIGURATION FILE FORMAT:
--------------------------
configs/cood_win.cfg (Windows) or configs/cood_mac.cfg (macOS):

  pair_top_left: -357, 829       # X and Y offset from Run Button
  pair_bottom_right: 363, 61     # X and Y offset from Run Button

How to find these coordinates:
1. Use the existing config_coords.py to find the Run Button
2. Note the top-left corner of the card area (relative to Run Button)
3. Note the bottom-right corner of the card area (relative to Run Button)
4. Update the config file with these values

EXAMPLE WORKFLOW:
-----------------
# 1. Take screenshot and save as pics/img.png

# 2. Test without clicking (dry run)
python auto_card_matcher.py --dry-run

# 3. If coordinates look correct, run for real
python auto_card_matcher.py

# Output example:
[2025-11-16 12:30:00] Automatic Card Matcher
[2025-11-16 12:30:00] Loading rectangle coordinates from config...
[2025-11-16 12:30:00] Rectangle area loaded:
[2025-11-16 12:30:00]   Top-left: (-357.0, 829.0)
[2025-11-16 12:30:00]   Bottom-right: (363.0, 61.0)
[2025-11-16 12:30:00]   Size: 720.0 x -768.0
[2025-11-16 12:30:01] Successfully extracted 30 cards
[2025-11-16 12:30:01] Found 15 matching pairs
[2025-11-16 12:30:01] 
[2025-11-16 12:30:01] Pair 1/15 - Similarity: 0.955
[2025-11-16 12:30:01] Clicking pair: Card 10 (grid 1,4) <-> Card 16 (grid 2,4)
[2025-11-16 12:30:01]   Click 1: (180.5, 650.2)
[2025-11-16 12:30:02]   Click 2: (180.5, 522.4)
...

TROUBLESHOOTING:
---------------
Problem: "Unable to load image from pics/img.png"
Solution: Make sure you saved the screenshot with the exact filename

Problem: "Rectangle coordinates not found in config file"
Solution: Add pair_top_left and pair_bottom_right to your config file

Problem: Clicks are in wrong positions
Solution: 
  1. Verify Run Button is correctly detected
  2. Check pair_top_left and pair_bottom_right values
  3. Use --dry-run to test coordinate mapping

Problem: Cards not matching correctly
Solution: 
  1. Ensure screenshot quality is good
  2. Cards should be clearly visible (not partially covered)
  3. Try adjusting similarity_threshold in find_matching_pairs()

Problem: Game doesn't respond to clicks
Solution:
  1. Make sure game window is in focus
  2. Check if click coordinates are correct (use --dry-run)
  3. Increase click_delay_after to give game more time

FILES:
------
auto_card_matcher.py          # Main script (NEW - use this one!)
card_matching_game.py         # Original analysis script (reference)
play_matching_game.py         # Original interactive game (reference)
configs/cood_win.cfg          # Windows coordinates
configs/cood_mac.cfg          # macOS coordinates
AUTO_MATCHER_README.txt       # This file
MATCHING_GAME_INSTRUCTIONS.txt # Original instructions

TECHNICAL DETAILS:
-----------------
- Uses cv2 (OpenCV) for image analysis
- Uses log_helper.py for timestamped logging
- Uses config_coords.py for coordinate system
- Uses click.py for cross-platform clicking
- Histogram + template matching for card comparison
- Greedy algorithm for optimal pair selection

CARD GRID LAYOUT:
----------------
   Col 0   Col 1   Col 2   Col 3   Col 4   Col 5
Row 0:  0      1      2      3      4      5
Row 1:  6      7      8      9     10     11
Row 2: 12     13     14     15     16     17
Row 3: 18     19     20     21     22     23
Row 4: 24     25     26     27     28     29

Each card is assigned an ID (0-29) based on its position in the grid.

NOTES:
------
- The script will click pairs automatically, so watch it work!
- All clicks use the existing click.py infrastructure
- Coordinates are platform-aware (uses correct config file)
- The script handles display scaling automatically
- Logging uses log_helper.py for consistency

================================================================================
For questions or issues, check the log output for detailed information.
================================================================================
