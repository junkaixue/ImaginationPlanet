import time

from click import click_at
from common import *

class Fight:
    sft = 0.0
    total = 0

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
        while not self.check_ticket_runout():
            i = 1
            print ("Total: " + str(len(ft)) + " slots")
            for b in ft:
                if self.check_ticket_runout():
                    print("Tickets running out!")
                    return
                print("Fight " + str(i) + " slot")
                click_at(b.x / self.sft, b.y / self.sft)
                time.sleep(10)
                if sk is None:
                    sk = get_center("FightSkip")
                click_at(sk.x / self.sft, sk.y / self.sft)
                time.sleep(2)
                click_at(sk.x / self.sft, sk.y / self.sft)
                time.sleep(4)
                print("Fight " + str(i) + " end, total fight " + str(self.total) + " games.")
                i += 1
                self.total += 1
        print("Tickets running out!")

    def check_ticket_runout(self):
        if "TicketRunout" not in find_button():
            return False
        return True

    def fight(self):
        print ("Go to fight...")
        self.go_to_fight()
        time.sleep(3) # Very slow
        print ("Start fight...")
        self.start_fight()
        self.exit_fight()

    def exit_fight(self):
        print("Exiting fight...")
        if self.check_ticket_runout():
            cc = get_center("CancelBuy")
            click_at(cc.x / self.sft, cc.y / self.sft)
            time.sleep(1)

        while "Exit" in find_button():
            bt = get_center("Exit")
            click_at(bt.x / self.sft, bt.y / self.sft)
            time.sleep(1)
        print("Exited fight...")




if __name__ == "__main__":
    f = Fight()
    f.exit_fight()

