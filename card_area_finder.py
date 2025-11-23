"""
Find Card Area Coordinates

Interactive tool to help you find the correct card area coordinates.
Move your mouse to mark the corners of the card matching area.
"""

import pyautogui
import time
from config_coords import ConfigCoords

print("=" * 70)
print("FIND CARD AREA COORDINATES")
print("=" * 70)

# Load config to get run button
config = ConfigCoords()

print(f"\nRun Button Position:")
print(f"  Pixel: ({config.rb.x}, {config.rb.y})")
rb_logical_x = config.rb.x / config.sft
rb_logical_y = config.rb.y / config.sft
print(f"  Logical: ({rb_logical_x:.1f}, {rb_logical_y:.1f})")
print(f"  Scaling factor: {config.sft}")

print("\n" + "=" * 70)
print("STEP 1: Find TOP-LEFT corner of card area")
print("=" * 70)
print("\nInstructions:")
print("1. Move your mouse to the TOP-LEFT corner of the card matching area")
print("2. Press ENTER when your mouse is in position")
input("\nPress ENTER when ready...")

# Get top-left position
tl_pos = pyautogui.position()
tl_logical_x = tl_pos.x / config.sft
tl_logical_y = tl_pos.y / config.sft

print(f"\nTop-left captured:")
print(f"  Physical: ({tl_pos.x}, {tl_pos.y})")
print(f"  Logical: ({tl_logical_x:.1f}, {tl_logical_y:.1f})")

# Calculate delta from run button
delta_tl_x = tl_logical_x - rb_logical_x
delta_tl_y = tl_logical_y - rb_logical_y

print(f"  Delta from Run Button: ({delta_tl_x:+.0f}, {delta_tl_y:+.0f})")

print("\n" + "=" * 70)
print("STEP 2: Find BOTTOM-RIGHT corner of card area")
print("=" * 70)
print("\nInstructions:")
print("1. Move your mouse to the BOTTOM-RIGHT corner of the card matching area")
print("2. Press ENTER when your mouse is in position")
input("\nPress ENTER when ready...")

# Get bottom-right position
br_pos = pyautogui.position()
br_logical_x = br_pos.x / config.sft
br_logical_y = br_pos.y / config.sft

print(f"\nBottom-right captured:")
print(f"  Physical: ({br_pos.x}, {br_pos.y})")
print(f"  Logical: ({br_logical_x:.1f}, {br_logical_y:.1f})")

# Calculate delta from run button
delta_br_x = br_logical_x - rb_logical_x
delta_br_y = br_logical_y - rb_logical_y

print(f"  Delta from Run Button: ({delta_br_x:+.0f}, {delta_br_y:+.0f})")

# Calculate size
width = br_logical_x - tl_logical_x
height = br_logical_y - tl_logical_y

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

print(f"\nCard Area:")
print(f"  Top-left (absolute): ({tl_logical_x:.1f}, {tl_logical_y:.1f})")
print(f"  Bottom-right (absolute): ({br_logical_x:.1f}, {br_logical_y:.1f})")
print(f"  Size: {width:.0f} × {height:.0f} pixels")

print(f"\n✅ Add these lines to configs/cood_mac.cfg:")
print("-" * 70)
print(f"pair_top_left: {delta_tl_x:.0f}, {delta_tl_y:.0f}")
print(f"pair_bottom_right: {delta_br_x:.0f}, {delta_br_y:.0f}")
print("-" * 70)

# For Windows config (multiply by scaling factor if this was Mac)
if config.sft != 1:
    print(f"\n📝 For Windows config (if needed), use these unscaled values:")
    print("-" * 70)
    delta_tl_x_win = delta_tl_x * config.sft
    delta_tl_y_win = delta_tl_y * config.sft
    delta_br_x_win = delta_br_x * config.sft
    delta_br_y_win = delta_br_y * config.sft
    print(f"pair_top_left: {delta_tl_x_win:.0f}, {delta_tl_y_win:.0f}")
    print(f"pair_bottom_right: {delta_br_x_win:.0f}, {delta_br_y_win:.0f}")
    print("-" * 70)

print("\n" + "=" * 70)
print("COPY THE VALUES ABOVE TO YOUR CONFIG FILE")
print("=" * 70)
