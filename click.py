import pyautogui


def click_at(x, y):
    """
    Simulate a mouse click at the specified (x, y) coordinates.
    :param x: Horizontal coordinate (int)
    :param y: Vertical coordinate (int)
    """
    pyautogui.click(x, y)


def move_to(x, y):
    """
    Move the mouse pointer to the specified (x, y) coordinates.
    :param x: Horizontal coordinate (int)
    :param y: Vertical coordinate (int)
    """
    pyautogui.moveTo(x, y)
