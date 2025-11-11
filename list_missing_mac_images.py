#!/usr/bin/env python3
"""
List missing images in pics/mac/ compared to pics/.
Note: Missing images are INTENTIONAL if those features are not enabled.
Only add Mac-specific screenshots for features you actually use.
"""

import os

def find_missing_images():
    """Find images in pics/ that don't exist in pics/mac/"""
    pics_dir = "pics"
    mac_dir = "pics/mac"
    
    # Get all PNG files from both directories
    pics_files = {f for f in os.listdir(pics_dir) if f.endswith('.png')}
    mac_files = {f for f in os.listdir(mac_dir) if f.endswith('.png')}
    
    # Find missing files
    missing = pics_files - mac_files
    
    return sorted(missing)

def list_missing_images():
    """List missing images for informational purposes only"""
    missing = find_missing_images()
    
    if not missing:
        print("✓ pics/mac/ has all images from pics/")
        return
    
    print(f"Found {len(missing)} images in pics/ not in pics/mac/:\n")
    
    for img in missing:
        print(f"  - {img}")
    
    print(f"\n📝 Note: Missing images are OK if those features aren't used.")
    print(f"Only add Mac screenshots for features you actually need.")

if __name__ == "__main__":
    print("=" * 60)
    print("Mac Image Directory Status")
    print("=" * 60)
    print()
    
    list_missing_images()
