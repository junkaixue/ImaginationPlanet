import pyautogui
import time

print("=== Mouse Control Test ===\n")

# Get current position
current = pyautogui.position()
print(f"Current mouse position: {current}")

print("\nIn 3 seconds, will try to move mouse to center of screen...")
time.sleep(3)

# Test moving to a position
screen_width, screen_height = pyautogui.size()
center_x = screen_width // 2
center_y = screen_height // 2

print(f"Moving to center: ({center_x}, {center_y})")

try:
    pyautogui.moveTo(center_x, center_y)
    time.sleep(1)
    
    new_pos = pyautogui.position()
    print(f"New position: {new_pos}")
    
    if new_pos.x == center_x and new_pos.y == center_y:
        print("✅ Mouse moved successfully!")
    else:
        print("❌ Mouse did NOT move to the target position")
        print("   This means pyautogui doesn't have accessibility permissions")
        print("\n🔧 Fix:")
        print("   Go to: System Settings → Privacy & Security → Accessibility")
        print("   Add and enable: Terminal (or PyCharm if using IDE)")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n🔧 Fix:")
    print("   Go to: System Settings → Privacy & Security → Accessibility")
    print("   Add and enable: Terminal (or PyCharm if using IDE)")

print("\nTest complete!")
