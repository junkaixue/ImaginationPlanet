import pyautogui
import time

print("Make sure the game window with the run button is visible!")
print("Searching in 3 seconds...")
time.sleep(3)

# Test with different confidence levels
for confidence in [0.9, 0.8, 0.7, 0.6, 0.5]:
    try:
        print(f"\nTrying confidence={confidence}...")
        loc = pyautogui.locateOnScreen("pics/mac/throwbutton.png", confidence=confidence)
        if loc:
            print(f"✅ FOUND at confidence={confidence}!")
            print(f"   Location: {loc}")
            center = pyautogui.center(loc)
            print(f"   Center: {center}")
            break
    except Exception as e:
        print(f"❌ Not found at confidence={confidence}: {e}")

print("\nDone!")
