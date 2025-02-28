from datetime import datetime

import Quartz
import cv2
import numpy as np
import pyautogui

# Preserve the original print function
original_print = print

coor_dict = {}

# Load the button templates (for multiple buttons)
main_map = {
    # Main Run
    "RunButton": "pics/throwbutton.png",
    "Replace": "pics/replace.png",
    "NoMore": "pics/no_more.png",
    "Gift": "pics/gift.png",

    # Guess
    "Guess": "pics/guess.png",
    # Temp hard code
    # "GuessL": "pics/guess_left.png",
    # "GuessR": "pics/guess_right.png",

    # Visit Main
    "VisitMain": "pics/visiting_main.png",
}

visit_map = {
    # Visit
    "VisitComplete": "pics/visiting_complete.png",
    "Roll": "pics/rolling.png",
    "Timeout": "pics/timeout.png",
    "VisitBusy": "pics/visit_busy.png",
    "AdsSkip": "pics/ads_skip.png",
}

fight_map = {
    # Fight
    "FightButton": "pics/fight_button.png",
}

common_map = {
    # Common
    "CancelBuy": "pics/cancel_button.png",
    "Exit": "pics/exit.png",
    "Confirm": "pics/confirm.png",
}

single_find_map = {
    # Main
    "ThankGift": "pics/thank_gift.png",

    # Visit
    "CardButton": "pics/card_button.png",
    "CardMode": "pics/card_mode.png",
    "CatCard": "pics/cat_card.png",
    "CatHouse": "pics/cat_house.png",
    "VisitBack": "pics/visit_back.png",
    "Confirm": "pics/confirm.png",
    "BackVisit": "pics/back_normal_visit.png",
    "VisitFriend": "pics/friend_list.png",
    "VisitButton": "pics/visiting_button.png",
    "FightSkip": "pics/fight_skip.png",
    "CancelBuy": "pics/cancel_button.png",
    "UseTicket": "pics/use_ticket.png",
    "VisitBusy": "pics/visit_busy.png",

    # Fight
    "TaskMain": "pics/task_main.png",
    "FightMain": "pics/fight_main.png",
    "FightEntry": "pics/fight_entry.png",
    "Exit": "pics/exit.png",
    "TicketRunout": "pics/ticket_runout.png",

}

resource_map = {
    "Main": main_map,
    "Fight": fight_map,
    "Visit": visit_map,
    "Common": common_map,
    "Single": single_find_map,
}

but_list = {}

no_cache_list = ["CatHouse", "Exit", "Replace"]


# Define a new print function with a timestamp
def print(*args, **kwargs):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    original_print(f'[{timestamp}]', *args, **kwargs)


def get_center(but, map_scope):
    if but in no_cache_list or but not in coor_dict:  # sometime scroll can change the pos
        location = pyautogui.locateOnScreen(resource_map[map_scope][but], confidence=0.8)
        coor_dict[but] = pyautogui.center(location)
    return coor_dict[but]


def get_all(but, map_scope):
    matches = list(pyautogui.locateAllOnScreen(resource_map[map_scope][but], confidence=0.8))
    coors = []
    prev = None
    for match in matches:
        if prev is None or abs(prev.top - match.top) > 20:
            prev = match
            coors.append(pyautogui.center(match))
    return coors


def get_all_with_cache(but, map_scope):
    if but not in but_list:
        but_list[but] = get_all(but, map_scope)
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


def find_button(map_scope):
    gray_screen = screen_shot()
    bts = []

    for button_name, template_path in resource_map[map_scope].items():
        if single_find_with_path(template_path, gray_screen):
            bts.append(button_name)
    return bts


def single_find(but):
    return single_find_with_path(single_find_map[but], None)


def single_find_with_path(but_path, gs):
    gray_screen = screen_shot() if gs is None else gs
    template = cv2.imread(but_path, 0)
    if template is None:
        print(f"Error: Unable to load '{but_path}'.")
        return False
    # Perform template matching
    result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        return True
    return False


def screen_shot():
    # Take a screenshot
    screenshot = pyautogui.screenshot()
    screen = np.array(screenshot)
    return cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
