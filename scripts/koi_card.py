"""Swim the nightly koi onto the toolkit row in both themes.

python koi_card.py <koi.gif> <assets_dir> <out_dir>
Reads koi-{mocha,latte}.png that compose.py left in <assets_dir> and writes
<out_dir>/koi-{mocha,latte}.webp. Needs Pillow.
"""
import sys
from pathlib import Path

from PIL import Image, ImageSequence

KOI_X = 0.81  # under the particle in compose.py


def swim(koi, row):
    cx, cy = round(row.width * KOI_X), row.height // 2
    at = (cx - koi.width // 2, cy - koi.height // 2)
    frames, durations = [], []
    for frame in ImageSequence.Iterator(koi):
        img = row.copy()
        img.alpha_composite(frame.convert("RGBA"), at)
        frames.append(img)
        durations.append(frame.info.get("duration", 70))
    return frames, durations


def main():
    koi_path, assets, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    koi = Image.open(koi_path)
    for name in ("mocha", "latte"):
        frames, durations = swim(koi, Image.open(assets / f"koi-{name}.png").convert("RGBA"))
        frames[0].save(out / f"koi-{name}.webp", save_all=True, append_images=frames[1:],
                       duration=durations, loop=0, lossless=True, method=4)


if __name__ == "__main__":
    main()
