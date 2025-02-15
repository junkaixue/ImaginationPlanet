from click import click_at
from common import *
import time

class BossFight:
    rb = None
    """ Hard code offset due to gift picture keep changing, now only works for windows """
    x_offset = 533 - 656
    y_offset = 1008 - 1209

    def __init__(self, sft = 1):
        if sft == 0:
            self.sft = get_scaling_factor()
        else:
            self.sft = sft
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

    def combo_fight(self):
        self.go_to_fight(0)
        print("Finish world boss fight")
       # self.go_to_fight(1)
        print("Finish group boss fight")

    def go_to_fight(self, fight_type, use_diam = False):
        if fight_type == 0:
            while single_find("TaskMain"):
                center = get_center("TaskMain", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print ("Entered task main")
            while single_find("BossWorld"):
                center = get_center("BossWorld", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print("Entered BossWorld")

            if single_find("VisitBack"):
                center = get_center("VisitBack", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
                print ("Closed result page")

            while single_find("Challenge"):
                center = get_center("Challenge", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print("Entered Boss fight")
        else:
            while single_find("Group"):
                center = get_center("Group", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
                print ("Find group main")

            while single_find("GBossMain"):
                try:
                    center = get_center("BossGroup", "Single")
                    click_at(center.x / self.sft, center.y / self.sft - 50)
                    time.sleep(2)
                except:
                    print("Try to click group boss but too many fliers")
            print ("Find group boss")

            while single_find("Challenge"):
                center = get_center("Challenge", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
                print ("Find challenge button")
        print ("Start fight!")
        self.fight(use_diam)
        self.collect_gift()
        self.exit_fight(fight_type)

    def exit_fight(self, fight_type):
        if fight_type == 0:
            while single_find("BossEnd"):
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(2)

            while single_find("WGoHome"):
                center = get_center("WGoHome", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print("Click go home")
        else:
            while single_find("BossEnd"):
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(2)
            print ("Finish fight!")
            while single_find("GoHome"):
                center = get_center("GoHome", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print ("Click go home")
            while single_find("Challenge"):
                try:
                    center = get_center("Exit", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(3)
                except:
                    print ("Some ads flying!")
            print ("Close the boss site")
            while single_find("BossBack"):
                center = get_center("BossBack", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print ("Exited to the main entry")


    def fight(self, use_diam = False):
        while not simple_single_find("BossEnd", "Single", 0.8):
            if use_diam and simple_single_find("BossDiam", "Single", 0.8):
                center = get_center("BossDiam", "Single")
                click_at(center.x / self.sft, center.y / self.sft + 50)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(2)
                print ("Use Diamond to fight boss")
            elif simple_single_find("BossFree", "Single", 0.8):
                center = get_center("BossFree", "Single")
                click_at(center.x / self.sft, center.y / self.sft + 50)
                time.sleep(1)
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(2)
                print("Use free hit to fight boss")
            else:
                click_at(self.rb.x / self.sft, self.rb.y / self.sft)
                time.sleep(2)

    def collect_gift(self):
        collects = 0
        while collects < 25:
            click_at(self.rb.x + self.x_offset / self.sft, self.rb.y + self.y_offset / self.sft)
            time.sleep(2)
            collects += 1
            print("Collect gift: " + str(collects) + "times")

if __name__ == '__main__':
    b = BossFight(1)
    b.go_to_fight(1)

