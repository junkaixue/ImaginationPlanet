"""
Debug Template Matching

Shows template matching confidence scores to help debug why matching fails.
"""

import cv2
import numpy as np
import os
from platform_config import get_image_path


def debug_single_template(img_path, template_path, template_name):
    """Test a single template match and show results."""
    img = cv2.imread(img_path)
    template = cv2.imread(template_path)
    
    if img is None:
        print(f"ERROR: Could not load image: {img_path}")
        return
    
    if template is None:
        print(f"ERROR: Could not load template: {template_path}")
        return
    
    print(f"\nTesting template: {template_name}")
    print(f"  Image size: {img.shape[1]}x{img.shape[0]}")
    print(f"  Template size: {template.shape[1]}x{template.shape[0]}")
    
    # Convert to grayscale (same as template_card_matcher.py)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # Try template matching with grayscale
    result = cv2.matchTemplate(gray_img, gray_template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    print(f"  Best match confidence: {max_val:.4f}")
    print(f"  Best match location: {max_loc}")
    
    # Find all matches above different thresholds
    for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
        locations = np.where(result >= threshold)
        num_matches = len(locations[0])
        print(f"  Matches at {threshold:.1f}: {num_matches}")
    
    return max_val


def main():
    print("=" * 70)
    print("DEBUG TEMPLATE MATCHING")
    print("=" * 70)
    
    img_path = get_image_path("img.png")
    template_dir = "pics/match"
    
    print(f"\nImage path: {img_path}")
    print(f"  File exists: {os.path.exists(img_path)}")
    if os.path.exists(img_path):
        img_test = cv2.imread(img_path)
        if img_test is not None:
            print(f"  Can load: ✅ ({img_test.shape[1]}x{img_test.shape[0]})")
        else:
            print(f"  Can load: ❌ (imread returned None)")
    
    print(f"\nTemplate dir: {template_dir}")
    print(f"  Directory exists: {os.path.exists(template_dir)}")
    
    if not os.path.exists(img_path):
        print(f"\n❌ ERROR: Image not found at: {img_path}")
        print(f"\nExpected location on Mac: pics/mac/img.png")
        return
    
    if not os.path.exists(template_dir):
        print(f"\nERROR: Template directory not found: {template_dir}")
        return
    
    # Get all templates
    template_files = sorted([f for f in os.listdir(template_dir) 
                            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                            and f != 'flipback.png'])
    
    print(f"\nFound {len(template_files)} templates")
    print("\n" + "=" * 70)
    
    results = []
    
    for filename in template_files:
        template_path = os.path.join(template_dir, filename)
        max_conf = debug_single_template(img_path, template_path, filename)
        if max_conf is not None:
            results.append((filename, max_conf))
    
    print("\n" + "=" * 70)
    print("SUMMARY - Best confidence for each template:")
    print("=" * 70)
    
    results.sort(key=lambda x: x[1], reverse=True)
    
    for filename, conf in results:
        status = "✅" if conf >= 0.7 else "❌"
        print(f"{status} {filename:20s}: {conf:.4f}")
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS:")
    print("=" * 70)
    
    good_matches = [r for r in results if r[1] >= 0.7]
    
    if not good_matches:
        print("\n❌ No templates match (all < 0.7 confidence)")
        print("\n🔍 PROBLEM: Template sizes don't match Mac card sizes")
        print("\nThe templates in pics/match/ were created on Windows.")
        print("Mac displays cards at different pixel dimensions.")
        print("\n💡 SOLUTIONS:")
        print("\n  Option 1: Retake templates on Mac")
        print("    - Play the game on Mac")
        print("    - Screenshot individual cards")
        print("    - Save to pics/match/ (replace existing)")
        print("\n  Option 2: Use auto_card_matcher.py instead")
        print("    - Uses color-based matching (size-independent)")
        print("    - Already works on both Windows and Mac")
        print("    - Run: python play_matching_game.py")
    else:
        print(f"\n✅ {len(good_matches)} templates match well (>= 0.7)")
        
        bad_matches = [r for r in results if r[1] < 0.7]
        if bad_matches:
            print(f"\n⚠️  {len(bad_matches)} templates need adjustment:")
            for filename, conf in bad_matches[:5]:
                print(f"  - {filename}: {conf:.4f}")


if __name__ == "__main__":
    main()
