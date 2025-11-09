"""
Platform configuration module for cross-platform support.
Automatically detects the operating system and provides platform-specific settings.
"""
import platform
import os

# Detect current platform
CURRENT_PLATFORM = platform.system()  # Returns 'Windows', 'Darwin' (macOS), or 'Linux'
IS_WINDOWS = CURRENT_PLATFORM == "Windows"
IS_MAC = CURRENT_PLATFORM == "Darwin"

# Set platform-specific image directory
if IS_MAC:
    IMAGE_DIR = "pics/mac"
else:
    # Default to pics (Windows and other platforms)
    IMAGE_DIR = "pics"

def get_image_path(filename):
    """
    Get the full path to an image file based on the current platform.
    
    Args:
        filename: Just the filename or path with subdirectory (e.g., "throwbutton.png" or "star/ship_1.png")
    
    Returns:
        Full path to the image (e.g., "pics/mac/throwbutton.png" or "pics/mac/star/ship_1.png")
    """
    return os.path.join(IMAGE_DIR, filename)

# Print platform info for debugging
if __name__ == "__main__":
    print(f"Platform: {CURRENT_PLATFORM}")
    print(f"Image Directory: {IMAGE_DIR}")
    print(f"Sample path: {get_image_path('test.png')}")
