import time
from collections import namedtuple

import pyautogui

from common import *
from robot_check import RobotCheck

Point = namedtuple('Point', ['x', 'y'])


class StarPick:
    ships = {"Ship1": 0, "Ship2": 1, "Ship3": 2, "Ship4": 3}
    ships_list = ["Ship1", "Ship2", "Ship3", "Ship4"]
    verify_list = ["S1V", "S2V", "S3V", "S4V"]
    visiting = {}
    visit_ship = {}
    ship_coo = []
    send_coo = []
    free = set()
    click_point = None
    click_start = None
    click_end = None
    offset_unit = 65
    scan_unit = 12
    rounds = 0
    bottom_line = 0
    top_line = 0
    fails = 0
    rb = None
    refresh_time = 0
    refresh_period = 1200

    def __init__(self, sft=0, debug=False):

        if sft == 0:
            self.sft = get_scaling_factor()
        else:
            self.sft = sft
        if debug:
            return
        completed = False
        while not completed:
            try:
                loc = pyautogui.locateOnScreen(single_find_map["Shop"])
                self.click_point = Point((loc.left + loc.width) / self.sft, (loc.top - 20) / self.sft)
                self.click_start = Point(loc.left / self.sft, (loc.top - 20) / self.sft)
                loc = pyautogui.locateOnScreen(single_find_map["SChat"])
                print("Found Click")
                self.bottom_line = (loc.top + loc.height) / self.sft + 50
                print("Found bottom line")
                self.top_line = self.click_point.y - 200
                print("BT : " + str(self.bottom_line))
                print("TO : " + str(self.top_line))
                completed = True
            except:
                print("Cannot find click point")
        self.refresh_time = time.time()

    def get_send_coo(self):
        sp_cc = []
        while len(sp_cc) != 4:
            try:
                sp_cc = get_all("Details", "Single")
            except:
                time.sleep(2)
                print("No found for 4 ships!")
        for scc in sp_cc:
            self.send_coo.append(Point(scc.x - 200, scc.y))

    def scroll_left_right(self, n):
        pyautogui.moveTo(self.click_point.x, self.click_point.y)
        pyautogui.mouseDown()
        pyautogui.move(n * self.offset_unit, 0)
        pyautogui.mouseUp()

    def scroll_start(self, n):
        pyautogui.mouseDown()
        pyautogui.move(n * self.offset_unit, 0)
        pyautogui.mouseUp()

    def scroll_down(self, n):
        pyautogui.moveTo(self.click_point.x, self.click_point.y)
        pyautogui.scroll(n * self.offset_unit)

    def single_round_scan(self):
        if single_find("Disconnected"):
            print("Find disconnected")
            center = get_center("Disconnected", "Single")
            click_at(center.x / self.sft, center.y / self.sft + 200)
            time.sleep(1)

        if not self.count_free_ship():
            print("Failed to find free ships!")
            return False

        if len(self.free) == 0:
            print("No free ships!")
            return True
        # find left top
        pyautogui.moveTo(self.click_start.x / self.sft, self.click_start.y / self.sft)
        for i in range(0, 10):
            pyautogui.vscroll(200)
        for i in range(0, 5):
            pyautogui.moveTo(self.click_start.x / self.sft, self.click_start.y / self.sft)
            self.scroll_start(6)
            time.sleep(1)

        print("Get top left corner, start scan")
        block_index = 0
        for i in range(0, 3):
            for j in range(0, 4):
                if len(self.free) == 0:
                    return True

                if single_find("RobotDetected"):
                    if self.rb is None:
                        self.rb = RobotCheck(self.sft)
                    self.rb.break_check()
                    time.sleep(1)
                click_at(self.click_start.x / self.sft, self.click_start.y / self.sft)
                self.find_in_single_block(block_index)
                block_index += 1
                self.scroll_left_right(-11)
            self.scroll_down(-7)
            # scroll to left
            for i in range(0, 8):
                pyautogui.moveTo(self.click_start.x / self.sft, self.click_start.y / self.sft)
                self.scroll_start(6)
                time.sleep(1)
        return True

    def find_in_single_block(self, block_index):
        if block_index not in self.visiting.keys():
            self.visiting[block_index] = {}
        try:
            stars = get_all("Star", "Single")
        except:
            print("No stars in this area for block: " + str(block_index))
            return
        for star in stars:
            print(str(star.x) + "," + str(star.y))

        if len(stars) == 0:
            return

        to_assign = min(len(stars), len(self.free))
        if to_assign > 0:
            print("To set to center position")
            reset_index = 0
            while reset_index < to_assign:
                if stars[reset_index].y / self.sft <= self.bottom_line or stars[
                    reset_index].y / self.sft >= self.top_line:
                    reset_index += 1
                    continue
                else:
                    break
            if reset_index == to_assign:
                print("no valid point")
                return
            click_at(stars[reset_index].x / self.sft, stars[reset_index].y / self.sft)
            time.sleep(2)
            click_at(self.click_point.x / self.sft, self.click_point.y / self.sft)
            time.sleep(2)
            try:
                stars = get_all("Star", "Single")
            except:
                print("No stars in this area for block: " + str(block_index))
                return

        nstars = []
        for star in stars:
            if star.y / self.sft <= self.bottom_line or star.y / self.sft >= self.top_line or (
                    round(star.x / 100) * 100 + round(star.y / 100)) in self.visiting[block_index].keys():
                continue
            nstars.append(star)
        stars = nstars
        to_assign = min(len(stars), len(self.free))

        print("Total: " + str(len(stars)) + " stars")
        for i in range(to_assign):
            picks = 5
            while not single_find("StarPick") and picks > 0:
                print("Picking star...")
                picks -= 1
                click_at(stars[i].x / self.sft, stars[i].y / self.sft)
                time.sleep(2)
            if picks == 0:
                print("Failed to pick star")
                return
            picks = 5
            while single_find("StarPick") and picks > 0 and not single_find("SendShip"):
                print("Click star at: (" + str(stars[i].x / self.sft) + "," + str(stars[i].y / self.sft) + ")")
                center = get_center("StarPick", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(2)
                picks -= 1
            if picks == 0:
                print("Failed to click star")
                return
            if len(self.send_coo) == 0:
                print("Get send coo")
                self.get_send_coo()
            time.sleep(2)
            ship = self.free.pop()
            index = self.ships[ship]
            while single_find("Details"):
                click_at(self.send_coo[index].x / self.sft, self.send_coo[index].y / self.sft)
                print("Send ship " + ship)
                time.sleep(2)
            if single_find("SConfirm"):
                print("Need to buy tickets")
                while single_find("SConfirm"):
                    print("Click Confirm buying tickets")
                    try:
                        loc = pyautogui.locateOnScreen(single_find_map["SConfirm"])
                        click_at((loc.left + loc.width * 0.75) / self.sft, (loc.top + loc.height + 40) / self.sft)
                        time.sleep(1)
                    except:
                        print("Failed to locate confirm")
                print("Brought 4 tickets, no tickets")
                click_at(self.click_point.x / self.sft, self.click_point.y / self.sft)
                picks = 5
                while not single_find("StarPick") and picks > 0:
                    print("Picking star...")
                    picks -= 1
                    click_at(stars[i].x / self.sft, stars[i].y / self.sft)
                    time.sleep(1)
                if picks == 0:
                    print("Failed to pick star")
                    return
                print("Click star at: (" + str(stars[i].x / self.sft) + "," + str(stars[i].y / self.sft) + ")")
                center = get_center("StarPick", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(2)
                while single_find("PPT"):
                    click_at(self.click_point.x / self.sft, self.click_point.y / self.sft)
                    time.sleep(1)
                    print("Found property, click point")
                while single_find("Details"):
                    click_at(self.send_coo[index].x / self.sft, self.send_coo[index].y / self.sft)
                    time.sleep(2)
            print("Send ship " + ship + " with block index " + str(block_index) + " coords " + str(
                round(stars[i].x / 100) * 100 + round(stars[i].y / 100)))
            self.visiting[block_index][round(stars[i].x / 100) * 100 + round(stars[i].y / 100)] = ship
            self.visit_ship[ship] = block_index

    def count_free_ship(self):
        self.free = set()
        tries = 10
        while not single_find("ShipList") and tries > 0:
            time.sleep(2)
            print("Not find ship list button")
            tries -= 1
        if tries == 0:
            return False
        tries = 10
        while not single_find("ShipPage") and tries > 0:
            center = get_center("ShipList", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
            print("Clicked the ship list")
            tries -= 1
        if tries == 0:
            return False

        if len(self.ship_coo) == 0:
            c1 = get_center("Ship1", "Single")
            c2 = get_center("Ship2", "Single")
            offset = c2.x - c1.x
            self.ship_coo.append(Point(c1.x, c1.y))
            self.ship_coo.append(Point(c2.x, c2.y))
            self.ship_coo.append(Point(c2.x + offset, c2.y))
            self.ship_coo.append(Point(c2.x + 2 * offset, c1.y))

        for i in range(0, len(self.ship_coo)):
            ship = self.ships_list[i]
            print("Click ship " + ship + " with verify " + self.verify_list[i])
            click_at(self.ship_coo[i].x / self.sft, self.ship_coo[i].y / self.sft)
            time.sleep(1)
            tries = 5
            while not single_find(self.verify_list[i]) and tries > 0:
                print("Click at " + str(self.ship_coo[i].x / self.sft) + "," + str(self.ship_coo[i].y / self.sft))
                click_at(self.ship_coo[i].x / self.sft, self.ship_coo[i].y / self.sft)
                time.sleep(1)
                tries -= 1

            if tries == 0:
                return False
            print("Check ship: " + ship)
            if single_find("ShipFree"):
                print("Ship " + ship + " is free")
                self.free.add(ship)
                if ship in self.visit_ship.keys():
                    print("Block index: " + str(self.visit_ship[ship]))
                    indx = -1
                    for index in self.visiting[self.visit_ship[ship]].keys():
                        if self.visiting[self.visit_ship[ship]][index] == ship:
                            indx = index
                            break
                    if indx != -1:
                        self.visiting[self.visit_ship[ship]].pop(indx)
                        self.visit_ship.pop(ship)
                        print("Ship " + ship + " is back. Remove from list.")
        print("Total free ships: " + ",".join(self.free))

        tries = 5
        while single_find("ShipPage") and tries > 0:
            center = get_center("CloseList", "Single")
            click_at(center.x / self.sft, center.y / self.sft + 20)
            time.sleep(1)
            print("Closed the ship list")
            tries -= 1
        if tries == 0:
            return False
        return True

    def reenter(self):
        picks = 5
        while single_find("SBack") and picks > 0:
            center = get_center("SBack", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            print("Clicking go back button")
            picks -= 1
            time.sleep(2)

        if picks == 0:
            print("Failed to reenter")

        picks = 5
        while single_find("Exit") and picks > 0:
            center = get_center("Exit", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            print("Clicking go exit button")
            picks -= 1
            time.sleep(2)

        if picks == 0:
            print("Failed to reenter")

        picks = 5
        while single_find("SEntry") and picks > 0:
            center = get_center("SEntry", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            print("Clicking click entry button")
            picks -= 1
            time.sleep(2)
        if picks == 0:
            print("Failed to reenter")
        self.refresh_time = time.time()

        # picks = 5
        # while not single_find("75V") and picks > 0:
        #     center = get_center("75", "Single")
        #     click_at(center.x / self.sft, center.y / self.sft)
        #     print("Clicking click 75% button")
        #     picks -= 1
        #     time.sleep(2)

    def pick_up(self):
        time_wait = 2 * 60
        while True:
            if single_find("RobotDetected"):
                if self.rb is None:
                    self.rb = RobotCheck(self.sft)
                self.rb.break_check()
                time.sleep(1)
            click_at(self.click_start.x / self.sft, self.click_start.y / self.sft)
            self.rounds += 1
            if time.time() >= self.refresh_time + self.refresh_period or self.fails >= 5:
                try:
                    self.reenter()
                except:
                    print("Failed to reenter")
                    time.sleep(10)
            print("This is round " + str(self.rounds))
            if not self.single_round_scan():
                self.fails += 1
            else:
                self.fails = 0
            print("Finish round" + str(self.rounds) + ". Now sleep for " + str(time_wait) + " seconds")
            time.sleep(time_wait)


if __name__ == "__main__":
    s = StarPick()
    s.pick_up()
