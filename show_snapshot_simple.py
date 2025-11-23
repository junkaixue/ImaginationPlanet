"""
Show Mac Snapshot

Simple viewer to see what the snapshot looks like and measure card sizes.
"""

import cv2
import numpy as np
from platform_config import get_image_path


def main():
    img_path = get_image_path("img.png")
    
    print(f"Loading: {img_path}")
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"ERROR: Could not load {img_path}")
        return
    
    print(f"Snapshot size: {img.shape[1]}x{img.shape[0]}")
    
    # Save a copy with info overlay
    annotated = img.copy()
    
    # Add text showing dimensions
    cv2.putText(annotated, f"Snapshot: {img.shape[1]}x{img.shape[0]}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    output_path = get_image_path("snapshot_view.png")
    cv2.imwrite(output_path, annotated)
    
    print(f"\nSaved to: {output_path}")
    print("\nOpen this image and measure a card manually.")
    print("Then compare to template sizes in pics/match/")
    print("\nIf card sizes are different, you need to:")
    print("  1. Resize templates to match Mac card size, OR")
    print("  2. Retake template screenshots on Mac")


if __name__ == "__main__":
    main()
