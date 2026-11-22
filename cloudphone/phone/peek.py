"""The phone screen, scaled (default 0.5), as JPEG on stdout: small enough for a slow link.
    ./run.sh python3 /ip/peek.py [scale]"""
import io
import subprocess
import sys

from PIL import Image

DEVICE = "127.0.0.1:5555"
subprocess.run(["adb", "connect", DEVICE], capture_output=True, timeout=30)   # (a fresh adb server)
png = subprocess.run(["adb", "-s", DEVICE, "exec-out", "screencap", "-p"], capture_output=True, timeout=60).stdout
start = png.find(b"\x89PNG")
if start < 0:
    sys.exit(f"no screenshot: {png[:200]!r}")
im = Image.open(io.BytesIO(png[start:])).convert("RGB")
s = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
im = im.resize((int(im.width * s), int(im.height * s)))
buf = io.BytesIO()
im.save(buf, "JPEG", quality=75)
sys.stdout.buffer.write(buf.getvalue())
