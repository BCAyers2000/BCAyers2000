"""Swim the nightly koi onto the toolkit row in both themes, with ripples.

python koi_card.py <koi.gif> <assets_dir> <out_dir>
Reads koi-{mocha,latte}.png that compose.py left in <assets_dir> and writes
<out_dir>/koi-{mocha,latte}.webp. Needs Pillow.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageSequence

KOI_X = 0.81  # under the particle in compose.py
BOX = (500, 420)
RIPPLE = {"mocha": (180, 190, 254), "latte": (114, 135, 253)}
N_RINGS, R_IN, R_OUT, SQUASH, PEAK = 4, 90, 316, 0.42, 90


def enlarge(frames):
    """Crops to the swim path and scales by the largest whole factor that fits
    BOX, so a young koi is not lost in its canvas and stays pixel sharp."""
    box = frames[0].getchannel("A").getbbox()
    for f in frames[1:]:
        b = f.getchannel("A").getbbox()
        box = (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    w, h = box[2] - box[0], box[3] - box[1]
    s = max(1, min(BOX[0] // w, BOX[1] // h))
    return [f.crop(box).resize((w * s, h * s), Image.NEAREST) for f in frames]


def ripples(size, centre, t, colour):
    """Rings drift outward by one spacing per loop, fading in and out, so the
    last frame meets the first."""
    sub = 4
    mask = Image.new("L", (size[0] * sub, size[1] * sub), 0)
    d = ImageDraw.Draw(mask)
    for k in range(N_RINGS):
        u = (k + t) / N_RINGS
        r = (R_IN + u * (R_OUT - R_IN)) * sub
        cx, cy = centre[0] * sub, centre[1] * sub
        d.ellipse((cx - r, cy - r * SQUASH, cx + r, cy + r * SQUASH),
                  outline=round(PEAK * math.sin(math.pi * u)), width=2 * sub)
    layer = Image.new("RGBA", size, colour + (0,))
    layer.putalpha(mask.resize(size, Image.LANCZOS))
    return layer


def main():
    koi_path, assets, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    source = list(ImageSequence.Iterator(Image.open(koi_path)))
    durations = [f.info.get("duration", 70) for f in source]
    koi = enlarge([f.convert("RGBA") for f in source])
    for name, colour in RIPPLE.items():
        row = Image.open(assets / f"koi-{name}.png").convert("RGBA")
        centre = (round(row.width * KOI_X), row.height // 2)
        at = (centre[0] - koi[0].width // 2, centre[1] - koi[0].height // 2)
        frames = []
        for i, k in enumerate(koi):
            img = row.copy()
            img.alpha_composite(ripples(row.size, centre, i / len(koi), colour))
            img.alpha_composite(k, at)
            frames.append(img)
        frames[0].save(out / f"koi-{name}.webp", save_all=True, append_images=frames[1:],
                       duration=durations, loop=0, lossless=True, method=4)


if __name__ == "__main__":
    main()
