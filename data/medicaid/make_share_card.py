"""Draw the 1200x627 link-preview image for the Data Analysis page.

Reads summary.json so the headline total and the trend line come from the same
numbers the page shows. Writes ../../shots/share-data-analysis.png with no
embedded metadata. Uses the site's own self-hosted fonts (Fraunces, Source Sans 3)
and dark-theme colors.

Sized for phones like the other cards (see scripts/make_share_cards.py): no text
under 24 px, and no page address, since apps print the domain under the card.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "shots" / "share-data-analysis.png"
FONTS = HERE.parent.parent / "fonts"
W, H, M = 1200, 627, 56
# Colors: the site's dark theme (styles.css dark tokens), so every card matches dark mode
BG, PANEL, LINE = (26, 24, 22), (36, 32, 25), (58, 53, 46)
INK, DIM, ACCENT, BLUE, MUTED, OK = (235, 229, 217), (177, 168, 153), (134, 196, 170), (122, 168, 232), (84, 78, 68), (134, 196, 170)
INCOMPLETE = {"2024-11", "2024-12"}
SCALE = 2  # draw at 2x, then downsample for smooth edges
PANEL_BOX = (664, 92, W - M, 470)
COL_W = PANEL_BOX[0] - 24 - M


FACES = {"serif": "fraunces-var.woff2", "sans": "source-sans-3-var.woff2"}


def font(face, size, weight=400):
    f = ImageFont.truetype(str(FONTS / FACES[face]), size * SCALE)
    # Fraunces axes are (optical size, weight); Source Sans 3 has weight only
    f.set_variation_by_axes([min(144, size), weight] if face == "serif" else [weight])
    return f


def width(d, text, f):
    return d.textlength(text, font=f) / SCALE


def fit(d, face, size, weight, texts, maxw):
    """Largest font at or under `size` that keeps every line within maxw."""
    while size > 20:
        f = font(face, size, weight)
        if max(width(d, t, f) for t in texts) <= maxw:
            return f, size
        size -= 2
    return font(face, size, weight), size


def main():
    s = json.loads((HERE / "summary.json").read_text())
    # Nov and Dec 2024 are incomplete (claims still arriving); the card stops at Oct 2024
    months = [m for m in s["monthly"] if m["month"] not in INCOMPLETE]
    total = s["quality"]["paid"]

    img = Image.new("RGB", (W * SCALE, H * SCALE), BG)
    d = ImageDraw.Draw(img)
    p = lambda v: v * SCALE

    # chart panel on the right
    cx0, cy0, cx1, cy1 = PANEL_BOX
    d.rounded_rectangle([p(cx0), p(cy0), p(cx1), p(cy1)], radius=p(14), fill=PANEL, outline=LINE, width=p(1))
    px0, py0, px1, py1 = cx0 + 28, cy0 + 84, cx1 - 28, cy1 - 62
    ctitle = "Total paid per month"
    d.text((p(cx0 + 28), p(cy0 + 20)), ctitle, font=fit(d, "sans", 26, 600, [ctitle], cx1 - cx0 - 56)[0], fill=INK)
    top = max(m["paid"] for m in months) * 1.08
    for g in range(4):
        y = py1 - (py1 - py0) * g / 3
        d.line([p(px0), p(y), p(px1), p(y)], fill=LINE if g else (92, 85, 74), width=p(1))
    n = len(months)
    pts = [(px0 + i * (px1 - px0) / (n - 1), py1 - m["paid"] / top * (py1 - py0)) for i, m in enumerate(months)]
    last_ok = n - 1
    fill = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(fill).polygon([(p(x), p(y)) for x, y in [(pts[0][0], py1)] + pts[:last_ok + 1] + [(pts[last_ok][0], py1)]], fill=BLUE + (22,))
    img.paste(fill, (0, 0), fill)
    d = ImageDraw.Draw(img)
    d.line([(p(x), p(y)) for x, y in pts[:last_ok + 1]], fill=BLUE, width=p(3), joint="curve")
    ex, ey = pts[last_ok]
    d.ellipse([p(ex - 9), p(ey - 9), p(ex + 9), p(ey + 9)], fill=PANEL)
    d.ellipse([p(ex - 6), p(ey - 6), p(ex + 6), p(ey + 6)], fill=BLUE)
    tick = font("sans", 24)
    for label, i, align in (("2018", 0, 0), ("2021", 36, 0.5), ("2024", 72, 1)):
        d.text((p(pts[i][0] - width(d, label, tick) * align), p(py1 + 14)), label, font=tick, fill=DIM)

    # left column: kicker, title, headline figure, supporting line
    d.text((p(M), p(44)), "DATA ANALYSIS  ·  DEREK NYE", font=font("sans", 26, 700), fill=ACCENT)
    title_lines = ["Medicaid Provider", "Spending, 2018–2024"]
    tf, ts = fit(d, "serif", 60, 650, title_lines, COL_W)
    for i, line in enumerate(title_lines):
        d.text((p(M), p(84 + i * round(ts * 1.1))), line, font=tf, fill=INK)
    figure = f"${total / 1e12:.2f} trillion"
    d.text((p(M), p(232)), figure, font=fit(d, "serif", 88, 650, [figure], COL_W)[0], fill=INK)
    sub = font("sans", 30)
    d.text((p(M), p(360)), "paid to providers, from 238 million", font=sub, fill=DIM)
    d.text((p(M), p(398)), "rows of public HHS data", font=sub, fill=DIM)

    # bottom strip: verification
    d.line([p(M), p(500), p(W - M), p(500)], fill=LINE, width=p(1))
    ccx, ccy, r = M + 16, 547, 16
    d.ellipse([p(ccx - r), p(ccy - r), p(ccx + r), p(ccy + r)], outline=OK, width=p(3))
    d.line([p(ccx - 7), p(ccy), p(ccx - 2), p(ccy + 6), p(ccx + 8), p(ccy - 6)], fill=OK, width=p(3), joint="curve")
    foot = "Matches HHS’s own published figures to the cent"
    d.text((p(M + 46), p(527)), foot, font=fit(d, "sans", 30, 600, [foot], W - 2 * M - 46)[0], fill=INK)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(OUT, format="PNG", optimize=True)
    print(OUT)


if __name__ == "__main__":
    main()
