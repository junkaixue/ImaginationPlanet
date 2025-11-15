import time
import platform

from click import *
from common import *
from smart_card_grab import SmartCardGrab
from log_helper import log


class MainRun:
    sft = 0.0
    rb = None
    count = 0
    visits = 1
    sc = False
    cg = 5
    is_switch = False
    go_home = False
    is_mac = platform.system() == "Darwin"
    smart_grab = None  # Smart card grab handler

    def __init__(self, skip_cat_grab, go_home, semi_auto=False, is_switch=False, is_niu=False):
        self.semi_auto = semi_auto
        self.go_home = go_home
        self.sft = get_scaling_factor()
        self.is_switch = is_switch
        self.is_niu = is_niu

        # Mac-specific optimizations
        if self.is_mac:
            self.cg = 10  # More cat grabs on Mac

        log("Scaling factor : " + str(self.sft))
        self.sc = skip_cat_grab
        self.back_visit = None
        self.card_button = None
        found_rb = False
        retry = 50
        while not found_rb:
            try:
                self.rb = get_center("RunButton", "Main")
                found_rb = True
            except:
                log("Run Botton was not found!")
                retry -= 1
                if retry == 0:
                    log("No run button, stop!")
                    exit(0)
                time.sleep(1)

        # Mac uses scaling factor of 1
        if self.is_mac:
            self.sft = 1

        # Initialize smart card grab handler
        self.smart_grab = SmartCardGrab(sft=self.sft, rb=self.rb)

        log("Found the Run Button!")

    def long_click(self):
        # Move to the position (if necessary)
        pyautogui.moveTo(self.rb.x / self.sft, self.rb.y / self.sft)

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
        time.sleep(4 if self.is_mac else 2)
        # Disable grab cat
        # if not self.sc:
        #     self.grab_cat()

        if self.go_home or self.is_niu:
            log("Going home!")
            while single_find("VisitGoHome"):
                try:
                    center = get_center("VisitGoHome", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    log("Clicked go home!")
                    time.sleep(2)
                    center = get_center("Confirm", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    log("Clicked confirm button!")
                    time.sleep(2)
                    if single_find("VisitBack"):
                        center = get_center("VisitBack", "Single")
                        click_at(center.x / self.sft, center.y / self.sft)
                        time.sleep(2)
                except:
                    log("Super slow in loading animation")

            log("Go home directly")
            return
        log("In visiting mode!")
        self.visits += 1

        for i in range(1, 2000):
            # Check for duplicate visit before each roll
            if not self.sc:
                try:
                    if self.smart_grab._check_face_in_any_box():
                        log("🎯 Duplicate visit detected in visiting loop, triggering smart card grab!")
                        if self.smart_grab.smart_grab_cat():
                            log("�?Successfully used AgainCard, returning to main mode!")
                except Exception as e:
                    log(f"Smart grab check failed: {e}")

            if single_find("Confirm") and not self.is_mac:
                try:
                    log("Confirm of high rolling!")
                    center = get_center("Confirm", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                except:
                    time.sleep(1)
                    continue
                time.sleep(1)
            btl = find_button("Visit")
            if "Roll" in btl:
                log("Found Rolling!")
                if self.is_switch:
                    while single_find("OneMore"):
                        log("High times, one more!")
                        center = get_center("OneMore", "Single")
                        click_at(center.x / self.sft, center.y / self.sft)
                        time.sleep(1)
                        while single_find("UseTicket"):
                            log("Use ticket!")
                            cc = get_center("UseTicket", "Single")
                            click_at(cc.x / self.sft, cc.y / self.sft)
                            time.sleep(1)
                            click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                            time.sleep(1)
                        while single_find("Confirm"):
                            log("Confirm ticket!")
                            cc = get_center("Confirm", "Single")
                            click_at(cc.x / self.sft, cc.y / self.sft)
                            time.sleep(1)

                else:
                    center = get_center("Roll", "Visit")
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(1)
                    while single_find("HConfirm"):
                        click_at(center.x / self.sft, center.y / self.sft)
                log("Complete Rolling!")
            elif "VisitComplete" in btl:
                log("Complete visiting!")
                while single_find("VisitBack"):
                    cc = get_center("VisitBack", "Single")
                    click_at(cc.x / self.sft, cc.y / self.sft)
                    time.sleep(1)
                return
            elif "Timeout" in btl:
                log("Visit timeout!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                return
            elif "VisitBusy" in btl:
                log("Visit busy!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif "TooManyRequest" in btl:
                log("Too many request!")
                center = get_center("TooManyRequest", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif "AdsSkip" in btl:
                log("Ads skipped!")
                center = get_center("UseTicket", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            else:
                log("Keep visiting!")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)

    def find_cat_house(self):
        # Use relative coordinates from config instead of scrolling and image recognition
        cat_house_coords = self.smart_grab.config.get_coord("cat_house")
        if not cat_house_coords:
            log("ERROR: cat_house coordinate not found in config!")
            return False

        log("Clicking cat house using relative coordinates")
        click_at(cat_house_coords[0], cat_house_coords[1])
        time.sleep(1)

        if not single_find("VisitGoHome"):
            log("Not in visiting main page, retry!")
            time.sleep(3)
            return False
        log("Finish finding, go to visiting")
        return True

        # OLD IMPLEMENTATION - Kept for future reference
        # # Mac needs larger scroll values
        # scroll_up = 100 if self.is_mac else 10
        # scroll_down = -100 if self.is_mac else -2
        #
        # pyautogui.vscroll(scroll_up)  # Make it top
        # scrolls = 50
        # cat_house_name = ("CatHouseNiu" if self.is_niu else "CatHouse")
        # while True:
        #     scrolls -= 1
        #     if scrolls == 0:
        #         break
        #     elif not single_find(cat_house_name):
        #         pyautogui.vscroll(scroll_down)
        #         log("Cat House not found, " + str(scrolls) + " retries remain")
        #         continue
        #     else:
        #         break
        # while single_find(cat_house_name):
        #     try:
        #         lc = get_center(cat_house_name, "Single")
        #         vc = get_center("VisitButton", "Single")
        #         # log(f"Image found at: {center.y}")
        #         click_at((vc.x / self.sft), (lc.y / self.sft))
        #         log("Clicked cat house")
        #         time.sleep(1)
        #     except:
        #         log("Cat house already clicked")
        #
        # if not single_find("VisitGoHome"):
        #     log("Not in visiting main page, retry!")
        #     time.sleep(3)
        #     return False
        # log("Finish finding, go to visiting")
        # return True

    def grab_cat(self):
        if self.cg == 0:
            log("Skip cat grab")
            return
        self.cg -= 1
        retry = 10
        while not single_find("CardButton"):
            log("Card Button is not found!")
            click_at(self.rb.x / self.sft, self.rb.y / self.sft)
            time.sleep(2)
            if single_find("UseTicket"):
                center = get_center("UseTicket", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(2)
            retry -= 1
            if retry <= 0:
                log("Retry runs out for card button found!")
                return
        retry = 10
        while not single_find("CardMode"):
            while self.card_button is None:
                try:
                    self.card_button = get_center("CardButton", "Single")
                except:
                    log("Card button not found")
                    time.sleep(2)
            click_at(self.card_button.x / self.sft, self.card_button.y / self.sft)
            log(
                "Found card button at " + str(self.card_button.x / self.sft) + " " + str(self.card_button.y / self.sft))
            time.sleep(1)
            click_at(self.rb.x / self.sft, self.rb.y / self.sft)
            time.sleep(1)
            if single_find("VisitBusy"):
                log("Visit busy!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(5)
        log("Card already opened!")
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
                log("Visit busy!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
        while single_find("CardMode"):
            click_at(self.rb.x / self.sft, self.rb.y / self.sft - 300)
            time.sleep(2)
            while self.back_visit is None:
                try:
                    self.back_visit = get_center("BackVisit", "Single")
                except:
                    log("Back Visit not found")
                    time.sleep(2)
            click_at(self.back_visit.x / self.sft, self.back_visit.y / self.sft)
            time.sleep(1)
        log("Exited card mode, start running...")

    def light_run(self):
        if not self.semi_auto:
            self.long_click()
        while True:
            bts = find_button("Main")
            if "VisitMain" in bts:
                log("Visiting! This is " + str(self.visits) + " visit!")
                center = get_center("VisitFriend", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft - 200)
                while not self.find_cat_house():
                    time.sleep(1)
                self.visiting()
                time.sleep(1)
                continue
            elif "NoMore" in bts:
                log("This RUN is DONE!! Total " + str(self.visits) + " visits!")
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
                log("Robot detected!")
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
                log("Auto run stopped, resume it...")
                self.long_click()
                time.sleep(2)
            else:
                log("In running!")
                time.sleep(5)

    def switch_run(self):
        while True:
            if simple_single_find("FACE_UP_LEFT", "Single", 0.65):
                self.switch("ONE", "TWB")
            else:
                if single_find("TW"):
                    self.switch("TW", "ONEB")

            bts = find_button("Main")
            if "Guess" in bts:
                log("Found Guess! Let's guess!")
                self.guess()
                time.sleep(2)
                continue
            elif "VisitMain" in bts:
                log("Visiting! This is " + str(self.visits) + " visit!")
                center = get_center("VisitFriend", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft - 200)
                if not self.find_cat_house():
                    time.sleep(1)
                    self.find_cat_house()
                self.visiting()
                time.sleep(1)
                continue
            elif "Replace" in bts:
                log("Found replacement let's wait!")
                # center = get_center("Replace", "Main")
                # click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(5)
                continue
            elif "Gift" in bts:
                log("Need to thank the gift sender!")
                center = get_center("Exit", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                continue
            elif "NoMore" in bts:
                log("This RUN is DONE!! Total " + str(self.visits) + " visits!")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                return
            elif "ToManyRequest" in bts:
                log("Too many requests!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif single_find("PKG"):
                click_at(self.rb.x / self.sft, self.rb.y / self.sft + 100)
                time.sleep(1)
            else:
                self.count += 1
                log("Keep running! This is " + str(self.count) + " clicks")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(4.5)

    def run(self):
        while True:
            bts = find_button("Main")
            if "Guess" in bts:
                log("Found Guess! Let's guess!")
                self.guess()
                time.sleep(2)
                continue
            elif "VisitMain" in bts:
                log("Visiting! This is " + str(self.visits) + " visit!")
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
                log("Found replacement! Take it!")
                center = get_center("Replace", "Main")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                continue
            elif "Gift" in bts:
                log("Need to thank the gift sender!")
                center = get_center("Exit", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
                continue
            elif "NoMore" in bts:
                log("This RUN is DONE!! Total " + str(self.visits) + " visits!")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(1)
                return
            elif "ToManyRequest" in bts:
                log("Too many requests!")
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            else:
                self.count += 1
                log("Keep running! This is " + str(self.count) + " clicks")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(0.5)

    def switch(self, from_s, to_s):
        while simple_single_find(from_s, "Single", 0.5):
            center = get_center(from_s, "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
            try:
                center = get_center(to_s, "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            except:
                log("Switch failed, retry...")
        log("Switched to " + to_s)


if __name__ == '__main__':
    r = MainRun(False, False, False, True)
    r.switch_run()
