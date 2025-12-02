"""
Configuration-based Coordinate Clicking

Reads platform-specific coordinate configurations and provides functions
to click at positions relative to the Run Button.

Config file format:
    name:deltax,deltay
    
Example:
    visit_last_c1:-154,-406
    cat_house:250,-724

Usage:
    # Normal mode (auto-detects Run Button)
    config = ConfigCoords()
    config.click_coord("cat_house", delay=1)
    
    # Mock mode for testing (uses mock Run Button position)
    config = ConfigCoords(mock_rb=(2667, 1164))
    config.click_coord("cat_house")  # Still actually clicks! Just uses mock RB position
    
    # Dry-run mode (only prints, doesn't click)
    config.click_coord("cat_house", dry_run=True)
"""

import os
import platform
from common import get_center, get_scaling_factor
from click import click_at


class ConfigCoords:
    """Handles reading and clicking coordinates from platform-specific config files."""
    
    def __init__(self, mock_rb=None):
        """Initialize and load platform-specific configuration.
        
        Args:
            mock_rb: Optional tuple (x, y) to mock Run Button position for testing.
                     If provided, skips automatic Run Button detection.
        """
        self.sft = get_scaling_factor()
        self.rb = None  # Run button center
        self.coords = {}  # Dictionary of name -> (delta_x, delta_y)
        self.mock_mode = (mock_rb is not None)
        
        # Determine platform-specific config file
        is_mac = (platform.system() == "Darwin")
        config_file = "cood_mac.cfg" if is_mac else "cood_win.cfg"
        config_path = os.path.join("configs", config_file)
        
        print(f"Platform: {platform.system()}")
        print(f"Loading config from: {config_path}")
        
        # Load coordinates from config
        self._load_config(config_path)
        
        # Find run button (or use mock)
        if mock_rb:
            from collections import namedtuple
            Point = namedtuple('Point', ['x', 'y'])
            self.rb = Point(mock_rb[0], mock_rb[1])
            print(f"\nMOCK MODE: Using mock Run Button at ({self.rb.x}, {self.rb.y})")
            rb_x_logical = self.rb.x / self.sft
            rb_y_logical = self.rb.y / self.sft
            print(f"   Logical coordinates: ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
        else:
            self._find_run_button()
    
    def _load_config(self, config_path):
        """Load coordinates from config file.
        
        Args:
            config_path: Path to the config file
        """
        if not os.path.exists(config_path):
            print(f"Warning: Config file not found at {config_path}")
            return
        
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse line: name:deltax,deltay
                try:
                    name, coords = line.split(':')
                    name = name.strip()
                    
                    # Remove trailing period if present (fix typo in config)
                    coords = coords.strip().rstrip('.')
                    
                    delta_x, delta_y = coords.split(',')
                    delta_x = float(delta_x.strip())
                    delta_y = float(delta_y.strip())
                    
                    self.coords[name] = (delta_x, delta_y)
                    print(f"  Loaded {name}: Δx={delta_x:+.1f}, Δy={delta_y:+.1f}")
                    
                except ValueError as e:
                    print(f"Warning: Could not parse line '{line}': {e}")
        
        print(f"Loaded {len(self.coords)} coordinate entries")
    
    def _find_run_button(self):
        """Find and store the Run Button center position."""
        import time
        
        print("\nLooking for Run Button...")
        retry = 10
        
        while retry > 0 and self.rb is None:
            try:
                self.rb = get_center("RunButton", "Main")
                print(f"✅ Found Run Button at: ({self.rb.x}, {self.rb.y}) [pixel coords]")
                rb_x_logical = self.rb.x / self.sft
                rb_y_logical = self.rb.y / self.sft
                print(f"   Logical coordinates: ({rb_x_logical:.1f}, {rb_y_logical:.1f})")
                
                # Update config file with run button coordinate
                ConfigCoords.update_run_button_in_config(rb_x_logical, rb_y_logical)
            except:
                print(f"Run Button not found, retrying... ({retry} attempts left)")
                retry -= 1
                time.sleep(1)
        
        if self.rb is None:
            raise RuntimeError("Failed to find Run Button. Make sure the game window is visible.")
    
    def get_coord(self, name):
        """Get the absolute screen coordinates for a named position.
        
        Args:
            name: Name of the coordinate from config file
            
        Returns:
            Tuple of (x, y) in logical coordinates, or None if not found
        """
        if name not in self.coords:
            print(f"Warning: Coordinate '{name}' not found in config")
            return None
        
        delta_x, delta_y = self.coords[name]
        
        # Calculate absolute position from run button + delta
        rb_x_logical = self.rb.x / self.sft
        rb_y_logical = self.rb.y / self.sft
        
        abs_x = rb_x_logical + delta_x
        abs_y = rb_y_logical + delta_y
        
        return (abs_x, abs_y)
    
    def click_coord(self, name, delay=0, dry_run=False):
        """Click at a named coordinate position.
        
        Args:
            name: Name of the coordinate from config file
            delay: Optional delay in seconds after clicking
            dry_run: If True, only print where it would click (don't actually click)
            
        Returns:
            True if successful, False if coordinate not found
        """
        coords = self.get_coord(name)
        
        if coords is None:
            return False
        
        x, y = coords
        
        if dry_run:
            print(f"[DRY RUN] Would click '{name}' at ({x:.1f}, {y:.1f})")
        else:
            mode_indicator = "[MOCK] " if self.mock_mode else ""
            print(f"{mode_indicator}Clicking '{name}' at ({x:.1f}, {y:.1f})")
            click_at(x, y)
        
        if delay > 0:
            import time
            time.sleep(delay)
        
        return True
    
    def list_coords(self):
        """Print all available coordinate names."""
        print("\nAvailable coordinates:")
        for name, (delta_x, delta_y) in sorted(self.coords.items()):
            print(f"  {name}: Δx={delta_x:+.1f}, Δy={delta_y:+.1f}")
    
    @staticmethod
    def update_run_button_in_config(rb_x, rb_y):
        """Update the run_button coordinate in the platform-specific config file.
        
        Args:
            rb_x: Run Button x coordinate (logical)
            rb_y: Run Button y coordinate (logical)
        """
        # Determine platform-specific config file
        is_mac = (platform.system() == "Darwin")
        config_file = "cood_mac.cfg" if is_mac else "cood_win.cfg"
        config_path = os.path.join("configs", config_file)
        
        if not os.path.exists(config_path):
            print(f"Warning: Config file not found at {config_path}, cannot update run_button")
            return
        
        # Read all lines from config
        with open(config_path, 'r') as f:
            lines = f.readlines()
        
        # Update or add run_button line
        run_button_line = f"run_button:{rb_x:.0f},{rb_y:.0f}\n"
        found_run_button = False
        
        for i, line in enumerate(lines):
            if line.strip().startswith('run_button:'):
                lines[i] = run_button_line
                found_run_button = True
                break
        
        # If run_button not found, add it after comments/blank lines
        if not found_run_button:
            # Find a good position to insert (after initial comments)
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('#'):
                    insert_pos = i
                    break
            lines.insert(insert_pos, run_button_line)
        
        # Write back to config file
        with open(config_path, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ Updated {config_file} with run_button: ({rb_x:.0f}, {rb_y:.0f})")


# Convenience function for one-off clicks
def click_from_config(name, delay=0):
    """Quick function to click a coordinate from config.
    
    Args:
        name: Name of the coordinate from config file
        delay: Optional delay in seconds after clicking
        
    Returns:
        True if successful, False otherwise
    """
    config = ConfigCoords()
    return config.click_coord(name, delay)


if __name__ == "__main__":
    # Example usage
    print("=" * 70)
    print("CONFIG COORDS - Test")
    print("=" * 70)
    
    config = ConfigCoords()
    config.list_coords()
    
    print("\n" + "=" * 70)
    print("Test complete. Use config.click_coord('name') to click positions.")
    print("=" * 70)
