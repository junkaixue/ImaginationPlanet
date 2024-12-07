import cv2
import pytesseract
import easyocr
from click import click_at
from common import get_center, single_find_map
import time
from collections import namedtuple
import pyautogui


# Configure Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

ScreenRegion = namedtuple('ScreenRegion', ['left', 'top', 'width', 'height'])
easy_reader = easyocr.Reader(['en'])



def preprocess_image(image_path):
    """
    Preprocess the image for Tesseract (grayscale and binary thresholding).
    """
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    return binary

def screen_shot_by_area(my_region):
    # Pass the region to pyautogui
    screenshot = pyautogui.screenshot(region=my_region)
    screenshot.save("tmp.png")

def run_easyocr(image_path):
    """
    Perform OCR using EasyOCR.
    """
    results = easy_reader.readtext(image_path)
    # Concatenate all detected text
    for bbox, text, confidence in results:
        ct = text.strip()
        if ct.isdigit():
            return int(ct)
    return -1


class RobotCheck:
    left_add = None
    right_add = None
    loc_e = None
    loc_p = None
    result = 0
    answers = []
    sft = 0
    def __init__(self, sft):
        self.sft = sft
        self.compute_pos()

    def compute_pos(self):
        self.loc_p = None
        self.loc_e = None
        while self.loc_p is None:
            try:
                self.loc_p = pyautogui.locateOnScreen(single_find_map["Plus"])
            except:
                print("Plus not found")
        print("Plus found")
        """
        while self.loc_e is None:
            try:
                self.loc_e = pyautogui.locateOnScreen(single_find_map["Equal"])
            except:
                print("Equal not found")
        print("Equal found")
        """
        
        # left and right
        #c_len = self.loc_e.left - self.loc_p.left - self.loc_p.width
        #c_len += 10
        #self.left_add = ScreenRegion(int(self.loc_p.left - c_len), int(self.loc_e.top), int(c_len) , int(self.loc_e.height))
        #self.right_add = ScreenRegion(int(self.loc_p.left + self.loc_p.width), int(self.loc_e.top), int(c_len), int(self.loc_e.height))

        # answers
        # gift can block searching
        loc_w = None
        while loc_w is None:
            try:
                loc_w = pyautogui.locateOnScreen(single_find_map["QWD"])
            except:
                time.sleep(5)
        loc_r = pyautogui.locateOnScreen(single_find_map["QReward"])

        top_line = int(self.loc_p.top + 2 * self.loc_p.height)
        w_w = loc_r.left + loc_r.width - loc_w.left
        s_w = (loc_w.width - 2 * w_w) // 2
        self.answers.append(ScreenRegion(int(loc_w.left), top_line, int(w_w), int(loc_r.top - top_line)))
        self.answers.append(ScreenRegion(int(loc_w.left + w_w), top_line, int(s_w), int(loc_r.top - top_line)))
        self.answers.append(ScreenRegion(int(loc_w.left + w_w + s_w), top_line, int(s_w), int(loc_r.top - top_line)))
        self.answers.append(ScreenRegion(int(loc_w.left + w_w + 2 * s_w), top_line, int(s_w), int(loc_r.top - top_line)))


    def get_add_numbers(self, screen_region):
        screen_shot_by_area(screen_region)
        return run_easyocr("tmp.png")
       #

    def break_check(self):
        result = 0
        # loc_tt = ScreenRegion(int(self.loc_e.left - 4 * self.loc_p.width), int(self.loc_e.top), int(4 * self.loc_p.width),
        #                      int(self.loc_e.height))
        loc_tt = ScreenRegion(int(self.loc_p.left - 2 * self.loc_p.width), int(self.loc_p.top), int(3.9 * self.loc_p.width),
                              int(self.loc_p.height))
        screen_shot_by_area(loc_tt)
        results = easy_reader.readtext("tmp.png")
        if len(results) > 1 or '+' not in results[0][1]:
            print ("Result is not found")
            return
        d = results[0][1].split('+')
        result += int(d[0])
        result += int(d[1])
        print ("Computed result : " + str(result))
        self.click_answer(result)
        center = get_center("QConfirm", "Single")
        click_at(center.x, center.y)

    def click_answer(self, result):
        for area in self.answers:
            screen_shot_by_area(area)
            # print ("Screen shot area" + str(area))
            results = easy_reader.readtext("tmp.png")
            # Concatenate all detected text
            for bbox, text, confidence in results:
                ct = text.strip()
                if ct.isdigit() and result == int(ct):
                    print ("Find result by easyocr. result : " + ct)
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]

                    # Calculate the center of the bounding box in image coordinates
                    center_x_image = (min(x_coords) + max(x_coords)) / 2
                    center_y_image = (min(y_coords) + max(y_coords)) / 2

                    # Map the center to screen coordinates
                    center_x_screen = center_x_image + area[0]
                    center_y_screen = center_y_image + area[1]
                    print ("It locates at: " + str(center_x_screen) + " " + str(center_x_screen))
                    click_at(center_x_screen, center_y_screen)
                    return
            processed_image = preprocess_image("tmp.png")
            data = pytesseract.image_to_boxes(processed_image, config='-c tessedit_char_whitelist=0123456789')

            # Image dimensions (needed to flip Y-axis for Tesseract coordinates)
            image_height = area[3]

            # Parse data and filter for digits
            for line in data.splitlines():
                char, x1, y1, x2, y2, _ = line.split()
                if char.isdigit() and result == int(char):  # Check if the character is a digit
                    print ("Find result by tesseract. result : " + char)
                    # Convert coordinates to integers
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                    # Calculate center in image coordinates
                    center_x_image = (x1 + x2) / 2
                    center_y_image = image_height - ((y1 + y2) / 2)  # Flip Y-axis

                    # Map to screen coordinates
                    center_x_screen = center_x_image + area[0]
                    center_y_screen = center_y_image + area[1]
                    print ("It locates at: " + str(center_x_screen) + " " + str(center_x_screen))
                    click_at(center_x_screen, center_y_screen)
                    return




if __name__ == "__main__":
    r = RobotCheck(1)
    r.break_check()

