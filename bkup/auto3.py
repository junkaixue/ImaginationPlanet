import cv2
import numpy as np
import pyautogui

# Load the button template
template = cv2.imread('pics/throwbutton.png', 0)
if template is None:
    print("Error: Unable to load 'button_template.png'. Ensure the file exists.")
    exit()

w, h = template.shape[::-1]

# Take a screenshot of the entire screen
screenshot = pyautogui.screenshot()
screen = np.array(screenshot)
gray_screen = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

# Perform template matching
result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
threshold = 0.8
loc = np.where(result >= threshold)

if len(loc[0]) > 0:
    for pt in zip(*loc[::-1]):
        # Calculate the center of the button
        center_x = pt[0] + w // 2
        center_y = pt[1] + h // 2
        print(f"Button detected at ({center_x}, {center_y})")

        # Adjust for Retina scaling
        scaling_factor = 2  # Adjust for Retina displays
        scaled_x = int(center_x * scaling_factor)
        scaled_y = int(center_y * scaling_factor)

        print(f"Scaled coordinates: ({scaled_x}, {scaled_y})")

        # Simulate the click
        pyautogui.click(x=scaled_x, y=scaled_y)
        break
else:
    print("Button not found.")
