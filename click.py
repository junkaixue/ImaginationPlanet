import platform
import pyautogui

pyautogui.FAILSAFE = False

# Platform-specific imports and click implementation
if platform.system() == "Darwin":  # macOS
    import Quartz
    
    def click_at(x, y):
        """
        Simulate a mouse click at the specified (x, y) coordinates using Quartz (macOS).
        :param x: Horizontal coordinate (int)
        :param y: Vertical coordinate (int)
        """
        import time

        # Move the pointer there first and hold the button briefly: the Android emulator
        # ignores a down/up pair posted at the same instant without a preceding move.
        event_move = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_move)
        time.sleep(0.05)

        event_down = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventLeftMouseDown, (x, y), Quartz.kCGMouseButtonLeft
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
        time.sleep(0.08)

        event_up = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventLeftMouseUp, (x, y), Quartz.kCGMouseButtonLeft
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)
    
    def move_to(x, y):
        """
        Move the mouse pointer to the specified (x, y) coordinates using Quartz (macOS).
        :param x: Horizontal coordinate (int)
        :param y: Vertical coordinate (int)
        """
        event_move = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_move)

    def drag(x1, y1, x2, y2, duration=0.7, steps=14, hold=0.3, press=0.1):
        """
        Press at (x1, y1), move to (x2, y2) in small steps and release (macOS).
        `press` is the pause between pressing and moving (longer on pages whose cells react
        to taps); the pause before release avoids the emulator's fling/inertia scrolling.
        """
        import time

        def post(kind, x, y):
            ev = Quartz.CGEventCreateMouseEvent(None, kind, (x, y), Quartz.kCGMouseButtonLeft)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

        post(Quartz.kCGEventMouseMoved, x1, y1)
        time.sleep(0.05)
        post(Quartz.kCGEventLeftMouseDown, x1, y1)
        time.sleep(press)
        for i in range(1, steps + 1):
            t = i / steps
            post(Quartz.kCGEventLeftMouseDragged, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
            time.sleep(duration / steps)
        time.sleep(hold)
        post(Quartz.kCGEventLeftMouseUp, x2, y2)

else:  # Windows and other platforms
    def click_at(x, y):
        """
        Simulate a mouse click at the specified (x, y) coordinates using PyAutoGUI.
        :param x: Horizontal coordinate (int)
        :param y: Vertical coordinate (int)
        """
        pyautogui.click(x, y)

    def move_to(x, y):
        """
        Move the mouse pointer to the specified (x, y) coordinates using PyAutoGUI.
        :param x: Horizontal coordinate (int)
        :param y: Vertical coordinate (int)
        """
        pyautogui.moveTo(x, y)

    def drag(x1, y1, x2, y2, duration=0.7, steps=14, hold=0.3, press=0.1):
        """
        Press at (x1, y1), move to (x2, y2) and release (PyAutoGUI).
        """
        import time
        pyautogui.moveTo(x1, y1)
        pyautogui.mouseDown()
        time.sleep(press)
        pyautogui.moveTo(x2, y2, duration=duration)
        time.sleep(hold)
        pyautogui.mouseUp()
