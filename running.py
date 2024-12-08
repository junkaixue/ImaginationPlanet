import time

from click import *
from common import *
from robot_check import RobotCheck


class MainRun:
    sft = 0.0
    rb = None
    count = 0
    visits = 1
    sc = False
    cg = 5
    rd = None

    def __init__(self, skip_cat_grab):
        self.sft = get_scaling_factor()
        print ("Scaling factor : " + str(self.sft))
        self.sc = skip_cat_grab
        found_rb = False
        retry = 50
        while not found_rb:
            try:
                self.rb = get_center("RunButton", "Main")
                found_rb = True
            except:
                print("Run Botton was not found!")
                retry -= 1
                if retry == 0:
                    print("No run button, stop!")
                    exit(0)
                time.sleep(1)
        print("Found the Run Button!")
        self.long_click()

    def long_click(self):
        # Move to the position (if necessary)
        pyautogui.moveTo(self.rb.x, self.rb.y)

        # Press and hold the mouse button
        pyautogui.mouseDown()

        # Wait for 2 seconds
        time.sleep(2)

        # Release the mouse button
        pyautogui.mouseUp()

    def visiting(self):
        time.sleep(2)
        if not self.sc:
            self.grab_cat()
        print ("In visiting mode!")
        self.visits += 1
        for i in range(1, 2000):
            btl = find_button("Visit")
            if "Roll" in btl:
                print("Found Rolling!")
                center = get_center("Roll", "Visit")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                while single_find("Confirm"):
                    click_at(center.x / self.sft, center.y / self.sft)
                print("Complete Rolling!")
            elif "VisitComplete" in btl:
                print("Complete visiting!")
                while single_find("VisitBack"):
                    cc = get_center("VisitBack", "Single")
                    click_at(cc.x / self.sft, cc.y / self.sft)
                    time.sleep(1)
                return
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
            elif "TooManyRequest" in btl:
                print ("Too many request!")
                center = get_center("TooManyRequest", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif "AdsSkip" in btl:
                print("Ads skipped!")
                center = get_center("UseTicket", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif "RobotDetect" in btl:
                print("Robot detected!")
                if self.rd is None:
                    self.rd = RobotCheck(self.sft)
                self.rd.break_check()
                time.sleep(1)
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)
            else:
                print("Keep visiting!")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)

    def find_cat_house(self):
        pyautogui.vscroll(100)  # Make it top
        scrolls = 50
        while True:
            scrolls -= 1
            if scrolls == 0:
                return False
            elif not single_find("CatHouse"):
                pyautogui.vscroll(-100)
                print ("Cat House not found, " + str(scrolls) + " retries remain")
                continue
            else:
                break
        while single_find("CatHouse"):
            try:
                lc = get_center("CatHouse", "Single")
                vc = get_center("VisitButton", "Single")
                # print(f"Image found at: {center.y}")
                click_at((vc.x / self.sft), (lc.y / self.sft))
                print ("Clicked cat house")
            except:
                print ("Cat house already clicked")
            
                
        print ("Finish finding, go to visiting")
        return True

    def grab_cat(self):
        if self.cg == 0:
            print ("Skip cat grab")
            return
        self.cg -= 1
        retry = 10
        while not single_find("CardButton"):
            if single_find("RobotDetected"):
                self.rd.break_check()
                time.sleep(1)
                continue
            print("Card Button is not found!")
            time.sleep(2)
            retry -= 1
            if retry <= 0:
                print("Retry runs out for card button found!")
                return
        retry = 10
        while not single_find("CardMode"):
            if single_find("RobotDetected"):
                self.rd.break_check()
                time.sleep(1)
                continue
            card_button = get_center("CardButton", "Single")
            click_at(card_button.x / self.sft, card_button.y / self.sft)
            print("Found card button at " + str(card_button.x / self.sft) + " " + str(card_button.y / self.sft))
            time.sleep(1)
            click_at(self.rb.x / self.sft, self.rb.y / self.sft)
            time.sleep(1)
            if single_find("VisitBusy"):
                print("Visit busy!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(5)
        print("Card already opened!")
        time.sleep(1)
        if single_find("CatCard"):
            if single_find("RobotDetected"):
                self.rd.break_check()
                time.sleep(1)
            cc = get_center("CatCard", "Single")
            # Move the cursor to the starting point
            pyautogui.moveTo(cc.x / self.sft, cc.y / self.sft, duration=0.5)
            # Drag the cursor to the destination point
            pyautogui.dragTo(cc.x / self.sft, cc.y / self.sft - 300, duration=1, button='left')
            time.sleep(8)
            # Can be busy sometime
            while single_find("VisitBusy"):
                if single_find("RobotDetected"):
                    self.rd.break_check()
                    time.sleep(1)
                    continue
                print("Visit busy!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
        while single_find("CardMode"):
            if single_find("RobotDetected"):
                self.rd.break_check()
                time.sleep(1)
                continue
            click_at(self.rb.x / self.sft, self.rb.y / self.sft - 300)
            time.sleep(2)
            bv = get_center("BackVisit", "Single")
            click_at(bv.x / self.sft, bv.y / self.sft)
            time.sleep(1)
        print("Exited card mode, start running...")

    def light_run(self):
        while True:
            bts = find_button("Main")
            if "VisitMain" in bts:
                print("Visiting! This is " + str(self.visits) + " visit!")
                center = get_center("VisitFriend", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft - 200)
                if not self.find_cat_house():
                     click_at(center.x / self.sft, center.y / self.sft)
                     time.sleep(1)
                     click_at(center.x / self.sft, center.y / self.sft - 200)
                     self.find_cat_house()
                self.visiting()
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
                return
            elif "Confirm" in bts:
                while single_find("Confirm"):
                    center = get_center("Confirm", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(1)
                self.long_click()
            elif "RobotDetect" in bts:
                print ("Robot detected!")
                if self.rd is None:
                    self.rd = RobotCheck(self.sft)
                self.rd.break_check()
                time.sleep(1)
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)
                self.long_click()
                time.sleep(1)
            elif single_find("PKG"):
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)
            elif simple_single_find("RunButton", "Main", 0.8):
                print ("Auto run stopped, resume it...")
                self.long_click()
                time.sleep(2)
            else:
                print ("In running!")
                time.sleep(5)

    def run(self):
        while True:
            bts = find_button("Main")
            if "Guess" in bts:
                print("Found Guess! Let's guess!")
                # self.guess()
                time.sleep(2)
                continue
            elif "VisitMain" in bts:
                print("Visiting! This is " + str(self.visits) + " visit!")
                center = get_center("VisitFriend", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                if not self.find_cat_house():
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
                return
            elif "ToManyRequest" in bts:
                print ("Too many requests!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            else:
                self.count += 1
                print("Keep running! This is " + str(self.count) + " clicks")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(0.5)


if __name__ == '__main__':
    r = MainRun(True)
    r.visiting()
