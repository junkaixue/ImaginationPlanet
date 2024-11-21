import time

from click import *
from common import *
from fight import Fight


class MainRun:
    sft = 0.0
    rb = None
    count = 0
    visits = 1
    f = Fight()

    def __init__(self):
        self.sft = get_scaling_factor()
        found_rb = False

        while not found_rb:
            try:
                self.rb = get_center("RunButton", "Main")
                found_rb = True
            except:
                print("Run Botton was not found!")
        print("Found the Run Button!")

    def visiting(self):
        time.sleep(2)
        self.grab_cat()
        self.visits += 1
        for i in range(1, 2000):
            btl = find_button("Visit")
            if "Roll" in btl:
                print("Found Rolling!")
                center = get_center("Roll", "Visit")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                print("Complete Rolling!")
            elif "VisitComplete" in btl:
                print("Complete visiting!")
                cc = get_center("VisitBack", "Single")
                # click twice
                click_at(cc.x / self.sft, cc.y / self.sft)
                time.sleep(1)
                click_at(cc.x / self.sft, cc.y / self.sft)
                break
            elif "Timeout" in btl:
                print("Visit timeout!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                return
            elif "VisitBusy" in btl:
                print("Visit busy!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif "AdsSkip" in btl:
                print("Ads skipped!")
                center = get_center("UseTicket", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            else:
                print("Keep visiting!")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)

    def guess(self):
        # l = get_center("GuessL", "Main")
        click_at(self.rb.x / self.sft - 50, self.rb.y / self.sft)
        time.sleep(1)
        # r = get_center("GuessR", "Main")
        click_at(self.rb.x / self.sft + 50, self.rb.y / self.sft)

    def find_cat_house(self):
        click_at(1200, 500)
        pyautogui.scroll(10)  # Make it top
        while True:
            if not single_find("CatHouse"):
                pyautogui.scroll(-2)
                continue
            else:
                break

        lc = get_center("CatHouse", "Single")
        vc = get_center("VisitButton", "Single")
        # print(f"Image found at: {center.y}")
        click_at((vc.x / self.sft), (lc.y / self.sft))

    def grab_cat(self):
        while not single_find("CardButton"):
            print("Card Button is not found!")
            time.sleep(1)
        while not single_find("CardMode"):
            card_button = get_center("CardButton", "Single")
            click_at(card_button.x / self.sft, card_button.y / self.sft)
            print("Found card button at " + str(card_button.x / self.sft) + " " + str(card_button.y / self.sft))
            time.sleep(1)
            click_at(self.rb.x / self.sft, self.rb.y / self.sft)
            time.sleep(5)
        print("Card already opened!")
        time.sleep(1)
        if single_find("CatCard"):
            cc = get_center("CatCard", "Single")
            # Move the cursor to the starting point
            pyautogui.moveTo(cc.x / self.sft, cc.y / self.sft, duration=0.5)
            # Drag the cursor to the destination point
            pyautogui.dragTo(cc.x / self.sft, cc.y / self.sft - 300, duration=1, button='left')
            time.sleep(8)
            # Can be busy sometime
            while single_find("VisitBusy"):
                print("Visit busy!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
        while single_find("CardMode"):
            click_at(self.rb.x / self.sft, self.rb.y / self.sft - 300)
            time.sleep(2)
            bv = get_center("BackVisit", "Single")
            click_at(bv.x / self.sft, bv.y / self.sft)
            time.sleep(1)
        print("Exited card mode, start running...")

    def run(self):
        while True:
            bts = find_button("Main")
            if "Guess" in bts:
                print("Found Guess! Let's guess!")
                self.guess()
                time.sleep(2)
                continue
            elif "VisitMain" in bts:
                print("Visiting! This is " + str(self.visits) + " visit!")
                center = get_center("VisitFriend", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                self.find_cat_house()
                self.visiting()
                time.sleep(1)
                continue
            elif "Replace" in bts:
                print("Found replacement! Take it!")
                center = get_center("Replace", "Main")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                continue
            elif "Gift" in bts:
                print("Need to thank the gift sender!")
                center = get_center("Exit", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                continue
            elif "NoMore" in bts:
                print("This RUN is DONE!! Total " + str(self.visits) + " visits!")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)
                self.f.fight()
                print("Complete fight after running!")
                return
            else:
                self.count += 1
                print("Keep running! This is " + str(self.count) + " clicks")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(0.5)


if __name__ == '__main__':
    r = MainRun()
    r.visiting()
