import cv2
import numpy as np
import pyautogui
import Quartz

def click_at(x, y):
    event_down = Quartz.CGEventCreateMouseEvent(
        None, Quartz.kCGEventLeftMouseDown, (x, y), Quartz.kCGMouseButtonLeft
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)

    event_up = Quartz.CGEventCreateMouseEvent(
        None, Quartz.kCGEventLeftMouseUp, (x, y), Quartz.kCGMouseButtonLeft
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)

def map_coordinates(detected_x, detected_y, scaling_factor):
    adjusted_x = int(detected_x / scaling_factor)
    adjusted_y = int(detected_y / scaling_factor)
    return adjusted_x, adjusted_y

# Load the button template
template = cv2.imread('pics/throwbutton.png', 0)
if template is None:
    print("Error: Unable to load 'button_template.png'. Ensure the file exists.")
    exit()

w, h = template.shape[::-1]

# Take a screenshot
screenshot = pyautogui.screenshot()
screen = np.array(screenshot)
gray_screen = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

# Perform template matching
result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
threshold = 0.8
loc = np.where(result >= threshold)

if len(loc[0]) > 0:
    detected_x, detected_y = next(zip(*loc[::-1]))
    center_x = detected_x + w // 2
    center_y = detected_y + h // 2
    print(f"Detected at: ({center_x}, {center_y})")

    # Calculate scaling factor
    actual_width, actual_height = 2560, 1600  # Replace with your screen resolution
    logical_width, logical_height = pyautogui.size()
    scaling_factor = actual_width / logical_width
    print(f"Scaling factor: {scaling_factor}")

    # Map to logical coordinates
    adjusted_x, adjusted_y = map_coordinates(center_x, center_y, scaling_factor)
    print(f"Mapped coordinates: ({adjusted_x}, {adjusted_y})")

    # Click at the adjusted coordinates
    click_at(adjusted_x, adjusted_y)
else:
    print("Button not found.")
