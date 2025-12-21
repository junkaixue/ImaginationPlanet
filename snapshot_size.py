"""Test snapshot resolution on Mac"""
import pyautogui
import cv2
import numpy as np
from common import get_scaling_factor

sft = get_scaling_factor()
print(f"Scaling factor: {sft}")
print(f"Screen size: {pyautogui.size()}")

# Test snapshot of a specific region
# Logical coordinates: (983, 287) to (1449, 840)
# Size: 466×553 logical
region_x, region_y = 983, 287
region_w, region_h = 466, 553

print(f"\nTaking snapshot:")
print(f"  Region (logical): ({region_x}, {region_y}) {region_w}×{region_h}")

screenshot = pyautogui.screenshot(region=(region_x, region_y, region_w, region_h))
screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

print(f"  Captured size: {screenshot_cv.shape[1]}×{screenshot_cv.shape[0]}")
print(f"  Expected on Retina: {region_w * 2}×{region_h * 2}")

# Save for inspection
cv2.imwrite("test_snapshot.png", screenshot_cv)
print(f"\nSaved to test_snapshot.png")
