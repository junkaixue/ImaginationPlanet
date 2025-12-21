"""
Extract Mac Card Templates

Helps you manually extract card images from Mac snapshot to create templates.
Shows the snapshot with grid overlay so you can identify which cards to extract.
"""

import cv2
import numpy as np
import os
from platform_config import get_image_path


def draw_grid_on_image(img_path, output_path="pics/mac/snapshot_with_grid.png"):
    """Draw a grid on the snapshot to help identify card positions."""
    img = cv2.imread(img_path)
    
    if img is None:
        print(f"ERROR: Could not load image: {img_path}")
        return False
    
    print(f"Image size: {img.shape[1]}x{img.shape[0]}")
    
    # Make a copy for drawing
    annotated = img.copy()
    
    # Approximate card dimensions (you may need to adjust)
    card_width = 80
    card_height = 110
    
    # Grid starts at approximate position
    # You'll need to adjust these based on your actual card positions
    start_x = 40  # Left margin
    start_y = 60  # Top margin
    
    cols = 5  # 5 columns
    rows = 6  # 6 rows
    
    spacing_x = 95  # Horizontal spacing between card centers
    spacing_y = 92  # Vertical spacing between card centers
    
    # Draw grid
    for row in range(rows):
        for col in range(cols):
            # Calculate center position
            cx = start_x + col * spacing_x
            cy = start_y + row * spacing_y
            
            # Draw rectangle around card
            tl_x = cx - card_width // 2
            tl_y = cy - card_height // 2
            br_x = cx + card_width // 2
            br_y = cy + card_height // 2
            
            # Draw rectangle
            cv2.rectangle(annotated, (tl_x, tl_y), (br_x, br_y), (0, 255, 0), 2)
            
            # Draw grid position label
            cv2.putText(annotated, f"({row},{col})", (cx - 20, cy + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            # Draw center point
            cv2.circle(annotated, (cx, cy), 3, (0, 0, 255), -1)
    
    # Save annotated image
    cv2.imwrite(output_path, annotated)
    print(f"\n✅ Grid overlay saved to: {output_path}")
    print(f"\nOpen this image to see where cards are located.")
    print(f"Use these coordinates to manually extract card templates.")
    
    return True


def extract_single_card(img_path, row, col, card_name, 
                        start_x=40, start_y=60, spacing_x=95, spacing_y=92,
                        card_width=80, card_height=110):
    """
    Extract a single card from the grid.
    
    Args:
        img_path: Path to snapshot image
        row, col: Grid position (0-indexed)
        card_name: Name for the template (e.g., "cat", "book")
        start_x, start_y: Grid starting position
        spacing_x, spacing_y: Grid spacing
        card_width, card_height: Card dimensions
    """
    img = cv2.imread(img_path)
    
    if img is None:
        print(f"ERROR: Could not load image: {img_path}")
        return False
    
    # Calculate card position
    cx = start_x + col * spacing_x
    cy = start_y + row * spacing_y
    
    tl_x = max(0, cx - card_width // 2)
    tl_y = max(0, cy - card_height // 2)
    br_x = min(img.shape[1], cx + card_width // 2)
    br_y = min(img.shape[0], cy + card_height // 2)
    
    # Extract card
    card = img[tl_y:br_y, tl_x:br_x]
    
    # Save to match directory
    output_dir = "pics/match_mac"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"{card_name}.png")
    cv2.imwrite(output_path, card)
    
    print(f"✅ Extracted {card_name} from ({row},{col}) -> {output_path}")
    print(f"   Size: {card.shape[1]}x{card.shape[0]}")
    
    return True


def main():
    print("=" * 70)
    print("EXTRACT MAC CARD TEMPLATES")
    print("=" * 70)
    
    img_path = get_image_path("img.png")
    
    print(f"\nSnapshot: {img_path}")
    
    if not os.path.exists(img_path):
        print(f"ERROR: Snapshot not found at {img_path}")
        return
    
    print("\nSTEP 1: Creating grid overlay...")
    if not draw_grid_on_image(img_path):
        return
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("\n1. Open pics/mac/snapshot_with_grid.png")
    print("2. Identify which cards are at which grid positions")
    print("3. Edit this script and uncomment the extraction lines below")
    print("4. Run again to extract templates")
    print("\nExample extractions (uncomment and adjust):")
    print("  extract_single_card(img_path, row=0, col=0, card_name='cat')")
    print("  extract_single_card(img_path, row=0, col=1, card_name='dog')")
    print("  # etc...")
    print("\n" + "=" * 70)
    
    # Uncomment and edit these lines to extract cards:
    # Example: if you see a cat at grid position (1, 2)
    # extract_single_card(img_path, row=1, col=2, card_name="cat")
    
    # Add more extraction lines here for each unique card


if __name__ == "__main__":
    main()
