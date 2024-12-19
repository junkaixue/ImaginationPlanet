# -*- coding: utf-8 -*-

from pynput.keyboard import Controller, Key
import time
from datetime import datetime, timedelta

from robot_check import RobotCheck

keyboard = Controller()

from click import *
from common import *
import ctypes
import random



class RedPack:
    sft = 0.0
    count = 0
    thankyou_texts = ["xie xie!", "3q", "duo xie hong bao!", "xx"]
    now = 0
    timeout= 7200
    rb = None
    
    
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
            elif simple_single_find("RobotDetected", "Single", 0.8):
                if self.rb is None:
                    self.rb = RobotCheck(self.sft)
                self.rb.break_check()
                time.sleep(1)
            elif simple_single_find("RollRed", "Single", 0.8):
                self.single_get("RollRed")
            elif simple_single_find("DiamRed", "Single", 0.8):
                self.single_get("DiamRed")
            else:
                print ("Nothing sleep 1 seconds")
                time.sleep(1)
        while single_find("MainBack"):
            print ("Get red pack finished")
            center = get_center("MainBack", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(2)
        print("finished red")
            

    def single_get(self, pk_name):
        thankyou = False
        while simple_single_find(pk_name, "Single", 0.8):
            if simple_single_find("RobotDetect", "Single", 0.8):
                if self.rb is None:
                    self.rb = RobotCheck(self.sft)
                self.rb.break_check()
            center = get_center_h(pk_name, "Single", 0.8)
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)

        if single_find("TakeRed"):
            self.count += 1
            print ("New Red Pack")
            center = get_center("TakeRed", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
            thankyou = True
        while single_find("RedBack"):
            center = get_center("RedBack", "Single")
            click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
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
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
            # center = get_center("SendText", "Single")
            # click_at(center.x / self.sft, center.y / self.sft)
            time.sleep(1)
        except:
            print ("Failed to say thank you")

if __name__ == '__main__': 
    r = RedPack(0)
    r.get_red_pack()

