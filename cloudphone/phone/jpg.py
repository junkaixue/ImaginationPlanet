"""An image file on the phone (e.g. a debug shot), scaled (default 0.5), as JPEG on stdout.
    ./run.sh python3 /ip/jpg.py /ip/app/pics/mac/zone/debug/NAME.png [scale]"""
import io
import sys

from PIL import Image

im = Image.open(sys.argv[1]).convert("RGB")
s = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
im = im.resize((int(im.width * s), int(im.height * s)))
buf = io.BytesIO()
im.save(buf, "JPEG", quality=80)
sys.stdout.buffer.write(buf.getvalue())
