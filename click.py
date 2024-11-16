import Quartz
import time

def click_at(x, y):
    """
    Simulate a mouse click at the specified (x, y) coordinates.
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

# print(f"Clicked at ({x}, {y})")

def move_to(x, y):
    event_move = Quartz.CGEventCreateMouseEvent(
        None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_move)

# Move to (500, 300)
#move_to(200, 200)

# Example: Simulate a click at (500, 300) on the desktop
#for i in range(1,100):
#    click_at(1200, 800)
#    time.sleep(2)
    
click_at(1214,810)
