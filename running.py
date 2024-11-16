import cv2
import numpy as np
import pyautogui
from click import click_at
import time
import Quartz
from datetime import datetime



# Load the button templates (for multiple buttons)
templates = {
    "RunButton": "pics/throwbutton.png",
    "VisitMain": "pics/visiting_main.png",
    "VisitFriend": "pics/friend_list.png",
    "VisitComplete": "pics/visiting_complete.png",
    "VisitButton": "pics/visiting_button.png",
    "VisitBack": "pics/visit_back.png",
    "CardButton": "pics/card_button.png",
    "Roll": "pics/rolling.png",
    "Guess": "pics/guess.png",
    "GuessL": "pics/guess_left.png",
    "GuessR": "pics/guess_right.png",
    "CatHouse": "pics/cat_house.png",
    "Replace": "pics/replace.png",
    "NoMore": "pics/no_more.png"
}


# Preserve the original print function
original_print = print

coor_dict = {}

# Define a new print function with a timestamp
def print(*args, **kwargs):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    original_print(f'[{timestamp}]', *args, **kwargs)


def get_center(but):
    if but == "VisitButton" or but not in coor_dict: # sometime scroll can change the pos
        location = pyautogui.locateOnScreen(templates[but], confidence=0.8)
        coor_dict[but] = pyautogui.center(location)
    return coor_dict[but]
    


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

    for button_name, template_path in templates.items():
        template = cv2.imread(template_path, 0)
        if template is None:
            print(f"Error: Unable to load '{template_path}'.")
            continue
        # Perform template matching
        result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            #print ("Found " + button_name)
            bts.append(button_name)
    return bts


def visiting(sft, rb):
    for i in range(1,500):
        btl = find_button()
        if "Roll" in btl:
            print ("Found Rolling!")
            center = get_center("Roll")
            click_at(center.x / sft, center.y / sft)
            time.sleep(1)
            click_at(center.x / sft, center.y / sft)
            print ("Complete Rolling!")
        elif "VisitComplete" in btl:
            print ("Complete visiting!")
            cc = get_center("VisitBack")
            click_at(cc.x / sft, cc.y / sft)
            break
        else:
            print ("Keep visiting!")
            click_at(rb.x / sft, rb.y / sft)
            time.sleep(1)

def guess(sft):
    l = get_center("GuessL")
    click_at(l.x / sft, l.y / sft)
    time.sleep(1)
    r = get_center("GuessR")
    click_at(r.x / sft, r.y / sft)

def find_cat_house(scale_ft):
    click_at(1200, 500)
    pyautogui.scroll(10) # Make it top
    while True:
        if "CatHouse" not in find_button():
            pyautogui.scroll(-2)
            continue
        else:
            break
        
    lc = get_center("CatHouse")
    vc = get_center("VisitButton")
    # print(f"Image found at: {center.y}")
    click_at((vc.x / scale_ft) , (lc.y / scale_ft))
    
def grab_cat(sft, rb):
    card_button = get_center("CardButton")
    click_at(card_button.x / sft, card_button.y / sft)
    print ("Found card button at " +  str(card_button.x / sft) + " " + str(card_button.y / sft))
    time.sleep(1)
    click_at(rb.x / sft, rb.y / sft) # open card
    
    
sft =  get_scaling_factor()
found_rb = False

while not found_rb:
    try:
        rb = get_center("RunButton")
        found_rb = True
    except:
        print ("Run Botton was not found!")

print ("Found the Run Button!")

#grab_cat(sft, rb)


#exit(0)





count = 0
while True:
    bts = find_button()
    if  "Guess" in bts:
        print ("Found Guess! Let's guess!")
        guess(sft)
        time.sleep(2)
        continue
    elif "VisitMain" in bts:
        print ("Visiting!")
        center = get_center("VisitFriend")
        click_at(center.x /sft, center.y / sft)
        find_cat_house(sft)
        visiting(sft, rb)
        time.sleep(1)
        continue
    elif "Replace" in bts:
        print ("Found replacement! Take it!")
        center = get_center("Replace")
        click_at(center.x /sft, center.y / sft)
        time.sleep(1)
        continue
    elif "NoMore" in bts:
        print ("This RUN is DONE!!")
        exit(0)
    else:
        count += 1
        print ("Keep running! Spend " + str(count)+ " dices")
        click_at(rb.x / sft, rb.y/sft)
        time.sleep(0.5)
    
#find_button()
#visiting()
