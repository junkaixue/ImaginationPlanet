from common import *
import time
from collections import namedtuple

Point = namedtuple('Point', ['x', 'y'])

class StarPick:
    ships = ["Ship1", "Ship2", "Ship3", "Ship4"]
    ship_coo = []
    free = set()

    def __init__(self, sft = 0):
        if sft == 0:
            self.sft = get_scaling_factor()
        else:
            self.sft = sft


    def count_free_ship(self):
        while not single_find("ShipList"):
            time.sleep(2)
            print("Not find ship list button")

        while not single_find("ShipPage"):
            center = get_center("ShipList", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
            print ("Clicked the ship list")

        if len(self.ship_coo) == 0:
            c1 = get_center("Ship1", "Single")
            c2 = get_center("Ship2", "Single")
            offset = c2.x - c1.x
            self.ship_coo.append(Point(c1.x, c1.y))
            self.ship_coo.append(Point(c2.x, c2.y))
            self.ship_coo.append(Point(c2.x + offset, c2.y))
            self.ship_coo.append(Point(c2.x + 2 * offset, c1.y))

        for i in range(0, len(self.ship_coo)):
            ship = self.ships[i]
            click_at(self.ship_coo[i].x / self.sft, self.ship_coo[i].y / self.sft)
            time.sleep(1)
            print("Check ship: " + ship)
            if single_find("ShipFree"):
                print ("Ship " + ship + " is free")
                self.free.add(ship)

        while single_find("ShipPage"):
            center = get_center("CloseList", "Single")
            click_at(center.x / self.sft, center.y / self.sft + 20)
            time.sleep(1)
            print("Closed the ship list")

    def pick_up(self):
        stars = get_all("Star", "Single")
        for s in stars:
            click_at(s.x / self.sft, s.y / self.sft)
            time.sleep(1)
            print("Picked the star at " + str(s.x / self.sft) + "," + str(s.y / self.sft))
            center = get_center("StarPick", "Single")
            click_at(center.x / self.sft, center.y / self.sft - 200)
            #click_at(center.x / self.sft, center.y / self.sft)



if __name__ == "__main__":
    s = StarPick(1)
    s.count_free_ship()
    print(s.free)
    s.pick_up()