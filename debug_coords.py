"""
Debug Coordinate Calculations

Shows exactly what coordinates are being calculated from the config file.
"""

from config_coords import ConfigCoords

print("=" * 70)
print("COORDINATE DEBUG")
print("=" * 70)

# Load config
config = ConfigCoords()

print("\n" + "=" * 70)
print("CALCULATED ABSOLUTE COORDINATES")
print("=" * 70)

# Test a few key coordinates
test_coords = ["cat_house", "gohome_confirm", "repair_entry", "card_button"]

for name in test_coords:
    coords = config.get_coord(name)
    if coords:
        print(f"{name:20s} → ({coords[0]:7.1f}, {coords[1]:7.1f})")
    else:
        print(f"{name:20s} → NOT FOUND")

print("\n" + "=" * 70)
print("BREAKDOWN FOR 'cat_house':")
print("=" * 70)

if "cat_house" in config.coords:
    delta_x, delta_y = config.coords["cat_house"]
    rb_x_pixel = config.rb.x
    rb_y_pixel = config.rb.y
    rb_x_logical = rb_x_pixel / config.sft
    rb_y_logical = rb_y_pixel / config.sft
    
    print(f"Run Button (pixel):    ({rb_x_pixel:.1f}, {rb_y_pixel:.1f})")
    print(f"Run Button (logical):  ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
    print(f"Scaling Factor:        {config.sft}")
    print(f"Delta from config:     ({delta_x:+.1f}, {delta_y:+.1f})")
    print(f"Final absolute:        ({rb_x_logical + delta_x:.1f}, {rb_y_logical + delta_y:.1f})")
    
    print("\nIf deltas should be scaled:")
    scaled_delta_x = delta_x / config.sft
    scaled_delta_y = delta_y / config.sft
    print(f"Scaled delta:          ({scaled_delta_x:+.1f}, {scaled_delta_y:+.1f})")
    print(f"Final with scaling:    ({rb_x_logical + scaled_delta_x:.1f}, {rb_y_logical + scaled_delta_y:.1f})")

print("\n" + "=" * 70)
