"""Draw the two profile rows on a transparent ground, in Catppuccin Mocha and
Latte text colours.

python compose.py <particle_frames_dir>
Writes assets/header-{mocha,latte}.webp, the header with the turning particle,
assets/koi-{mocha,latte}.png, the toolkit row that koi_card.py swims the koi
onto, and the link icons assets/icon-*-{mocha,latte}.png. Needs Pillow, Fira
Sans and JetBrains Mono Nerd Font.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FONTS = Path.home() / "Library" / "Fonts"

#==============================================================================#
# Design tokens, at twice the displayed size                                   #
#==============================================================================#

WIDTH = 1680
HEADER_H, TOOLKIT_H = 600, 512
PARTICLE = 640
FRAME_MS = 45
X0 = 4
ICON = 56

FLAVOURS = {
    "mocha": dict(text=(205, 214, 244), subtext=(166, 173, 200), overlay=(127, 132, 156),
                  accent=(180, 190, 254), chip=(49, 50, 68)),
    "latte": dict(text=(76, 79, 105), subtext=(108, 111, 133), overlay=(140, 143, 161),
                  accent=(114, 135, 253), chip=(230, 233, 239)),
}

FOCUS = (
    "Grand-canonical DFT in ONETEP and FHI-aims",
    "A direct ensemble minimiser for Quantum ESPRESSO",
    "Lithium nanoparticles under applied potential",
)
TOOLKIT = (
    ("Codes", ("ONETEP", "FHI-aims", "Quantum ESPRESSO", "VASP")),
    ("Languages", ("Fortran", "Python", "Rust", "Bash", "LaTeX")),
    ("Tools", ("Git", "Neovim", "Blender", "ASE")),
)
ICONS = {
    "email": "\U000f01f0",
    "orcid": "",
    "paper": "\U000f09ee",
    "koi": "\U000f023a",
}


def sans(weight, size):
    return ImageFont.truetype(str(FONTS / f"FiraSans-{weight}.ttf"), size)


def mono(size):
    return ImageFont.truetype(str(FONTS / "JetBrainsMonoNerdFontMono-Regular.ttf"), size)


#==============================================================================#
# Drawing on a transparent ground                                              #
#==============================================================================#

def paint(img, mask, colour):
    """Straight-alpha fill through a coverage mask, so edges keep their colour
    rather than fading through black."""
    layer = Image.new("RGBA", img.size, colour + (0,))
    layer.putalpha(mask)
    img.alpha_composite(layer)


def text(img, xy, s, fnt, colour, anchor="ls"):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text(xy, s, font=fnt, fill=255, anchor=anchor)
    paint(img, mask, colour)


def pill(img, box, colour, radius=12):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    big = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), radius * 4, fill=255)
    mask = Image.new("L", img.size, 0)
    mask.paste(big.resize((w, h), Image.LANCZOS), (x0, y0))
    paint(img, mask, colour)


#==============================================================================#
# Rows                                                                         #
#==============================================================================#

def header(frames_dir, c):
    base = Image.new("RGBA", (WIDTH, HEADER_H), (0, 0, 0, 0))
    text(base, (X0 - 4, 150), "Brad Ayers", sans("SemiBold", 104), c["text"])
    text(base, (X0, 214), "Electronic structure for electrochemistry", sans("Regular", 38), c["subtext"])
    for i, line in enumerate(FOCUS):
        y = 330 + 68 * i
        text(base, (X0, y), f"{i + 1:02d}", mono(26), c["accent"])
        text(base, (X0 + 62, y), line, sans("Regular", 34), c["text"])
    text(base, (X0, 568), "University of Southampton", sans("Regular", 28), c["overlay"])
    at = (WIDTH - PARTICLE, 0)
    out = []
    for path in sorted(Path(frames_dir).glob("frame_*.png")):
        img = base.copy()
        img.alpha_composite(Image.open(path).convert("RGBA").resize((PARTICLE, PARTICLE), Image.LANCZOS), at)
        out.append(img)
    return out


def toolkit(c):
    img = Image.new("RGBA", (WIDTH, TOOLKIT_H), (0, 0, 0, 0))
    font = mono(28)
    for i, (label, items) in enumerate(TOOLKIT):
        y = 120 + 100 * i
        text(img, (X0, y), label, sans("Regular", 30), c["overlay"], anchor="lm")
        x = 250
        for item in items:
            w = round(font.getlength(item)) + 44
            pill(img, (x, y - 30, x + w, y + 30), c["chip"])
            text(img, (x + w / 2, y), item, font, c["text"], anchor="mm")
            x += w + 14
    return img


def icon(glyph, c):
    """A link icon, its glyph scaled to fill most of the square."""
    path = str(FONTS / "JetBrainsMonoNerdFont-Regular.ttf")
    x0, y0, x1, y1 = ImageFont.truetype(path, 100).getbbox(glyph)
    fnt = ImageFont.truetype(path, round(100 * 0.82 * ICON / max(x1 - x0, y1 - y0)))
    x0, y0, x1, y1 = fnt.getbbox(glyph)
    img = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
    text(img, ((ICON - x1 - x0) / 2, (ICON - y1 - y0) / 2), glyph, fnt, c["subtext"], anchor="la")
    return img


def main():
    ASSETS.mkdir(exist_ok=True)
    for name, c in FLAVOURS.items():
        for key, glyph in ICONS.items():
            icon(glyph, c).save(ASSETS / f"icon-{key}-{name}.png")
        toolkit(c).save(ASSETS / f"koi-{name}.png")
        frames = header(sys.argv[1], c)
        frames[0].save(ASSETS / f"header-{name}.webp", save_all=True, append_images=frames[1:],
                       duration=FRAME_MS, loop=0, quality=84, method=6)


if __name__ == "__main__":
    main()
