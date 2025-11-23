"""
Test Snapshot Coordinates

Verifies that the card area coordinates are calculated correctly for auto_snapshot_solver.
"""

from auto_snapshot_solver import AutoSnapshotSolver
import platform

print("=" * 70)
print("SNAPSHOT COORDINATE TEST")
print("=" * 70)

print(f"\nPlatform: {platform.system()}")

# Create solver (this will load config and calculate card area)
solver = AutoSnapshotSolver()

print("\n" + "=" * 70)
print("LOADING CONFIGURATION")
print("=" * 70)

success = solver.load_config()

if not success:
    print("❌ Failed to load configuration!")
else:
    print("✅ Configuration loaded successfully!")
    
    print("\n" + "=" * 70)
    print("CARD AREA DETAILS")
    print("=" * 70)
    
    print(f"\nRun Button:")
    print(f"  Pixel coordinates: ({solver.config.rb.x}, {solver.config.rb.y})")
    print(f"  Scaling factor: {solver.config.sft}")
    rb_logical = (solver.config.rb.x / solver.config.sft, solver.config.rb.y / solver.config.sft)
    print(f"  Logical coordinates: ({rb_logical[0]:.1f}, {rb_logical[1]:.1f})")
    
    print(f"\nCard Area Configuration:")
    tl = solver.config.get_coord("pair_top_left")
    br = solver.config.get_coord("pair_bottom_right")
    
    if tl and br:
        print(f"  pair_top_left (from config):")
        print(f"    Delta: {solver.config.coords['pair_top_left']}")
        print(f"    Absolute: ({tl[0]:.1f}, {tl[1]:.1f})")
        
        print(f"  pair_bottom_right (from config):")
        print(f"    Delta: {solver.config.coords['pair_bottom_right']}")
        print(f"    Absolute: ({br[0]:.1f}, {br[1]:.1f})")
    
    print(f"\nCalculated Card Area (from solver):")
    print(f"  Top-left: ({solver.card_area['x1']}, {solver.card_area['y1']})")
    print(f"  Bottom-right: ({solver.card_area['x2']}, {solver.card_area['y2']})")
    print(f"  Width: {solver.card_area['width']} pixels")
    print(f"  Height: {solver.card_area['height']} pixels")
    
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    # Verify the calculations are reasonable
    if solver.card_area['width'] > 0 and solver.card_area['height'] > 0:
        print("✅ Card area has positive dimensions")
    else:
        print("❌ ERROR: Card area has invalid dimensions!")
    
    if solver.card_area['width'] < 2000 and solver.card_area['height'] < 2000:
        print("✅ Card area dimensions are reasonable")
    else:
        print("⚠️  WARNING: Card area dimensions seem very large!")
    
    # Check if x1 < x2 and y1 < y2
    if solver.card_area['x1'] < solver.card_area['x2']:
        print("✅ x1 < x2 (correct)")
    else:
        print("❌ ERROR: x1 >= x2 (coordinates swapped?)")
    
    if solver.card_area['y1'] < solver.card_area['y2']:
        print("✅ y1 < y2 (correct)")
    else:
        print("❌ ERROR: y1 >= y2 (coordinates swapped?)")

print("\n" + "=" * 70)
