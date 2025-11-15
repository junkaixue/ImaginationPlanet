"""
Logging helper with timestamps for all log messages.
"""
from datetime import datetime


def log(message):
    """Print message with timestamp prefix.
    
    Args:
        message: The message to log
    """
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {message}")
