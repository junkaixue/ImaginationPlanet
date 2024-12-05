import time

from click import *
from common import *


class RedPack():
    sft = 0.0
    count = 0

    def __init__(self, sfto):
        self.count = 0
        self.sft = sfto if sfto != 0 else get_scaling_factor()
        print ("start red pack waiting...")


    def get_red_pack(self):
        while single_find("Chat"):
            center = get_center("Chat", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(2)
        print ("Entered chat")
        while True:
            if single_find("TooManyRequest"):
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif single_find("RollRed"):
                self.single_get("RollRed")
            elif single_find("DiamRed"):
                self.single_get("DiamRed")
            else:
                print ("Nothing sleep 2 seconds")
                time.sleep(2)
            

    def single_get(self, pk_name):
        while single_find(pk_name):
            center = get_center(pk_name, "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)

        center = get_center("TakeRed", "Single")
        click_at(center.x / self.sft, center.y / self.sft)
        time.sleep(2)
        click_at(center.x / self.sft, center.y / self.sft)
        time.sleep(2)
        while single_find("RedBack"):
            center = get_center("RedBack", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(2)
        print ("Got red_pack")
        self.count += 1

if __name__ == '__main__': 
    r = RedPack(0)
    r.get_red_pack()
