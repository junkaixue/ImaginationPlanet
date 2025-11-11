#!/usr/bin/env python3
"""
Quick test script to verify platform detection and image path resolution.
Run this to confirm the refactoring works correctly.
"""

import os
from platform_config import CURRENT_PLATFORM, IS_MAC, IS_WINDOWS, IMAGE_DIR, get_image_path

def test_platform_detection():
    """Test that platform is correctly detected."""
    print("=" * 60)
    print("PLATFORM DETECTION TEST")
    print("=" * 60)
    print(f"✓ Detected Platform: {CURRENT_PLATFORM}")
    print(f"✓ Is macOS: {IS_MAC}")
    print(f"✓ Is Windows: {IS_WINDOWS}")
    print(f"✓ Image Directory: {IMAGE_DIR}")
    print()

def test_image_paths():
    """Test that image paths are correctly generated."""
    print("=" * 60)
    print("IMAGE PATH RESOLUTION TEST")
    print("=" * 60)
    
    test_images = [
        "throwbutton.png",
        "fight_button.png",
        "cat_house.png",
        "visiting_main.png"
    ]
    
    for img in test_images:
        path = get_image_path(img)
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"{status} {path:<40} {'EXISTS' if exists else 'MISSING'}")
    print()

def test_imports():
    """Test that refactored modules can be imported."""
    print("=" * 60)
    print("MODULE IMPORT TEST")
    print("=" * 60)
    
    try:
        import common
        print("✓ common.py imported successfully")
        print(f"  - Found {len(common.resource_map)} resource maps")
        print(f"  - Main map has {len(common.main_map)} buttons")
        print(f"  - Single find map has {len(common.single_find_map)} buttons")
    except Exception as e:
        print(f"✗ Failed to import common.py: {e}")
    
    try:
        import click
        print("✓ click.py imported successfully")
        print(f"  - click_at function: {hasattr(click, 'click_at')}")
        print(f"  - move_to function: {hasattr(click, 'move_to')}")
    except Exception as e:
        print(f"✗ Failed to import click.py: {e}")
    
    print()

def test_image_directory_structure():
    """Check that image directories are properly set up."""
    print("=" * 60)
    print("DIRECTORY STRUCTURE TEST")
    print("=" * 60)
    
    pics_dir = "pics"
    mac_dir = "pics/mac"
    
    pics_exists = os.path.isdir(pics_dir)
    mac_exists = os.path.isdir(mac_dir)
    
    print(f"{'✓' if pics_exists else '✗'} {pics_dir}/ {'EXISTS' if pics_exists else 'MISSING'}")
    if pics_exists:
        pics_count = len([f for f in os.listdir(pics_dir) if f.endswith('.png')])
        print(f"  └─ Contains {pics_count} PNG files")
    
    print(f"{'✓' if mac_exists else '✗'} {mac_dir}/ {'EXISTS' if mac_exists else 'MISSING'}")
    if mac_exists:
        mac_count = len([f for f in os.listdir(mac_dir) if f.endswith('.png')])
        print(f"  └─ Contains {mac_count} PNG files")
    
    print()

if __name__ == "__main__":
    print("\n🚀 Starting Platform Refactoring Verification Tests\n")
    
    test_platform_detection()
    test_image_directory_structure()
    test_image_paths()
    test_imports()
    
    print("=" * 60)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    if IS_MAC:
        print("1. Ensure all required images are in pics/mac/")
        print("2. Test running: python imaginationplanet.py -r=True")
    else:
        print("1. Ensure all required images are in pics/")
        print("2. Test running: python imaginationplanet.py -r=True")
    print("3. Delete obsolete files: common_mac.py, click_mac.py")
    print()
