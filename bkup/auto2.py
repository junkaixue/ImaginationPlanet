import cv2
import numpy as np
import pyautogui

# Load the button template
template = cv2.imread('pics/throwbutton.png', 0)  # Grayscale image of the button
if template is None:
    print("Error: Unable to load 'button_template.png'. Ensure the file exists.")
    exit()

# Get the template dimensions
w, h = template.shape[::-1]

# Take a screenshot of the entire screen
screenshot = pyautogui.screenshot()

# Convert the screenshot to a NumPy array
screen = np.array(screenshot)

# Convert the screenshot to grayscale
gray_screen = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

# Perform template matching
result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)

# Set a threshold for matching
threshold = 0.8
loc = np.where(result >= threshold)

# If a match is found, simulate a click
if len(loc[0]) > 0:
    # Get the first match's coordinates
    pt = next(zip(*loc[::-1]))  # loc[::-1] gives (x, y)

    # Calculate the center of the detected button
    center_x = pt[0] + w // 2
    center_y = pt[1] + h // 2

    print(f"Button detected at ({center_x}, {center_y}). Clicking...")

    # Simulate the click using PyAutoGUI
    pyautogui.click(x=center_x, y=center_y)
else:
    print("Button not found.")
