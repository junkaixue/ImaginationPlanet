import cv2
import numpy as np
import pyautogui

offset_x = 181
offset_y = 125


def map_coordinates(detected_x, detected_y, scaling_factor):
    adjusted_x = int(detected_x / scaling_factor)
    adjusted_y = int(detected_y / scaling_factor)
    return adjusted_x, adjusted_y


# Load the button templates (for multiple buttons)
templates = [
    ("pics/throwbutton.png", "Button 1"),
]

# Take a screenshot
screenshot = pyautogui.screenshot()
screen = np.array(screenshot)
gray_screen = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

# Calculate scaling factor
actual_width, actual_height = 2560, 1664  # Replace with your screen resolution
logical_width, logical_height = 1470, 956
scaling_factor = actual_width / logical_width
print(f"Scaling factor: {scaling_factor}")

# Process each button template
for template_path, button_name in templates:
    template = cv2.imread(template_path, 0)
    if template is None:
        print(f"Error: Unable to load '{template_path}'.")
        continue

    w, h = template.shape[::-1]

    # Perform template matching
    result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8
    loc = np.where(result >= threshold)

    # Click each match
    for detected_x, detected_y in zip(*loc[::-1]):
        center_x = detected_x + w // 2
        center_y = detected_y + h // 2
        # print(f"{button_name} detected at: ({center_x}, {center_y})")

        # Map to logical coordinates
        final_x, final_y = map_coordinates(center_x, center_y, scaling_factor)
        print(f"{button_name} mapped coordinates: ({final_x - offset_x}, {final_y - offset_y})")

        # Click at the mapped coordinates
        # print (final_x - offset_x, final_y - offset_y)
