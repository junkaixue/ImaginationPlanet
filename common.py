import cv2
import numpy as np
import pyautogui
import Quartz
import cmath
from datetime import datetime

# Preserve the original print function
original_print = print

coor_dict = {}

# Load the button templates (for multiple buttons)
resource_map = {
    # Main Run
    "RunButton": "pics/throwbutton.png",
    "Replace": "pics/replace.png",
    "NoMore": "pics/no_more.png",
    # Visit
    "VisitMain": "pics/visiting_main.png",
    "VisitFriend": "pics/friend_list.png",
    "VisitComplete": "pics/visiting_complete.png",
    "VisitButton": "pics/visiting_button.png",
    "VisitBack": "pics/visit_back.png",
    "CardButton": "pics/card_button.png",
    "Roll": "pics/rolling.png",
    "CatHouse": "pics/cat_house.png",
    # Guess
    "Guess": "pics/guess.png",
    "GuessL": "pics/guess_left.png",
    "GuessR": "pics/guess_right.png",
    # Fight
    "TaskMain": "pics/task_main.png",
    "FightMain": "pics/fight_main.png",
    "FightEntry": "pics/fight_entry.png",
    "FightButton": "pics/fight_button.png",
    "FightSkip": "pics/fight_skip.png",
}

but_list = {}


# Define a new print function with a timestamp
def print(*args, **kwargs):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    original_print(f'[{timestamp}]', *args, **kwargs)


def get_center(but):
    if but == "VisitButton" or but not in coor_dict:  # sometime scroll can change the pos
        location = pyautogui.locateOnScreen(resource_map[but], confidence=0.8)
        coor_dict[but] = pyautogui.center(location)
    return coor_dict[but]

def get_all(but, sft):
    if but not in but_list:
        matches = list(pyautogui.locateAllOnScreen(resource_map[but], confidence=0.8))
        coors = []
        prev = None
        for match in matches:
            if prev is None or abs(prev.top - match.top) > 20:
                prev = match
                coors.append(pyautogui.center(match))
        but_list[but] = coors
    return but_list[but]


def get_scaling_factor():
    # Get the main display ID
    main_display_id = Quartz.CGMainDisplayID()

    # Get the display mode
    display_mode = Quartz.CGDisplayCopyDisplayMode(main_display_id)

    # Retrieve the pixel dimensions
    pixel_width = Quartz.CGDisplayModeGetPixelWidth(display_mode)
    pixel_height = Quartz.CGDisplayModeGetPixelHeight(display_mode)

    # Retrieve the point dimensions
    point_width = Quartz.CGDisplayModeGetWidth(display_mode)
    point_height = Quartz.CGDisplayModeGetHeight(display_mode)

    # Calculate the scaling factor
    scaling_factor = pixel_width / point_width

    return scaling_factor


def find_button():
    # Take a screenshot
    screenshot = pyautogui.screenshot()
    screen = np.array(screenshot)
    gray_screen = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

    bts = []

    for button_name, template_path in resource_map.items():
        template = cv2.imread(template_path, 0)
        if template is None:
            print(f"Error: Unable to load '{template_path}'.")
            continue
        # Perform template matching
        result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            # print ("Found " + button_name)
            bts.append(button_name)
    return bts
