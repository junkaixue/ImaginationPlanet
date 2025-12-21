from time import sleep

from common import *
from platform_config import CURRENT_PLATFORM

# from robot_check import *
# from common import *
# def for_test(file):
#     results = easy_reader.readtext(file)
#     # Concatenate all detected text
#     for bbox, text, confidence in results:
#         ct = text.strip()
#         if ct.isdigit():
#             print(int(ct))


# for_test("tmp.png")
# print(pyautogui.locateOnScreen("test/after_visit.png", confidence=0.8))
# print(pyautogui.locateOnScreen("pics/throwbutton.png", confidence=0.8))
# print(pyautogui.locateOnScreen("pics/face_up_left.png", confidence=0.8))
# print(pyautogui.locateOnScreen("pics/twenty_throw_on_bar.png", confidence=0.8))
print(CURRENT_PLATFORM)
print("\n=== Testing simple_single_find for RunButton ===\n")

if simple_single_find("RunButton", "Main", 0.75):
    print("\n✅ RunButton FOUND!")
    print("\nNow getting center coordinates...")
    center = get_center("RunButton", "Main")  # Fixed: use "Main" scope
    if center:
        print(f"Center: ({center[0]}, {center[1]})")
        # Uncomment to actually click:
        click_at(center[0], center[1])
        # time.sleep(1)
    else:
        print("Error: Could not get center coordinates")
else:
    print("\n❌ RunButton NOT FOUND")
    print("Make sure the RunButton is visible on screen!")
# # Mac needs larger scroll values
# scroll_up = 1000
# scroll_down = -100
#
# click_at(2660, 1164)
# sleep(1)
#
# pyautogui.vscroll(scroll_up)  # Make it top
# sleep(1)
# pyautogui.vscroll(-70)  # Make it bottom
# sleep(1)
# pyautogui.vscroll(-70)  # Make it