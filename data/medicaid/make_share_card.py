"""Draw the 1200x627 link-preview image for the Data Analysis page.

Reads summary.json so the headline total and the trend line come from the same
numbers the page shows. Writes ../../shots/share-data-analysis.png with no
embedded metadata. Fonts: Segoe UI (Windows); pass other .ttf paths if needed.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "shots" / "share-data-analysis.png"
FONTS = Path("C:/Windows/Fonts")
W, H, M = 1200, 627, 64
BG, PANEL, LINE = (11, 11, 13), (20, 20, 23), (38, 38, 43)
INK, DIM, ACCENT, BLUE, MUTED, OK = (242, 242, 244), (154, 154, 164), (232, 72, 60), (57, 135, 229), (74, 74, 84), (12, 163, 12)
INCOMPLETE = {"2024-11", "2024-12"}
SCALE = 2  # draw at 2x, then downsample for smooth edges


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size * SCALE)


def main():
    s = json.loads((HERE / "summary.json").read_text())
    # Nov and Dec 2024 are incomplete (claims still arriving); the card stops at Oct 2024
    months = [m for m in s["monthly"] if m["month"] not in INCOMPLETE]
    total = s["quality"]["paid"]

    img = Image.new("RGB", (W * SCALE, H * SCALE), BG)
    d = ImageDraw.Draw(img)
    p = lambda v: v * SCALE

    # chart panel on the right
    cx0, cy0, cx1, cy1 = 640, 150, W - M, 470
    d.rounded_rectangle([p(cx0), p(cy0), p(cx1), p(cy1)], radius=p(14), fill=PANEL, outline=LINE, width=p(1))
    px0, py0, px1, py1 = cx0 + 28, cy0 + 56, cx1 - 28, cy1 - 44
    d.text((p(cx0 + 28), p(cy0 + 22)), "Total paid per month, Jan 2018 to Oct 2024", font=font("seguisb.ttf", 17), fill=INK)
    top = max(m["paid"] for m in months) * 1.08
    for g in range(4):
        y = py1 - (py1 - py0) * g / 3
        d.line([p(px0), p(y), p(px1), p(y)], fill=LINE if g else (58, 58, 66), width=p(1))
    n = len(months)
    pts = [(px0 + i * (px1 - px0) / (n - 1), py1 - m["paid"] / top * (py1 - py0)) for i, m in enumerate(months)]
    last_ok = n - 1
    fill = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(fill).polygon([(p(x), p(y)) for x, y in [(pts[0][0], py1)] + pts[:last_ok + 1] + [(pts[last_ok][0], py1)]], fill=BLUE + (28,))
    img.paste(fill, (0, 0), fill)
    d = ImageDraw.Draw(img)
    d.line([(p(x), p(y)) for x, y in pts[:last_ok + 1]], fill=BLUE, width=p(2), joint="curve")
    ex, ey = pts[last_ok]
    d.ellipse([p(ex - 6), p(ey - 6), p(ex + 6), p(ey + 6)], fill=PANEL)
    d.ellipse([p(ex - 4), p(ey - 4), p(ex + 4), p(ey + 4)], fill=BLUE)
    tick = font("segoeui.ttf", 14)
    for label, i in (("2018", 0), ("2021", 36), ("2024", 72)):
        x = pts[i][0]
        w = d.textlength(label, font=tick) / SCALE
        d.text((p(x - w / 2), p(py1 + 12)), label, font=tick, fill=DIM)

    # left column: kicker, title, headline figure
    d.text((p(M), p(M - 4)), "DATA ANALYSIS  \u00b7  DEREK NYE", font=font("seguisb.ttf", 15), fill=ACCENT)
    title = font("seguisb.ttf", 46)
    d.text((p(M), p(M + 30)), "Medicaid Provider", font=title, fill=INK)
    d.text((p(M), p(M + 86)), "Spending, 2018\u20132024", font=title, fill=INK)
    d.text((p(M), p(262)), f"${total / 1e12:.2f} trillion", font=font("seguisb.ttf", 58), fill=INK)
    sub = font("segoeui.ttf", 19)
    d.text((p(M), p(338)), "paid to providers, from 238 million rows", font=sub, fill=DIM)
    d.text((p(M), p(364)), "of public HHS data, charted and explained", font=sub, fill=DIM)

    # bottom strip: verification + address
    d.line([p(M), p(510), p(W - M), p(510)], fill=LINE, width=p(1))
    ccx, ccy, r = M + 11, 548, 11
    d.ellipse([p(ccx - r), p(ccy - r), p(ccx + r), p(ccy + r)], outline=OK, width=p(2))
    d.line([p(ccx - 5), p(ccy), p(ccx - 1), p(ccy + 4), p(ccx + 6), p(ccy - 4)], fill=OK, width=p(2), joint="curve")
    d.text((p(M + 34), p(535)), "Matches HHS\u2019s own published figures to the cent", font=font("seguisb.ttf", 20), fill=INK)
    url = "dereknye.com/data-analysis"
    uf = font("segoeui.ttf", 19)
    d.text((p(W - M) - d.textlength(url, font=uf), p(536)), url, font=uf, fill=DIM)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(OUT, format="PNG", optimize=True)
    print(OUT)


if __name__ == "__main__":
    main()
