import mss

with mss.mss() as sct:
    # Get all monitors
    monitors = sct.monitors

    # Print monitor information
    for idx, monitor in enumerate(monitors):
        print(f"Monitor {idx}: {monitor}")
