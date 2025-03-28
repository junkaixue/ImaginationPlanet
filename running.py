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
    is_switch = False
    go_home = False

    def __init__(self, skip_cat_grab, go_home, semi_auto=False, is_switch=False, is_niu=False):
        self.semi_auto = semi_auto
        self.go_home = go_home
        self.sft = get_scaling_factor()
        self.is_switch = is_switch
        print("Scaling factor : " + str(self.sft))
        self.sc = skip_cat_grab
        self.is_niu = is_niu
        self.back_visit = None
        self.card_button = None
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

    def long_click(self):
        # Move to the position (if necessary)
        pyautogui.moveTo(self.rb.x, self.rb.y)

        # Press and hold the mouse button
        pyautogui.mouseDown()

        # Wait for 2 seconds
        time.sleep(2)

        # Release the mouse button
        pyautogui.mouseUp()

    def guess(self):
        click_at(self.rb.x / self.sft - 50, self.rb.y / self.sft)
        time.sleep(1)
        click_at(self.rb.x / self.sft + 50, self.rb.y / self.sft)
        time.sleep(1)

    def visiting(self):
        time.sleep(4)
        if not self.sc:
            self.grab_cat()
        if self.go_home or self.is_niu:
            print("Going home!")
            while single_find("VisitGoHome"):
                try:
                    center = get_center("VisitGoHome", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    print("Clicked go home!")
                    time.sleep(2)
                    center = get_center("Confirm", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    print("Clicked confirm button!")
                    time.sleep(2)
                    if single_find("VisitBack"):
                        center = get_center("VisitBack", "Single")
                        click_at(center.x / self.sft, center.y / self.sft)
                        time.sleep(2)
                except:
                    print("Super slow in loading animation")

            print("Go home directly")
            return
        print("In visiting mode!")
        self.visits += 1
        for i in range(1, 2000):
            if single_find("Confirm"):
                try:
                    print("Confirm of high rolling!")
                    center = get_center("Confirm", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                except:
                    time.sleep(1)
                    continue
                time.sleep(1)
            btl = find_button("Visit")
            if "Roll" in btl:
                print("Found Rolling!")
                if self.is_switch:
                    while single_find("OneMore"):
                        print("High times, one more!")
                        center = get_center("OneMore", "Single")
                        click_at(center.x / self.sft, center.y / self.sft)
                        time.sleep(1)
                        while single_find("UseTicket"):
                            print("Use ticket!")
                            cc = get_center("UseTicket", "Single")
                            click_at(cc.x / self.sft, cc.y / self.sft)
                            time.sleep(1)
                            click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                            time.sleep(1)
                        while single_find("Confirm"):
                            print("Confirm ticket!")
                            cc = get_center("Confirm", "Single")
                            click_at(cc.x / self.sft, cc.y / self.sft)
                            time.sleep(1)

                else:
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
                print("Too many request!")
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
        cat_house_name = ("CatHouseNiu" if self.is_niu else "CatHouse")
        while True:
            scrolls -= 1
            if scrolls == 0:
                break
            elif not single_find(cat_house_name):
                pyautogui.vscroll(-100)
                print("Cat House not found, " + str(scrolls) + " retries remain")
                continue
            else:
                break
        while single_find(cat_house_name):
            try:
                lc = get_center(cat_house_name, "Single")
                vc = get_center("VisitButton", "Single")
                # print(f"Image found at: {center.y}")
                click_at((vc.x / self.sft), (lc.y / self.sft))
                print("Clicked cat house")
                time.sleep(1)
            except:
                print("Cat house already clicked")

        if not single_find("VisitGoHome"):
            print("Not in visiting main page, retry!")
            time.sleep(3)
            return False
        print("Finish finding, go to visiting")
        return True

    def grab_cat(self):
        if self.cg == 0:
            print("Skip cat grab")
            return
        self.cg -= 1
        retry = 10
        while not single_find("CardButton"):
            if single_find("RobotDetected"):
                if self.rd is None:
                    self.rd = RobotCheck(self.sft)
                self.rd.break_check()
                time.sleep(1)
                continue
            print("Card Button is not found!")
            click_at(self.rb.x / self.sft, self.rb.y / self.sft)
            time.sleep(2)
            if single_find("UseTicket"):
                center = get_center("UseTicket", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(2)
            retry -= 1
            if retry <= 0:
                print("Retry runs out for card button found!")
                return
        retry = 10
        while not single_find("CardMode"):
            if single_find("RobotDetected"):
                if self.rd is None:
                    self.rd = RobotCheck(self.sft)
                self.rd.break_check()
                time.sleep(1)
                continue
            while self.card_button is None:
                try:
                    self.card_button = get_center("CardButton", "Single")
                except:
                    print("Card button not found")
                    time.sleep(2)
            click_at(self.card_button.x / self.sft, self.card_button.y / self.sft)
            print(
                "Found card button at " + str(self.card_button.x / self.sft) + " " + str(self.card_button.y / self.sft))
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
                if self.rd is None:
                    self.rd = RobotCheck(self.sft)
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
                    if self.rd is None:
                        self.rd = RobotCheck(self.sft)
                    self.rd.break_check()
                    time.sleep(1)
                    continue
                print("Visit busy!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
        while single_find("CardMode"):
            if single_find("RobotDetected"):
                if self.rd is None:
                    self.rd = RobotCheck(self.sft)
                self.rd.break_check()
                time.sleep(1)
                continue
            click_at(self.rb.x / self.sft, self.rb.y / self.sft - 300)
            time.sleep(2)
            while self.back_visit is None:
                try:
                    self.back_visit = get_center("BackVisit", "Single")
                except:
                    print("Back Visit not found")
                    time.sleep(2)
            click_at(self.back_visit.x / self.sft, self.back_visit.y / self.sft)
            time.sleep(1)
        print("Exited card mode, start running...")

    def light_run(self):
        if not self.semi_auto:
            self.long_click()
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
                while not self.find_cat_house():
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(1)
                    click_at(center.x / self.sft, center.y / self.sft - 200)
                self.visiting()
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
                print("Robot detected!")
                if self.rd is None:
                    self.rd = RobotCheck(self.sft)
                self.rd.break_check()
                time.sleep(1)
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)
                self.long_click()
                time.sleep(1)
            elif single_find("PKG"):
                click_at(self.rb.x / self.sft, self.rb.y / self.sft + 100)
                time.sleep(1)
            elif not self.semi_auto and simple_single_find("RunButton", "Main", 0.8):
                print("Auto run stopped, resume it...")
                self.long_click()
                time.sleep(2)
            else:
                print("In running!")
                time.sleep(5)

    def switch_run(self):
        while True:
            if single_find("FACE_UP_LEFT"):
                self.switch("ONE", "TWB")
            else:
                if single_find("TW"):
                    self.switch("TW", "ONEB")

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
                click_at(center.x / self.sft, center.y / self.sft - 200)
                if not self.find_cat_house():
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(1)
                    click_at(center.x / self.sft, center.y / self.sft - 200)
                    self.find_cat_house()
                self.visiting()
                time.sleep(1)
                continue
            elif "Replace" in bts:
                print("Found replacement let's wait!")
                # center = get_center("Replace", "Main")
                # click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(5)
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
                print("Too many requests!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif "RobotDetect" in bts:
                print("Robot detected!")
                if self.rd is None:
                    self.rd = RobotCheck(self.sft)
                self.rd.break_check()
                time.sleep(1)
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)
                self.long_click()
                time.sleep(1)
            elif single_find("PKG"):
                click_at(self.rb.x / self.sft, self.rb.y / self.sft + 100)
                time.sleep(1)
            else:
                self.count += 1
                print("Keep running! This is " + str(self.count) + " clicks")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(4.5)

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
                print("Too many requests!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            else:
                self.count += 1
                print("Keep running! This is " + str(self.count) + " clicks")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(0.5)

    def switch(self, from_s, to_s):
        while single_find(from_s):
            center = get_center(from_s, "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
            try:
                center = get_center(to_s, "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            except:
                print("Switch failed, retry...")
        print("Switched to " + to_s)


if __name__ == '__main__':
    r = MainRun(True)
    r.switch_run()
