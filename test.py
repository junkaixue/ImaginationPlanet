import pyautogui

from robot_check import *
from common import *
def for_test(file):
    results = easy_reader.readtext(file)
    # Concatenate all detected text
    for bbox, text, confidence in results:
        ct = text.strip()
        if ct.isdigit():
            print(int(ct))


#for_test("tmp.png")
# print(pyautogui.locateOnScreen("test/after_visit.png", confidence=0.8))
#print(pyautogui.locateOnScreen("pics/throwbutton.png", confidence=0.8))
# print(pyautogui.locateOnScreen("pics/face_up_left.png", confidence=0.8))
#print(pyautogui.locateOnScreen("pics/twenty_throw_on_bar.png", confidence=0.8))

print(single_find("S1V"
))


a = 585.0

print (int(a / 100))