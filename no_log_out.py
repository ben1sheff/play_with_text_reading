import pyautogui as pag
from easyocr import Reader
import time
import numpy as np

def make_printv(verbose):
    ''' Makes a print function depending on verbosity setting '''
    if not verbose:
        return lambda *args, **kwargs: None
    else:
        return print
        

class NoLogOut:
    def __init__(self, click_text, verbose=True, gpu=False):
        self.ocr_reader = Reader(["en"], gpu=gpu)
        self.click_text = click_text
        self.last_mouse_pos = pag.position()
        self.center = None
        self.height = None
        self.width = None
        self.printv = make_printv(verbose)
        

    def text_match(self, text, sample):
        ''' test if text matches. Fuzzy matching would be better, but this is fine '''
        return text.lower() in sample.lower()
    
    def text_coord(self, ocr_results):
        ''' dig through the ocr results for particular text, return the center, height, and width '''
        for item in ocr_results:
            if self.text_match(self.click_text, item[1]):  # may want to do fuzzy matching
                coords = item[0]
                width = coords[2][0] - coords[0][0]
                height = coords[2][1] - coords[0][1]
                center = [coords[0][0] + width // 2, coords[0][1] + height // 2]
                return center, height, width
        raise Exception("Could not find the required text")
        
    def find_button(self):
        ''' Take a screenshot, read the text from it with easyocr, and run text_coord on that text '''
        screenshot = pag.screenshot()
        ocr_results = self.ocr_reader.readtext(np.asarray(screenshot.convert("RGB")))
        self.center, self.height, self.width = self.text_coord(ocr_results)

    def verify_button(self, padding=6):
        ''' function to quickly verify the desired text has not moved on the screen.
            This is achieved by taking a screenshot, cropping to the observed text plus
            a few pixels on each side, and verifying with easyocr that the included text
            is still just the desired text
             
            Arguments:
            - padding: how many pixels to add to each side of the desired text
             
            Return bool: True indicates text is still there, False indicates it is not '''
        if self.center is None:
            raise Exception("have to find a button before verifying it")
        just_target = np.asarray(pag.screenshot().convert("RGB"))
        just_target = just_target[self.center[1] - self.height // 2 - padding: 
                                    self.center[1] + self.height // 2 + padding,
                                  self.center[0] - self.width // 2 - padding: 
                                    self.center[0] + self.width // 2 + padding]
        # self.printv("verifying on a text of size", just_target.shape)
        new_ocr = self.ocr_reader.readtext(just_target)
        # self.printv("we're done verifying")
        return len(new_ocr) and self.text_match(self.click_text, new_ocr[0][1])
    
    def is_active(self):
        ''' 
        Check if the mouse is in the same location as the last time this was run or 
        when the object was initialized if this has not been run
        '''
        new_pos = pag.position()
        active = not all([new_coord == old_coord for new_coord, old_coord in zip(new_pos, self.last_mouse_pos)])
        if active:
            self.last_mouse_pos = new_pos
        return active

    def run(self, sleep_time=540, check_interval=60):
        '''
        Starts a loop that regularly checks if you have been active, and if you haven't
        within the sleep_time interval, clicks on self.click_text to keep a desired
        app or computer awake. Note that this tries to keep the checks evenly spaced, so 
        the total wait between automated activity may be up to check_interval above
        sleep_time, plus processing time.
        
        Arguments:
        - sleep_time: how many seconds since the last activity should we wait before 
            clicking on self.click_text
        - check_interval: how long to wait between checks for if we are still active
            (notably, each check can take up to a few seconds on a cpu)
        '''
        self.find_button()
        last_active = time.time()
        last_check = last_active
        while True:
            time.sleep((-(time.time() + 0.001 - last_check)) % check_interval)
            last_check = time.time() # Record this so the checks remain evenly spaced
            # Check if we've been active
            if not self.is_active():
                self.printv("we have been inactive since", last_active)
                if last_check - last_active >= sleep_time:
                    self.printv("time to click")
                    if not self.verify_button():
                        self.find_button()
                        self.printv("have to re-find the button")
                    pag.click(*self.center)

            if self.is_active() or (last_check - last_active >= sleep_time):
                last_active = time.time()
                self.printv("we're active")       

