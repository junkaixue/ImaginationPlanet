# -*- coding: utf-8 -*-

from pynput.keyboard import Controller
import time
from datetime import datetime, timedelta

keyboard = Controller()

from click import *
from common import *
import ctypes
import random



class RedPack():
    sft = 0.0
    count = 0
    thankyou_texts = ["xie xie!", "3q", "duo xie hong bao!", "lao ban da qi!"]
    now = 0
    timeout= 7200
    
    
    def __init__(self, sfto):
        self.now = datetime.now()
        self.count = 0
        self.sft = sfto if sfto != 0 else get_scaling_factor()
        print ("start red pack waiting...")

    def get_red_pack(self):
        while single_find("Chat"):
            center = get_center("Chat", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(2)
        print ("Entered chat")
        while self.now + timedelta(seconds=self.timeout) >= datetime.now():
            if single_find("TooManyRequest"):
                center = get_center("Confirm", "Single")
                click_at(center.x / self.sft, center.y / self.sft)
                time.sleep(1)
            elif simple_single_find("RollRed", "Single", 0.97):
                self.single_get("RollRed")
            elif simple_single_find("DiamRed", "Single", 0.99):
                self.single_get("DiamRed")
            else:
                print ("Nothing sleep 2 seconds")
                time.sleep(2)
            

    def single_get(self, pk_name):
        thankyou = False
        while simple_single_find(pk_name, "Single", 0.97):
            center = get_center_h(pk_name, "Single", 0.97)
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)

        if single_find("TakeRed"):
            self.count += 1
            print ("New Red Pack")
            center = get_center("TakeRed", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(2)
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(2)
            thankyou = True
        while single_find("RedBack"):
            center = get_center("RedBack", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(2)
        print ("Got red_pack")
        self.count += 1

        if thankyou:
            self.send_thankyou()
        
    def send_thankyou(self):
        try:
            t = self.thankyou_texts[random.randint(0, len(self.thankyou_texts) - 1)]
            print ("Find chatbar")
            center = get_center("ChatBar", "Single")
            pyautogui.click(center.x / self.sft, center.y / self.sft, clicks=2, interval=0.2)
            time.sleep(1)
            print ("Paste thank you")
            for char in t:
                keyboard.type(char)
                time.sleep(0.05) 
            time.sleep(0.5)
            print ("Click send")
            center = get_center("SendText", "Single")
            # click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
        except:
            print ("Failed to say thank you")

if __name__ == '__main__': 
    r = RedPack(0)
    r.send_thankyou()
    r.get_red_pack()

