"""
Test Flipback Detection

This script helps diagnose why flipback.png might not be detected on Mac.
Run this when the cards are flipped back (visible on screen).
"""

import cv2
import numpy as np
import pyautogui
import platform
from platform_config import get_image_path


def test_flipback_detection():
    print("=" * 70)
    print("FLIPBACK DETECTION TEST")
    print("=" * 70)
    print(f"\nPlatform: {platform.system()}")
    
    # Get the template path
    flipback_path = get_image_path("match/flipback.png")
    print(f"Template path: {flipback_path}")
    
    # Load template
    template = cv2.imread(flipback_path, 0)
    if template is None:
        print(f"\n❌ ERROR: Cannot load template from {flipback_path}")
        print("Make sure flipback.png exists in pics/mac/match/ (Mac) or pics/match/ (Windows)")
        return
    
    h, w = template.shape[:2]
    print(f"Template size: {w}x{h}")
    
    # Take screenshot
    print("\nTaking screenshot in 3 seconds...")
    print("Make sure the FLIPPED BACK cards are visible on screen!")
    import time
    time.sleep(3)
    
    screenshot = pyautogui.screenshot()
    screen = np.array(screenshot)
    gray_screen = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
    
    sh, sw = gray_screen.shape[:2]
    print(f"Screen size: {sw}x{sh}")
    
    # Try template matching
    print("\nPerforming template matching...")
    result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    print(f"\nMatch confidence: {max_val:.3f}")
    print(f"Match location: ({max_loc[0]}, {max_loc[1]})")
    
    # Test different thresholds
    print("\n" + "=" * 70)
    print("THRESHOLD TESTS")
    print("=" * 70)
    
    thresholds = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    for th in thresholds:
        if max_val >= th:
            print(f"✅ threshold={th:.1f}: PASS (match={max_val:.3f})")
        else:
            print(f"❌ threshold={th:.1f}: FAIL (match={max_val:.3f})")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    if max_val >= 0.7:
        print("✅ Detection should work fine with default settings!")
    elif max_val >= 0.5:
        print("⚠️  Detection marginal - Mac threshold of 0.5 should work")
        print(f"   Current match: {max_val:.3f}")
    elif max_val >= 0.3:
        print("⚠️  Detection weak - consider lowering threshold further")
        print(f"   Current match: {max_val:.3f}")
        print(f"   Suggested threshold: {max_val - 0.05:.2f}")
    else:
        print("❌ Template not detected!")
        print("\nPossible issues:")
        print("1. Template was captured on Windows, looks different on Mac Retina display")
        print("2. Wrong part of screen captured in template")
        print("3. Game graphics changed")
        print("\nSolution:")
        print("1. Take a new screenshot of flipped-back cards on Mac")
        print("2. Save as pics/mac/match/flipback.png")
        print("3. Make sure it captures a distinctive part that only appears when flipped back")
    
    # Save debug image
    debug_path = get_image_path("flipback_debug.png")
    # Draw rectangle where template was found
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    debug_img = cv2.cvtColor(gray_screen, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(debug_img, top_left, bottom_right, (0, 255, 0), 2)
    cv2.putText(debug_img, f"Match: {max_val:.3f}", (top_left[0], top_left[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imwrite(debug_path, debug_img)
    print(f"\n📸 Debug image saved to: {debug_path}")
    print("   (Green rectangle shows where template was found)")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_flipback_detection()
