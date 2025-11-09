import platform
import pyautogui

# Platform-specific imports and click implementation
if platform.system() == "Darwin":  # macOS
    import Quartz
    
    def click_at(x, y):
        """
        Simulate a mouse click at the specified (x, y) coordinates using Quartz (macOS).
        :param x: Horizontal coordinate (int)
        :param y: Vertical coordinate (int)
        """
        # Create mouse event for click down
        event_down = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventLeftMouseDown, (x, y), Quartz.kCGMouseButtonLeft
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)

        # Create mouse event for click up
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
