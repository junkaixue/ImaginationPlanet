from time import sleep

from common import *

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

# if single_find("Disconnected"):
#     print("Find disconnected")
#     center = get_center("Disconnected", "Single")
#     click_at(center.x / 1, center.y / 1 + 200)
#     time.sleep(1)
# # Mac needs larger scroll values
scroll_up = 1000
scroll_down = -100

click_at(2660, 1164)
sleep(1)

pyautogui.vscroll(scroll_up)  # Make it top
sleep(1)
pyautogui.vscroll(-70)  # Make it bottom
sleep(1)
pyautogui.vscroll(-70)  # Make it