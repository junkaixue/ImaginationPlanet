"""pyautogui where there is a desktop (the Mac); on a host without one (the Linux inside the
cloud phone) a stand-in, so the fortress/zone modules import everywhere. There the screen is
an Android device: click.use_device() puts its screenshot on this same object.

    from desktop import pyautogui     # instead of `import pyautogui`

On macOS and Windows a failing import is a real problem and is raised as it is.
"""
import platform
import types

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_DESKTOP = True
except (Exception, SystemExit) as _err:   # (mouseinfo sys.exit()s on Linux without tkinter)
    if platform.system() in ("Darwin", "Windows"):
        raise
    HAS_DESKTOP = False
    _why = f"{type(_err).__name__}: {_err}"

    def _no_desktop(*args, **kwargs):
        raise RuntimeError(f"no desktop on this host ({_why}): run with --adb SERIAL")

    pyautogui = types.ModuleType("pyautogui")
    for _name in ("screenshot", "click", "moveTo", "mouseDown", "mouseUp", "position", "size"):
        setattr(pyautogui, _name, _no_desktop)
