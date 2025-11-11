import pyautogui
import cv2
import time

print("=== Screen Capture Debug ===\n")

# 1. Check if image file exists and can be loaded
print("1. Checking throwbutton.png...")
try:
    img = cv2.imread("pics/mac/throwbutton.png")
    if img is not None:
        h, w = img.shape[:2]
        print(f"   ✅ Image loaded: {w}x{h} pixels")
    else:
        print("   ❌ Image file cannot be read!")
except Exception as e:
    print(f"   ❌ Error loading image: {e}")

# 2. Get screen size
print("\n2. Screen info:")
screen_width, screen_height = pyautogui.size()
print(f"   Screen size: {screen_width}x{screen_height}")

# 3. Take a screenshot of current screen
print("\n3. Taking screenshot in 3 seconds...")
print("   Make sure the game window with run button is visible!")
time.sleep(3)

screenshot = pyautogui.screenshot()
screenshot.save("debug_screenshot.png")
print("   ✅ Screenshot saved to: debug_screenshot.png")
print("   Please check this file to see what's on your screen")

# 4. Try to find with grayscale matching
print("\n4. Trying grayscale matching...")
try:
    loc = pyautogui.locateOnScreen("pics/mac/throwbutton.png", confidence=0.5, grayscale=True)
    if loc:
        print(f"   ✅ FOUND with grayscale: {loc}")
    else:
        print("   ❌ Not found with grayscale")
except Exception as e:
    print(f"   ❌ Grayscale matching failed: {e}")

print("\n=== Debug Complete ===")
print("\nNext steps:")
print("1. Open debug_screenshot.png to see what was captured")
print("2. Open pics/mac/throwbutton.png to compare")
print("3. Make sure they look similar and the button is visible")
