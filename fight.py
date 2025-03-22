from common import *


class Fight:
    sft = 0.0
    total = 0
    map_scope = "Single"

    def __init__(self):
        self.sft = get_scaling_factor()

    def go_to_fight(self):
        while single_find("TaskMain"):
            print("Found Task Main")
            tm = get_center("TaskMain", self.map_scope)
            click_at(tm.x / self.sft, tm.y / self.sft)
            time.sleep(2)
            while single_find("FightMain"):
                # go to fight main
                fm = get_center("FightMain", self.map_scope)
                click_at(fm.x / self.sft, fm.y / self.sft)
                time.sleep(2)
                while single_find("FightEntry"):
                    try:
                        fe = get_center("FightEntry", self.map_scope)
                        click_at(fe.x / self.sft, fe.y / self.sft)
                    except:
                        continue

    def start_fight(self):
        sk = None
        while not self.check_ticket_runout():
            i = 1
            while not single_find("FightButton"):
                if single_find("FightEntry"):
                    center = get_center("FightEntry", "Single")
                    click_at(center.x / self.sft, center.y / self.sft)
                    print("Find fight entry and clicked it.")
                time.sleep(2)
                print("Button not found")
            ft = get_all("FightButton", "Fight")
            print("Total: " + str(len(ft)) + " slots")
            for b in ft:
                if self.check_ticket_runout():
                    print("Tickets running out!")
                    return
                print("Fight " + str(i) + " slot")
                click_at(b.x / self.sft, b.y / self.sft)
                time.sleep(12)
                if sk is None:
                    while not single_find("FightSkip"):
                        print("Skip button is not found!")
                        time.sleep(2)
                    sk = get_center("FightSkip", self.map_scope)
                click_at(sk.x / self.sft, sk.y / self.sft)
                time.sleep(2)
                click_at(sk.x / self.sft, sk.y / self.sft)
                time.sleep(4)
                print("Fight " + str(i) + " end, total fight " + str(self.total) + " games.")
                i += 1
                self.total += 1
        print("Tickets running out!")

    def check_ticket_runout(self):
        if not single_find("TicketRunout"):
            return False
        return True

    def fight(self):
        print("Go to fight...")
        self.go_to_fight()
        time.sleep(3)  # Very slow
        print("Start fight...")
        self.start_fight()
        self.exit_fight()

    def exit_fight(self):
        print("Exiting fight...")
        if self.check_ticket_runout():
            cc = get_center("CancelBuy", self.map_scope)
            click_at(cc.x / self.sft, cc.y / self.sft)
            time.sleep(1)

        while single_find("Exit"):
            bt = get_center("Exit", self.map_scope)
            click_at(bt.x / self.sft, bt.y / self.sft)
            time.sleep(1)
        print("Exited fight...")


if __name__ == "__main__":
    f = Fight()
    f.fight()
