"""
Test script for config_coords module

Demonstrates how to use ConfigCoords to click positions from config files.
"""

from config_coords import ConfigCoords
import time


def test_config_coords(use_mock=False):
    """Test the config coordinate system.
    
    Args:
        use_mock: If True, use mock Run Button position for testing without game window
    """
    
    # Initialize with optional mock for testing
    if use_mock:
        # Mock Run Button position (2667, 1164) for testing
        config = ConfigCoords(mock_rb=(2667, 1164))
    else:
        # Automatically loads platform-specific config and finds Run Button
        config = ConfigCoords()
    
    # List all available coordinates
    print("\n" + "=" * 70)
    config.list_coords()
    print("=" * 70)
    
    # Example: Click at a specific named position
    print("\nExample clicks:")
    print("-" * 70)
    if use_mock:
        print("⚠️  WARNING: Mouse will ACTUALLY MOVE and CLICK at calculated positions!")
        print("   Using mock Run Button at (2667, 1164) to calculate targets")
        import time
        time.sleep(2)  # Give user time to see warning
    
    # Click at cat_house position with 1 second delay
    if config.click_coord("cat_house", delay=1):
        print("✅ Successfully clicked cat_house")
    
    # Click at visit positions
    for i in range(1, 5):
        coord_name = f"visit_last_c{i}"
        if config.click_coord(coord_name, delay=0.5):
            print(f"✅ Successfully clicked {coord_name}")
    
    # Get coordinate without clicking
    coords = config.get_coord("cat_house")
    if coords:
        x, y = coords
        print(f"\ncat_house absolute position: ({x:.1f}, {y:.1f})")


if __name__ == "__main__":
    # Use mock mode by default to test without game window open
    # Set use_mock=False to use actual Run Button detection
    test_config_coords(use_mock=True)
