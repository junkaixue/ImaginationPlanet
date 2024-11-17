from common import *
from click import *

class MainRun:
    sft = 0.0
    rb = None
    count = 0
    visits = 0

    def __init__(self):
        self.sft = get_scaling_factor()
        found_rb = False

        while not found_rb:
            try:
                self.rb = get_center("RunButton")
                found_rb = True
            except:
                print("Run Botton was not found!")
        print("Found the Run Button!")


    def visiting(self):
        self.visits += 1
        for i in range(1, 500):
            btl = find_button()
            if "Roll" in btl:
                print("Found Rolling!")
                center = get_center("Roll")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                print("Complete Rolling!")
            elif "VisitComplete" in btl:
                print("Complete visiting!")
                cc = get_center("VisitBack")
                click_at(cc.x / self.sft, cc.y / self.sft)
                break
            else:
                print("Keep visiting!")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)


    def guess(self):
        l = get_center("GuessL")
        click_at(l.x / self.sft, l.y / self.sft)
        time.sleep(1)
        r = get_center("GuessR")
        click_at(r.x / self.sft, r.y / self.sft)


    def find_cat_house(self):
        click_at(1200, 500)
        pyautogui.scroll(10)  # Make it top
        while True:
            if "CatHouse" not in find_button():
                pyautogui.scroll(-2)
                continue
            else:
                break

        lc = get_center("CatHouse")
        vc = get_center("VisitButton")
        # print(f"Image found at: {center.y}")
        click_at((vc.x / self.sft), (lc.y / self.sft))


    def grab_cat(self):
        card_button = get_center("CardButton")
        click_at(card_button.x / self.sft, card_button.y / self.sft)
        print("Found card button at " + str(card_button.x / self.sft) + " " + str(card_button.y / self.sft))
        time.sleep(1)
        click_at(self.rb.x / self.sft, self.rb.y / self.sft)  # open card


    def run(self):
        while True:
            bts = find_button()
            if "Guess" in bts:
                print("Found Guess! Let's guess!")
                self.guess()
                time.sleep(2)
                continue
            elif "VisitMain" in bts:
                print("Visiting! This is " + str(self.visits) + " visit!")
                center = get_center("VisitFriend")
                click_at(center.x / self.sft, center.y / self.sft)
                self.find_cat_house()
                self.visiting()
                time.sleep(1)
                continue
            elif "Replace" in bts:
                print("Found replacement! Take it!")
                center = get_center("Replace")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                continue
            elif "NoMore" in bts:
                print("This RUN is DONE!!")
                exit(0)
            else:
                self.count += 1
                print("Keep running! Spend " + str(self.count) + " dices")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(0.5)

