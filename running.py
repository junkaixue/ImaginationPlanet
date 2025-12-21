import time
import platform

from sympy import false

from click import *
from common import *
from smart_card_grab import SmartCardGrab
from log_helper import log
from config_coords import ConfigCoords


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
    current_mode = None  # Track current mode: "ONEB" or "TWB"
    visit_roll_count = 0  # Count rolls within each visit
    again_card_used = False  # Track if AgainCard was used in current visit
    friend_index = 0  # Track current friend slot for rotation (0-15)

    def __init__(self, skip_cat_grab, go_home, semi_auto=False, is_switch=False, is_niu=False):
        self.semi_auto = semi_auto
        self.go_home = go_home
        self.consecutive_clicks = 0
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
        
        # Update platform-specific config file with run button coordinate
        rb_x_logical = self.rb.x / self.sft
        rb_y_logical = self.rb.y / self.sft
        ConfigCoords.update_run_button_in_config(rb_x_logical, rb_y_logical)

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
        # Disable grab cat
        # if not self.sc:
        #     self.grab_cat()

        while not single_find("VisitGoHome"):
            log("Visit Go Home was not found! Sleep for 1 second")
            if simple_single_find("DingHao", "Single", 0.7):
                # Guosha ding le
                log("Guo sha ding le.... Sleep 10 mins")
                time.sleep(10 * 60)
                self.restart_game()
                continue
            time.sleep(1)

        log("Visit Go home found! In visiting main mode now!")

        if self.go_home or self.is_niu or (self.current_mode == "ONEB" and not simple_single_find("33", "Single", 0.7)):
            log("Going home!")
            
            # Click go home and confirm until we return to main page
            while simple_single_find("VisitGoHome", "Single", 0.8):
                if simple_single_find("DingHao", "Single", 0.7):
                    # Guosha ding le
                    log("Guo sha ding le.... Sleep 10 mins")
                    time.sleep(10 * 60)
                    self.restart_game()
                    return

                try:
                    center = get_center("VisitGoHome", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    log("Clicked go home!")
                    time.sleep(2)
                    
                    # Use config coordinate for go home confirm
                    gohome_confirm_coords = self.smart_grab.config.get_coord("gohome_confirm")
                    if gohome_confirm_coords:
                        click_at(gohome_confirm_coords[0], gohome_confirm_coords[1])
                        log(f"Clicked go home confirm at ({gohome_confirm_coords[0]:.1f}, {gohome_confirm_coords[1]:.1f})")
                    else:
                        log("ERROR: gohome_confirm coordinates not found in config!")
                    time.sleep(2)
                except:
                    log("Super slow in loading animation")
                    time.sleep(1)
            if not simple_single_find("VisitComplete", "Visit", 0.8):
                log("Go home completed - returned to main page")
                # If ONEB mode, reset friend_index back (since we're going home, not visiting)
                self.friend_index = self.friend_index - 1
                log(f"ONEB mode - friend slot reset back to #{self.friend_index}")
                return
        log("In visiting mode!")
        self.visits += 1

        # Reset roll counter and AgainCard flag for this visit
        self.visit_roll_count = 0
        self.again_card_used = False
        
        for i in range(1, 2000):

            if simple_single_find("DingHao", "Single", 0.7):
                # Guosha ding le
                log("Guo sha ding le.... Sleep 10 mins")
                time.sleep(10 * 60)
                self.restart_game()
                return

            # Check for duplicate visit before each roll (only after 30 rolls, not in ONEB mode, and AgainCard not used yet)
            if not self.sc  and not self.again_card_used and not self.again_card_used and self.visit_roll_count > 30:
                if self.current_mode == "ONEB":
                    # In ONEB mode, skip smart card grab
                    pass
                else:
                    try:
                        if self.smart_grab._check_face_in_any_box():
                            log(f"🎯 Duplicate visit detected after {self.visit_roll_count} rolls, triggering smart card grab!")
                            grab_result = self.smart_grab.smart_grab_cat()
                            if grab_result:
                                log("✅ Successfully used AgainCard!")
                                self.again_card_used = True  # Mark as used
                                log("AgainCard used, continuing with new visit...")
                                # Don't return - continue the visit with the new island
                            # If grab failed, just continue - next loop iteration will handle VisitComplete if present
                    except Exception as e:
                        log(f"Smart grab check failed: {e}")
                        # Continue loop - VisitComplete will be handled in the next iteration

            if single_find("RollComplete") and not self.is_mac:
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
                self.visit_roll_count += 1
                log(f"Found Rolling! (Visit #{self.visits}, Roll #{self.visit_roll_count})")
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

                # else:
                #     center = get_center("Roll", "Visit")
                #     click_at(center.x / self.sft, center.y / self.sft)
                #     time.sleep(1)
                #     while single_find("HConfirm"):
                #         click_at(center.x / self.sft, center.y / self.sft)
                log("Complete Rolling!")
            elif "VisitComplete" in btl:
                log(f"Complete visiting! (Visit #{self.visits}, Total rolls: {self.visit_roll_count})")
                
                # While loop to ensure complete is gone
                while simple_single_find("VisitComplete", "Visit", 0.8):
                    if simple_single_find("VisitBack", "Single", 0.8):
                        cc = get_center("VisitBack", "Single")
                        click_at(cc.x / self.sft, cc.y / self.sft)
                        log("Clicked VisitBack to clear complete")
                        time.sleep(1)
                    else:
                        time.sleep(1)
                
                log("VisitComplete is gone, continuing...")
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
                self.visit_roll_count += 1
                log(f"Keep visiting! (Visit #{self.visits}, Roll #{self.visit_roll_count})")
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                # Slow down after 30 rolls to let game catch up
                if not self.again_card_used and self.visit_roll_count > 30:
                    time.sleep(3)
                    log(f"⏱️ Extended wait (roll #{self.visit_roll_count} > 30)")
                else:
                    time.sleep(1)

    def find_cat_house(self):
        """Find and click cat house with friend rotation logic."""
        cat_house_coords = self.smart_grab.config.get_coord("cat_house")
        if not cat_house_coords:
            log("ERROR: cat_house coordinate not found in config!")
            return False

        retry = 3
        while not single_find("VisitGoHome") and retry > 0:
            log(f"Attempting to find cat house (retry {4 - retry}/3)")
            
            # Scroll to top first
            scroll_up = 500 if self.is_mac else 10
            pyautogui.vscroll(scroll_up)
            log("Scrolled to top of friend list")
            time.sleep(1)

            # Calculate target slot based on friend index (0-15)
            target_slot = self.friend_index % 16
            scroll_per_slot = -70 if not self.is_mac else -100
            
            log(f"Visiting friend slot #{target_slot} (total visit #{self.visits})")
            
            # Scroll incrementally, one slot at a time with 1 second delay
            for slot in range(target_slot):
                pyautogui.vscroll(scroll_per_slot)
                log(f"Scrolled to slot {slot + 1}/{target_slot}")
                time.sleep(1)
            
            # Click cat house at the calculated position
            log("Clicking cat house using relative coordinates")
            click_at(cat_house_coords[0], cat_house_coords[1])
            time.sleep(1)

            # Check if we're in visiting page
            if single_find("VisitGoHome"):
                log("✅ Successfully entered visiting page!")
                break
            else:
                log("⚠️ Not in visiting main page, retrying...")
                retry -= 1
                time.sleep(2)
        
        if retry <= 0:
            log("❌ Failed to find cat house after 3 retries!")
            return False
        
        # Increment friend index for next visit (rotate through 0-15)
        self.friend_index = (self.friend_index + 1) % 16
        log(f"Next visit will use friend slot #{self.friend_index}")
        
        return True

    def map_repair(self):
        """Repair map items by using tickets."""
        # Step 1: Check if repair signal exists
        if not single_find("Repair"):
            log("No repair signal found, skipping repair")
            return False
        
        log("🔧 Repair signal detected!")
        
        # Step 2: Click repair entry button using config coordinates
        repair_entry_coords = self.smart_grab.config.get_coord("repair_entry")
        if not repair_entry_coords:
            log("ERROR: repair_entry coordinates not found in config!")
            return False
        
        click_at(repair_entry_coords[0], repair_entry_coords[1])
        log(f"Clicked repair entry at ({repair_entry_coords[0]:.1f}, {repair_entry_coords[1]:.1f})")
        time.sleep(1)
        
        # Step 3-6: While loop to repair items
        repair_count = 0
        while single_find("RepairTop"):
            repair_count += 1
            log(f"🔨 Repairing item #{repair_count}...")
            
            # Step 4: Click repair_top from config
            repair_top_coords = self.smart_grab.config.get_coord("repair_top")
            if not repair_top_coords:
                log("ERROR: repair_top coordinates not found in config!")
                break
            
            click_at(repair_top_coords[0], repair_top_coords[1])
            log(f"Clicked repair_top at ({repair_top_coords[0]:.1f}, {repair_top_coords[1]:.1f})")
            time.sleep(2)
            
            # Step 5: Click use_ticket using single_find
            while single_find("UseTicket"):
                try:
                    center = get_center("UseTicket", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    log("Clicked UseTicket button")
                except Exception as e:
                    log(f"Failed to click UseTicket: {e}")
                    break
                time.sleep(1)
        
        # Step 7: Nothing left, completed
        log(f"✅ Map repair completed! Repaired {repair_count} items")
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
                self.consecutive_clicks = 0
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
            # elif "RobotDetect" in bts:
            #     log("Robot detected!")
            #     # RobotCheck disabled
            #     time.sleep(1)
            #     click_at(self.rb.x / self.sft, self.rb.y / self.sft)
            #     time.sleep(1)
            #     self.long_click()
            #     time.sleep(1)
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
            # Debug: Check what's on screen
            face_detected = simple_single_find("FACE_UP_LEFT", "Single", 0.45) and self.smart_grab.check_run_face_in_box()
            twb_bar_detected = simple_single_find("TW", "Single", 0.7)
            oneb_bar_detected = simple_single_find("ONE", "Single", 0.7)
            if self.current_mode is None:
                if oneb_bar_detected:
                    self.current_mode = "ONEB"
                else:
                    self.current_mode = "TWB"
            
            log(f"🔍 Detection: FACE={face_detected}, TWB_bar={twb_bar_detected}, ONEB_bar={oneb_bar_detected}, mode={self.current_mode}")
            
            # Simple idempotent checks:
            # 1. If FACE detected, switch to TWB
            # 2. Else, if not in ONEB, switch to ONEB
            if face_detected:
                if oneb_bar_detected:
                    log("🔄 Switching to TWB mode")
                    self.current_mode = "TWB"
                    self.switch("ONE", "TWB")
            else:
                if twb_bar_detected:
                    log("🔄 Switching to ONEB mode (smart grab disabled)")
                    self.current_mode = "ONEB"
                    self.switch("TW", "ONEB")

            # Check for map repair before other actions
            self.map_repair()

            if simple_single_find("DingHao", "Single", 0.7):
                # Guosha ding le
                log("Guo sha ding le.... Sleep 10 mins")
                time.sleep(10 * 60)
                self.restart_game()
                continue

            bts = find_button("Main")
            if "Guess" in bts:
                log("Found Guess! Let's guess!")
                self.guess()
                time.sleep(2)
                continue
            elif "VisitMain" in bts:
                self.consecutive_clicks = 0
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
                self.consecutive_clicks += 1
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                log("Keep running! This is " + str(self.count) + " clicks, " + str(self.consecutive_clicks) + " consecutive clicks")
                if self.consecutive_clicks > 100:
                    log(f"Consecutive clicks exceeded 100 ({self.consecutive_clicks}), restarting game...")
                    self.consecutive_clicks = 0
                    self.restart_game()
                    continue
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
                self.consecutive_clicks = 0
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
                self.consecutive_clicks += 1
                if self.consecutive_clicks > 100:
                    log(f"Consecutive clicks exceeded 100 ({self.consecutive_clicks}), restarting game...")
                    self.consecutive_clicks = 0
                    self.restart_game()
                    continue
                time.sleep(0.5)

    def switch(self, from_s, to_s):
        while simple_single_find(from_s, "Single", 0.7):
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

    def refresh_run_button_and_coords(self, retry=30):
        found_rb = False
        while not found_rb and retry > 0:
            try:
                self.rb = get_center("RunButton", "Main")
                found_rb = True
            except:
                retry -= 1
                log(f"Run Button was not found during refresh! retries left: {retry}")
                time.sleep(1)

        if not found_rb:
            log("ERROR: Failed to refresh Run Button")
            return False

        if self.is_mac:
            self.sft = 1
        else:
            self.sft = get_scaling_factor()

        rb_x_logical = self.rb.x / self.sft
        rb_y_logical = self.rb.y / self.sft
        ConfigCoords.update_run_button_in_config(rb_x_logical, rb_y_logical)

        try:
            coor_dict.clear()
        except:
            pass
        try:
            but_list.clear()
        except:
            pass

        try:
            self.smart_grab.sft = self.sft
            self.smart_grab.rb = self.rb
            self.smart_grab.config = ConfigCoords(mock_rb=(int(self.rb.x), int(self.rb.y)))
        except Exception as e:
            log(f"ERROR: Failed to refresh smart_grab config: {e}")
            self.smart_grab = SmartCardGrab(sft=self.sft, rb=self.rb)

        log(f"Refresh complete. Run Button at ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
        return True

    def restart_game(self):
        while not self.restart_games():
            log("Game restart failed, retrying...")
            time.sleep(5)
        


    def restart_games(self):
        start_time = time.time()
        timeout = 5 * 60
        close_name = self.smart_grab.config.get_coord("close_game")
        close_announce = self.smart_grab.config.get_coord("close_announce")
        main_game = self.smart_grab.config.get_coord("main_game")
        start_game = self.smart_grab.config.get_coord("start_game")
        setup = self.smart_grab.config.get_coord("setup")
        setup_confirm = self.smart_grab.config.get_coord("setup_confirm")

        while simple_single_find("DingHao", "Single", 0.7):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            try:
                location = pyautogui.locateOnScreen(resource_map["Single"]["CloseTab"], confidence=0.7)
                if location is not None:
                    click_x = (location.left + (location.width - 5)) / self.sft
                    click_y = (location.top + (location.height / 2)) / self.sft
                    click_at(click_x, click_y)
                else:
                    click_at(close_name[0], close_name[1])
            except:
                click_at(close_name[0], close_name[1])

            time.sleep(2)
            log("Closing the game.....")

        log("Game closed!")

        while not single_find("ClickGame"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            log("Waiting for game button shows up....")
            time.sleep(2)

        log("Game button shows up now!")

        while single_find("ClickGame"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            click_at(main_game[0], main_game[1])
            time.sleep(2)
            log("Game button clicked!")

        log("Game button clicked!")

        while not single_find("Announcement"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            log("Waiting for announcement shows up....")
            time.sleep(2)

        log("Announcement shows up now!")

        while single_find("Announcement"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            click_at(close_announce[0], close_announce[1])
            time.sleep(2)
            log("Announcement clicked!")

        log("Announcement clicked!")

        while not single_find("StartGame"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            log("Waiting for game button shows up....")
            time.sleep(2)

        log("Game button shows up now!")

        while not single_find("StartGame"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            log("Waiting starting game shows up....")
            time.sleep(2)

        log("Start game shows up!")

        while single_find("StartGame"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            click_at(start_game[0], start_game[1])
            time.sleep(2)
            log("Start game clicking!")

        while not single_find("RunButton"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            click_at(self.rb.x / self.sft, self.rb.y / self.sft)
            time.sleep(1)
            log("Waiting for main page and click empty place to close ads")

        while not single_find("AutoPick"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            log("Clicking auto configs....")
            click_at(setup[0], setup[1])
            time.sleep(2)

        log("Auto configs clicked!")

        while single_find("AutoPick"):
            if time.time() - start_time > timeout:
                log("Game restart timeout!")
                return False
            log("Auto configs starts...")
            click_at(setup_confirm[0], setup_confirm[1])
            time.sleep(2)

        log("Auto configs started! Everything is done! Continue!")
        self.refresh_run_button_and_coords()
        self.consecutive_clicks = 0
        time.sleep(2)
        return True


if __name__ == '__main__':
    r = MainRun(False, False, False, True)
    r.friend_index = 2
    r.restart_game()
