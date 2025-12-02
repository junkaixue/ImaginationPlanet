import time
import argparse

from common import *
from config_coords import ConfigCoords


class BossFight:
    rb = None
    """ Hard code offset due to gift picture keep changing, cross-platform compatible """
    x_offset = 533 - 656
    y_offset = 1008 - 1209

    def __init__(self, sft=1, use_config_diamond=False):
        if sft == 0:
            self.sft = get_scaling_factor()
        else:
            self.sft = sft
        
        self.use_config_diamond = use_config_diamond
        self.config_coords = None
        
        # Load config coordinates if using diamond from config
        if use_config_diamond:
            self.config_coords = ConfigCoords()
        
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

    def go_to_fight(self, fight_type, use_diam=False):
        if fight_type == 0:
            while single_find("TaskMain"):
                center = get_center("TaskMain", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print("Entered task main")
            while single_find("BossWorld"):
                center = get_center("BossWorld", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print("Entered BossWorld")

            if single_find("VisitBack"):
                center = get_center("VisitBack", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
                print("Closed result page")

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
                print("Find group main")

            while single_find("GBossMain"):
                try:
                    center = get_center("BossGroup", "Single")
                    click_at(center.x / self.sft, center.y / self.sft - 50)
                    time.sleep(2)
                except:
                    print("Try to click group boss but too many fliers")
            print("Find group boss")

            while single_find("Challenge"):
                center = get_center("Challenge", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
                print("Find challenge button")
        print("Start fight!")
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
            print("Finish fight!")
            while single_find("GoHome"):
                center = get_center("GoHome", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print("Click go home")
            while single_find("Challenge"):
                try:
                    center = get_center("Exit", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(3)
                except:
                    print("Some ads flying!")
            print("Close the boss site")
            while single_find("BossBack"):
                center = get_center("BossBack", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(3)
            print("Exited to the main entry")

    def fight(self, use_diam=False):
        while not simple_single_find("BossEnd", "Single", 0.8):
            if use_diam and simple_single_find("BossDiam", "Single", 0.8):
                # Use relative coordinate from config if enabled, otherwise use default behavior
                if self.use_config_diamond and self.config_coords:
                    coords = self.config_coords.get_coord("use_diamond")
                    if coords:
                        click_at(coords[0], coords[1])
                        time.sleep(1)
                        print("Use high Diamond to fight boss (from config)")
                    else:
                        # Fallback to old behavior if config coord not found
                        center = get_center("BossDiam", "Single")
                        click_at(center.x / self.sft, center.y / self.sft + 50)
                        time.sleep(1)
                        click_at(center.x / self.sft, center.y / self.sft)
                        time.sleep(2)
                        print("Use Diamond to fight boss (fallback)")
                else:
                    # Default behavior - use default ticket
                    center = get_center("BossDiam", "Single")
                    click_at(center.x / self.sft, center.y / self.sft + 50)
                    time.sleep(1)
                    click_at(center.x / self.sft, center.y / self.sft)
                    time.sleep(2)
                    print("Use default ticket to fight boss")
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Boss Fight automation')
    parser.add_argument('-d', '--diamond', action='store_true',
                        help='Use high diamond with relative coordinates from config file')
    args = parser.parse_args()
    
    # Create BossFight instance with diamond config option
    b = BossFight(1, use_config_diamond=args.diamond)
    
    if args.diamond:
        print("Running boss fight with HIGH DIAMOND from config")
    else:
        print("Running boss fight with DEFAULT TICKET")
    
    # Run world boss fight (fight_type=0)
    b.go_to_fight(0, use_diam=args.diamond)
