import time

from click import click_at
from common import *

class Fight:
    sft = 0.0

    def __init__(self):
        self.sft = get_scaling_factor()

    def go_to_fight(self):
        while True:
            if "TaskMain" in find_button():
                print("Found Task Main")
                tm = get_center("TaskMain")
                click_at(tm.x / self.sft, tm.y / self.sft)
                time.sleep(2)
                # go to fight main
                fm = get_center("FightMain")
                click_at(fm.x / self.sft, fm.y / self.sft)
                time.sleep(2)
                # go to fight entry
                fe = get_center("FightEntry")
                click_at(fe.x / self.sft, fe.y / self.sft)
                return
            else:
                print("Task Main is not found!")
                time.sleep(1)

    def start_fight(self):
        ft = get_all("FightButton", self.sft)
        sk = None
        total = 0
        while True:
            i = 1
            print ("Total: " + str(len(ft)) + " slots")
            for b in ft:
                print("Fight " + str(i) + " slot")
                click_at(b.x / self.sft, b.y / self.sft)
                time.sleep(10)
                if sk is None:
                    sk = get_center("FightSkip")
                click_at(sk.x / self.sft, sk.y / self.sft)
                time.sleep(2)
                click_at(sk.x / self.sft, sk.y / self.sft)
                time.sleep(4)
                print("Fight " + str(i) + " end, total fight " + str(count) + " games.")
                i += 1
                total += 1




    def fight(self):
        print ("Go to fight...")
        self.go_to_fight()
        time.sleep(3) # Very slow
        print ("Start fight...")
        self.start_fight()


if __name__ == "__main__":
    f = Fight()
    f.start_fight()

