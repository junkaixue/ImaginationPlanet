"""
Debug Mac Card Matcher

Tests template matching with the snapshot to find optimal threshold.
Shows confidence scores for each template.
"""

import cv2
import os
from platform_config import get_image_path


def template_matching():
    """Test all templates against the snapshot and show confidence scores."""
    
    # Load snapshot
    img_path = get_image_path("img.png")
    print(f"Loading snapshot: {img_path}")
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"ERROR: Could not load {img_path}")
        return
    
    print(f"Snapshot size: {img.shape[1]}x{img.shape[0]}")
    
    # Convert to grayscale
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Load templates - use platform-specific directory
    import platform
    template_dir = "pics/mac/match"
    
    print(f"Template directory: {template_dir}")
    skip_files = {'flipback.png'}
    
    template_files = sorted([f for f in os.listdir(template_dir)
                            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                            and f not in skip_files])
    
    print(f"\nTesting {len(template_files)} templates...\n")
    print("=" * 80)
    
    results = []
    
    for filename in template_files:
        filepath = os.path.join(template_dir, filename)
        template = cv2.imread(filepath, 0)  # Load as grayscale
        
        if template is None:
            print(f"ERROR: Could not load {filename}")
            continue
        
        # Perform template matching
        result = cv2.matchTemplate(gray_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # Count matches at different thresholds
        matches_05 = len(result[result >= 0.5])
        matches_06 = len(result[result >= 0.6])
        matches_07 = len(result[result >= 0.7])
        matches_08 = len(result[result >= 0.8])
        
        results.append({
            'name': filename,
            'max_conf': max_val,
            'template_size': f"{template.shape[1]}x{template.shape[0]}",
            'matches': {0.5: matches_05, 0.6: matches_06, 0.7: matches_07, 0.8: matches_08}
        })
        
        status = "✅" if max_val >= 0.7 else "⚠️" if max_val >= 0.5 else "❌"
        print(f"{status} {filename:20s} | Max: {max_val:.4f} | Size: {template.shape[1]:3d}x{template.shape[0]:3d} | " +
              f"Matches: 0.5={matches_05:2d} 0.6={matches_06:2d} 0.7={matches_07:2d} 0.8={matches_08:2d}")
    
    print("=" * 80)
    print("\nSUMMARY:")
    print("-" * 80)
    
    # Sort by confidence
    results.sort(key=lambda x: x['max_conf'], reverse=True)
    
    good_07 = [r for r in results if r['max_conf'] >= 0.7]
    okay_05 = [r for r in results if 0.5 <= r['max_conf'] < 0.7]
    poor = [r for r in results if r['max_conf'] < 0.5]
    
    print(f"\n✅ Good matches (>= 0.7): {len(good_07)}")
    for r in good_07[:5]:
        print(f"   {r['name']:20s} {r['max_conf']:.4f}")
    
    print(f"\n⚠️  Moderate matches (0.5-0.7): {len(okay_05)}")
    for r in okay_05[:5]:
        print(f"   {r['name']:20s} {r['max_conf']:.4f}")
    
    print(f"\n❌ Poor matches (< 0.5): {len(poor)}")
    for r in poor[:5]:
        print(f"   {r['name']:20s} {r['max_conf']:.4f}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    
    if len(good_07) >= 10:
        print("\n✅ Great! Most templates match well at threshold 0.7")
        print("   Use: threshold=0.7")
    elif len(good_07) + len(okay_05) >= 10:
        print("\n⚠️  Some templates need lower threshold")
        print("   Recommended: threshold=0.6 or 0.65")
        print("   Or retake templates that score < 0.7 on Mac")
    else:
        print("\n❌ Most templates don't match well")
        print("   Problem: Templates from Windows don't match Mac display")
        print("   Solution: Retake all template screenshots on Mac")
        print("\nHow to retake templates:")
        print("   1. Play the game on Mac")
        print("   2. Screenshot each unique card (crop to just the card)")
        print("   3. Save to pics/match/ with same filenames")
        print("   4. Make sure card size matches what's in img.png")
    
    # Suggest optimal threshold
    if results:
        median_conf = sorted([r['max_conf'] for r in results])[len(results)//2]
        print(f"\nMedian confidence: {median_conf:.4f}")
        
        if median_conf >= 0.7:
            suggested = 0.7
        elif median_conf >= 0.6:
            suggested = 0.6
        elif median_conf >= 0.5:
            suggested = 0.5
        else:
            suggested = 0.4
        
        print(f"Suggested threshold: {suggested}")


if __name__ == "__main__":
    print("=" * 80)
    print("MAC CARD MATCHER - DEBUG TEMPLATE MATCHING")
    print("=" * 80)
    print()
    template_matching()
