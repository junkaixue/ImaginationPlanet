"""
Test script for Smart Card Grab

This demonstrates how to use the smart card grabbing function
that checks for faces in visit boxes and uses the again_card.
"""

from smart_card_grab import SmartCardGrab, check_and_use_again_card


def test_with_game():
    """Test with actual game window (auto-detects Run Button)."""
    print("=" * 70)
    print("TEST MODE: Using actual game window")
    print("=" * 70)
    print()
    
    grabber = SmartCardGrab()
    result = grabber.smart_grab_cat()
    
    if result:
        print("\n✅ SUCCESS: Face found and AgainCard used!")
    else:
        print("\n❌ No action taken (no face found or no card available)")


def test_with_mock():
    """Test with mock Run Button (for testing without game window)."""
    print("=" * 70)
    print("TEST MODE: Using mock Run Button at (2667, 1164)")
    print("=" * 70)
    print()
    
    grabber = SmartCardGrab()
    result = grabber.smart_grab_cat(mock_rb=(2667, 1164))
    
    if result:
        print("\n✅ SUCCESS: Face found and AgainCard used!")
    else:
        print("\n❌ No action taken (no face found or no card available)")


def test_convenience_function():
    """Test using the convenience function."""
    print("=" * 70)
    print("TEST MODE: Using convenience function")
    print("=" * 70)
    print()
    
    # Quick one-liner to check and use again card
    result = check_and_use_again_card()
    
    if result:
        print("\n✅ SUCCESS!")
    else:
        print("\n❌ No action taken")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "mock":
        # Test with mock mode
        test_with_mock()
    elif len(sys.argv) > 1 and sys.argv[1] == "quick":
        # Test convenience function
        test_convenience_function()
    else:
        # Test with actual game
        print("Usage:")
        print("  python test_smart_grab.py        - Test with actual game window")
        print("  python test_smart_grab.py mock   - Test with mock Run Button")
        print("  python test_smart_grab.py quick  - Test convenience function")
        print()
        test_with_game()
