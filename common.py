import time
from datetime import datetime
import pyautogui
import cv2
import numpy as np
import platform
import ctypes

from click import click_at

coor_dict = {}

# Load the button templates (for multiple buttons)
main_map = {
    # Main Run
    "RunButton": "pics/throwbutton.png",
    "Replace": "pics/replace.png",
    "NoMore": "pics/no_more.png",
    "Gift": "pics/gift.png",
    "Confirm": "pics/confirm.png",

    # Guess
    "Guess": "pics/guess.png",
    # Temp hard code
    # "GuessL": "pics/guess_left.png",
    # "GuessR": "pics/guess_right.png",
    "RobotDetect": "pics/robot_detect.png",

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
    "RobotDetect": "pics/robot_detect.png",
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
    "PKG": "pics/package.png",
    "TW": "pics/twenty_throw.png",
    "TWB": "pics/twenty_throw_on_bar.png",
    "ONE": "pics/one_throw.png",
    "ONEB": "pics/one_throw_on_bar.png",
    "FACE_UP_LEFT": "pics/face_up_left.png",

    # Visit
    "CardButton": "pics/card_button.png",
    "CardMode": "pics/card_mode.png",
    "CatCard": "pics/cat_card.png",
    "CatHouse": "pics/cat_house.png",
    "CatHouseNiu": "pics/cat_house_niu.png",
    "VisitBack": "pics/visit_back.png",
    "Confirm": "pics/confirm.png",
    "BackVisit": "pics/back_normal_visit.png",
    "VisitFriend": "pics/friend_list.png",
    "VisitButton": "pics/visiting_button.png",
    "FightSkip": "pics/fight_skip.png",
    "CancelBuy": "pics/cancel_button.png",
    "UseTicket": "pics/use_ticket.png",
    "VisitBusy": "pics/visit_busy.png",
    "OneMore": "pics/one_more.png",
    "VisitGoHome": "pics/visit_go_home.png",

    # Fight
    "TaskMain": "pics/task_main.png",
    "FightMain": "pics/fight_main.png",
    "FightEntry": "pics/fight_entry.png",
    "Exit": "pics/exit.png",
    "TicketRunout": "pics/ticket_runout.png",
    "FightButton": "pics/fight_button.png",

    # Red Pack
    "Chat": "pics/chat.png",
    "RollRed": "pics/roll_red_pack.png",
    "TakeRed": "pics/take_red_pack.png",
    "RedBack": "pics/red_pack_back.png",
    "DiamRed": "pics/diamond_red_pack.png",
    "ChatBar": "pics/chat_bar.png",
    "SendText": "pics/send_text.png",
    "MainBack": "pics/main_back.png",

    "TooManyRequest": "pics/too_many_request.png",

    # Robot check
    "RobotDetected": "pics/robot_detect.png",
    "Plus": "pics/plus_sign.png",
    "Equal": "pics/equal_sign.png",
    "QWD": "pics/question_wide.png",
    "QConfirm": "pics/question_confirm.png",
    "QReward": "pics/answer_reward.png",

    # Boss fight
    "BossDiam": "pics/boss_diamond.png",
    "BossFree": "pics/boss_free.png",
    "BossEnd": "pics/boss_no_ticket.png",
    "BossWorld": "pics/boss_world.png",
    "Group": "pics/group.png",
    "BossGroup": "pics/group_boss.png",
    "Challenge": "pics/challenge.png",
    "GoHome": "pics/go_home.png",
    "BossBack": "pics/boss_back.png",
    "WGoHome": "pics/world_go_home.png",
    "BGift": "pics/boss_gift.png",
    "GBossMain": "pics/group_boss_main.png",
}

resource_map = {
    "Main": main_map,
    "Fight": fight_map,
    "Visit": visit_map,
    "Common": common_map,
    "Single": single_find_map,
}

but_list = {}

no_cache_list = ["CatHouse", "Exit", "Replace", "Chat", "RollRed", "DiamRed", "Confirm", "Challenge"]

# Define a new print function with a timestamp
# Save the original built-in print function
original_print = print

def print(*args, **kwargs):
    """
    Custom print function with a timestamp.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Call the original print function
    original_print(f'[{timestamp}]', *args, **kwargs)


def get_scaling_factor():
    """
    Get the display scaling factor.
    """
    if platform.system() == "Windows":
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi / 96  # Standard DPI is 96
    elif platform.system() == "Darwin":
        # If macOS support is needed, implement Quartz-based scaling factor logic
        raise NotImplementedError("MacOS support for scaling factor is not implemented in this example.")
    else:
        return 1  # Default scaling factor for other systems

def get_center(but, map_scope):
    return get_center_h(but, map_scope, 0.8)

def simple_single_find(but, map_scope, th):
    try:
        pyautogui.locateOnScreen(resource_map[map_scope][but], confidence=th)
        return True
    except:
        return False
                                     
def get_center_h(but, map_scope, th):
    """
    Get the center coordinates of a button on the screen.
    """
    if but in no_cache_list or but not in coor_dict:  # Sometimes scroll can change the position
        try:
            location = pyautogui.locateOnScreen(resource_map[map_scope][but], confidence=th)
            if location is not None:
                coor_dict[but] = pyautogui.center(location)
            else:
                print(f"Warning: Button '{but}' not found on screen.")
                return None
        except:
            location = pyautogui.locateOnScreen(resource_map[map_scope][but], confidence=th)
            if location is not None:
                coor_dict[but] = pyautogui.center(location)
            else:
                print(f"Warning: Button '{but}' not found on screen.")
                return None
    return coor_dict.get(but)

def get_all(but, map_scope):
    """
    Get all matching locations of a button on the screen.
    """
    matches = []
    try:
        matches = list(pyautogui.locateAllOnScreen(resource_map[map_scope][but], confidence=0.8))
    except:
        matches = list(pyautogui.locateAllOnScreen(resource_map[map_scope][but]))
    coors = []
    prev = None
    for match in matches:
        if prev is None or abs(prev.top - match.top) > 20:
            prev = match
            coors.append(pyautogui.center(match))
    return coors

def get_all_with_cache(but, map_scope):
    """
    Get all cached locations of a button on the screen.
    """
    if but not in but_list:
        but_list[but] = get_all(but, map_scope)
    return but_list[but]

def find_button(map_scope):
    """
    Find buttons on the screen by matching templates.
    """
    gray_screen = screen_shot()
    bts = []
    for button_name, template_path in resource_map[map_scope].items():
        if single_find_with_path(template_path, gray_screen, 0.8):
            bts.append(button_name)
    return bts

def single_find(but):
    """
    Find a single button using its pre-defined template path.
    """
    return single_find_with_path(single_find_map[but], None, 0.8)

def single_find_with_path(but_path, gs, th):
    """
    Perform template matching using a specified template path.
    """
    gray_screen = screen_shot() if gs is None else gs
    template = cv2.imread(but_path, 0)
    if template is None:
        print(f"Error: Unable to load template from '{but_path}'.")
        return False
    # Perform template matching
    result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
    threshold = th
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        return True
    return False

def screen_shot():
    """
    Take a screenshot and convert it to a grayscale image for template matching.
    """
    screenshot = pyautogui.screenshot()
    screen = np.array(screenshot)
    return cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

def challenge_fight():
    count = 1
    while single_find("Challenge"):
        print ("Chanllenge not pass, fight again!")
        center = get_center("Challenge", "Single")
        click_at(center.x, center.y)
        time.sleep(3)
        print("Start challenge fight " + str(count))
        count += 1

        while simple_single_find("FightSkip", "Single", 0.9):
            print("Found Skip Button")
            cc = get_center("FightSkip", "Single")
            click_at(cc.x, cc.y)
            time.sleep(3)
    print ("Challenge fight " + str(count) + " then it succeeded!")


if __name__ == "__main__":
    challenge_fight()