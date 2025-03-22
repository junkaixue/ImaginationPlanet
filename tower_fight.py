from common import *


class TowerFight:
    entry_center = None

    def __init__(self, sft=0, debug=False):
        if sft == 0:
            self.sft = get_scaling_factor()
        else:
            self.sft = sft
        if debug:
            return

        while single_find("TEntry") and self.entry_center is None:
            try:
                self.entry_center = get_center("TEntry", "Single")
            except:
                print("Failed to get center of entry")

    def find_cat_house(self):
        found = False
        page = 0
        while not found:
            if single_find("TClick"):
                center = get_center("TClick", "Single")
                click_at(center.x / self.sft, center.y / self.sft + 200)
                print("Click for scrolling")
                time.sleep(1)
            scroll = 5
            while scroll > 0:
                if not single_find("TSN"):
                    pyautogui.vscroll(-100)
                    scroll -= 1
                    continue
                else:
                    found = True
                    print("Found shanniu")
                    break
            if not found and single_find("TNext"):
                center = get_center("TNext", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                print("Go to page " + str(page))
                page += 1
                time.sleep(1)
            if page > 6:
                while single_find("TExit"):
                    center = get_center("TExit", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(1)
                    print("Failed to find shanniu")
                return
        while single_find("TSN"):
            try:
                lc = pyautogui.locateOnScreen(single_find_map["TSN"], confidence=0.9)
                lr = pyautogui.locateOnScreen(single_find_map["TFight"], confidence=0.9)
                # print(f"Image found at: {center.y}")
                click_at(((lr.left + lr.width / 2) / self.sft), ((lc.top + lc.height) / self.sft))
                print("Clicked Shanliu at " + str((lr.left + lr.width / 2) / self.sft) + "," + str(
                    (lc.top + lc.height) / self.sft))
                time.sleep(2)

                while single_find("TTicket"):
                    print("Need to buy tickets")
                    try:
                        center = get_center("TConfirm", "Single")
                        click_at(center.x / self.sft, center.y / self.sft)
                        time.sleep(2)
                    except:
                        print("Failed to buy tickets")

                while single_find("TBuy"):
                    click_at(self.entry_center.x / self.sft, self.entry_center.y / self.sft + 300)
                    time.sleep(2)
                    print("Click ticket buy complete")

            except:
                print("Cat house already clicked")

    def single_fight(self):
        while not single_find("TClick"):
            click_at(self.entry_center.x / self.sft, self.entry_center.y / self.sft)
            time.sleep(2)
            print("Click entry...")
        self.find_cat_house()
        while not single_find("TComplete"):
            time.sleep(2)
            print("Waiting for completion...")
        while single_find("TComplete"):
            click_at(self.entry_center.x / self.sft, self.entry_center.y / self.sft + 300)
            time.sleep(2)
            print("Click complete")

    def fight(self):
        while True:
            self.single_fight()


if __name__ == '__main__':
    t = TowerFight()
    t.fight()
