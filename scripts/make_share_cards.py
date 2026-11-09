"""Draw the 1200x627 link-preview images (Open Graph cards) for dereknye.com.

Writes, with no embedded metadata:
  shots/share-site.png       general card (Home, Resume, projects, creative, freelance, data hub)
  shots/share-get-help.png   Get help page
  shots/share-brand-race.png Brand Race page; figures come from data/brand-race/summary.json
  shots/share-ai-adoption.png AI Adoption page; figures come from data/ai-adoption/summary.json
  shots/share-satellites.png Satellite Physics page; figures come from data/satellites/summary.json
  shots/share-anatomy-channel.png Anatomy and Physiology Educational Channel page; figures as written on the page

Uses the site's own self-hosted fonts (Fraunces, Source Sans 3) and dark-theme colors.
The Medicaid card is drawn separately by data/medicaid/make_share_card.py.

Sized for phones: a feed shows the card about 350 px wide (3.4x smaller), so no
text is drawn under 24 px, and the page address is left off because X and other
apps print the domain under the card themselves.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
SHOTS = ROOT / "shots"
W, H, M = 1200, 627, 56
S = 2  # draw at 2x, then downsample for smooth edges
# Colors: the site's dark theme (styles.css dark tokens), so every card matches dark mode
BG, PANEL, LINE = (26, 24, 22), (36, 32, 25), (58, 53, 46)
INK, DIM, ACCENT, CLAY, OK = (235, 229, 217), (177, 168, 153), (134, 196, 170), (217, 160, 108), (134, 196, 170)
ORANGE = (236, 128, 66)
FACES = {"serif": "fraunces-var.woff2", "serif-italic": "fraunces-var-italic.woff2", "sans": "source-sans-3-var.woff2"}
# Text sizes (px on the 1200 px card)
KICKER, SUB, FOOT, CHART_TITLE, CHART_LABEL, TICK = 26, 30, 30, 26, 28, 24
# Data cards: chart panel on the right, text column fills the space up to it
PANEL_BOX = (664, 92, W - M, 470)
COL_W = PANEL_BOX[0] - 24 - M


def font(face, size, weight=400):
    f = ImageFont.truetype(str(FONTS / FACES[face]), size * S)
    # Fraunces axes are (optical size, weight); Source Sans 3 has weight only
    f.set_variation_by_axes([min(144, size), weight] if face.startswith("serif") else [weight])
    return f


def p(v):
    return v * S


def width(d, text, f):
    return d.textlength(text, font=f) / S


def fit(d, face, size, weight, texts, maxw):
    """Largest font at or under `size` that keeps every line within maxw."""
    while size > 20:
        f = font(face, size, weight)
        if max(width(d, t, f) for t in texts) <= maxw:
            return f, size
        size -= 2
    return font(face, size, weight), size


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and width(d, trial, f) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


def canvas():
    img = Image.new("RGB", (W * S, H * S), BG)
    return img, ImageDraw.Draw(img)


def footer(d, text, check=False):
    d.line([p(M), p(500), p(W - M), p(500)], fill=LINE, width=p(1))
    x = M
    if check:
        cx, cy, r = M + 16, 547, 16
        d.ellipse([p(cx - r), p(cy - r), p(cx + r), p(cy + r)], outline=OK, width=p(3))
        d.line([p(cx - 7), p(cy), p(cx - 2), p(cy + 6), p(cx + 8), p(cy - 6)], fill=OK, width=p(3), joint="curve")
        x = M + 46
    f, _ = fit(d, "sans", FOOT, 600, [text], W - M - x)
    d.text((p(x), p(527)), text, font=f, fill=INK)


def photo(img, d, x, y, size, round_=False):
    ph = Image.open(ROOT / "img" / "derek-nye.jpg").convert("RGB").resize((p(size), p(size)), Image.LANCZOS)
    if round_:
        mask = Image.new("L", ph.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, ph.size[0] - 1, ph.size[1] - 1], fill=255)
        img.paste(ph, (p(x), p(y)), mask)
    else:
        d.rectangle([p(x + 14), p(y + 14), p(x + size + 14), p(y + size + 14)], fill=(58, 53, 46))
        img.paste(ph, (p(x), p(y)))


def save(img, name):
    out = SHOTS / name
    img.resize((W, H), Image.LANCZOS).save(out, format="PNG", optimize=True)
    print(out)


def panel(d, title):
    """Chart panel on the right with its title; returns the panel box."""
    cx0, cy0, cx1, cy1 = PANEL_BOX
    d.rounded_rectangle([p(cx0), p(cy0), p(cx1), p(cy1)], radius=p(14), fill=PANEL, outline=LINE, width=p(1))
    f, _ = fit(d, "sans", CHART_TITLE, 600, [title], cx1 - cx0 - 56)
    d.text((p(cx0 + 28), p(cy0 + 20)), title, font=f, fill=INK)
    return PANEL_BOX


def left_column(d, kicker, title_lines, figure, sub):
    """Kicker, two-line title, headline figure and a short supporting line."""
    d.text((p(M), p(44)), kicker, font=fit(d, "sans", KICKER, 700, [kicker], COL_W)[0], fill=ACCENT)
    tf, ts = fit(d, "serif", 60, 650, title_lines, COL_W)
    for i, line in enumerate(title_lines):
        d.text((p(M), p(84 + i * round(ts * 1.1))), line, font=tf, fill=INK)
    ff, _ = fit(d, "serif", 88, 650, [figure], COL_W)
    d.text((p(M), p(232)), figure, font=ff, fill=INK)
    sf = font("sans", SUB)
    lines = wrap(d, sub, sf, COL_W)
    assert len(lines) <= 2, f"supporting line too long for two lines: {sub!r}"
    for i, line in enumerate(lines):
        d.text((p(M), p(360 + i * 38)), line, font=sf, fill=DIM)


def site_card():
    img, d = canvas()
    d.text((p(M), p(44)), "DEREKNYE.COM", font=font("sans", KICKER, 700), fill=ACCENT)
    d.text((p(M), p(74)), "Derek Nye", font=font("serif", 104, 650), fill=INK)
    sub = font("sans", 40)
    d.text((p(M), p(216)), "Computer and AI help,", font=sub, fill=INK)
    d.text((p(M), p(266)), "training and tools", font=sub, fill=INK)
    d.text((p(M), p(340)), "Teaching people new tools, especially AI", font=font("serif-italic", 32, 500), fill=CLAY)
    d.text((p(M), p(398)), "Registered Nurse  ·  MS, Data Science  ·  MBA", font=font("sans", 28), fill=DIM)
    photo(img, d, 750, 84, 380)
    footer(d, "Based in Middle Tennessee")
    save(img, "share-site.png")


def get_help_card():
    img, d = canvas()
    d.text((p(M), p(44)), "COMPUTER AND AI HELP  ·  MIDDLE TENNESSEE", font=font("sans", KICKER, 700), fill=ACCENT)
    head = font("serif", 72, 650)
    d.text((p(M), p(84)), "Technology doesn't", font=head, fill=INK)
    d.text((p(M), p(164)), "have to feel", font=head, fill=INK)
    d.text((p(M), p(244)), "intimidating.", font=font("serif-italic", 72, 650), fill=ACCENT)
    sub = font("sans", SUB)
    d.text((p(M), p(366)), "One-on-one help by phone or video, at your pace.", font=sub, fill=DIM)
    d.text((p(M), p(406)), "For people, creators, and small businesses.", font=sub, fill=DIM)
    photo(img, d, 814, 96, 330, round_=True)
    footer(d, "Free 20-minute intro call", check=True)
    save(img, "share-get-help.png")


def brand_race_card():
    s = json.loads((ROOT / "data" / "brand-race" / "summary.json").read_text())
    ind = sorted([r for r in s["industry"] if r["view"] == "all"], key=lambda r: r["year"])
    a, b = ind[0], ind[-1]
    img, d = canvas()
    # chart panel on the right: industry-average 0 to 60 time at each snapshot
    cx0, cy0, cx1, cy1 = panel(d, "Average 0 to 60 time")
    px0, py0, px1, py1 = cx0 + 44, cy0 + 112, cx1 - 112, cy1 - 78
    hi, lo = max(r["zero60"] for r in ind) + 1, min(r["zero60"] for r in ind) - 1
    X = lambda y: px0 + (y - ind[0]["year"]) / (ind[-1]["year"] - ind[0]["year"]) * (px1 - px0)
    Y = lambda v: py0 + (hi - v) / (hi - lo) * (py1 - py0)
    d.line([p(px0), p(py1 + 14), p(px1), p(py1 + 14)], fill=(92, 85, 74), width=p(1))
    pts = [(X(r["year"]), Y(r["zero60"])) for r in ind]
    d.line([(p(x), p(y)) for x, y in pts], fill=ORANGE, width=p(4), joint="curve")
    for (x, y), r in zip(pts, ind):
        if r["preliminary"]:
            d.ellipse([p(x - 8), p(y - 8), p(x + 8), p(y + 8)], fill=PANEL, outline=ORANGE, width=p(3))
        else:
            d.ellipse([p(x - 7), p(y - 7), p(x + 7), p(y + 7)], fill=ORANGE)
    lab = font("sans", CHART_LABEL, 600)
    d.text((p(pts[0][0] + 18), p(pts[0][1] - 34)), f"{a['zero60']:.1f}s", font=lab, fill=INK)
    d.text((p(pts[-1][0] + 16), p(pts[-1][1] - 19)), f"{b['zero60']:.1f}s", font=lab, fill=INK)
    tick = font("sans", TICK)
    d.text((p(px0 - 10), p(py1 + 26)), str(a["year"]), font=tick, fill=DIM)
    last = str(b["year"])
    d.text((p(px1 + 30 - width(d, last, tick)), p(py1 + 26)), last, font=tick, fill=DIM)

    brands = len({r["brand"] for r in s["rows"]})
    left_column(d, "DATA ANALYSIS  ·  DEREK NYE", ["Brand Race,", f"{a['year']} to {b['year']}"],
                f"{a['zero60']:.1f}s to {b['zero60']:.1f}s",
                f"How {brands} automakers changed on speed, power and fuel economy")
    footer(d, f"{len(s['checks'])} automated checks against EPA's raw file", check=True)
    save(img, "share-brand-race.png")


def ai_adoption_card():
    s = json.loads((ROOT / "data" / "ai-adoption" / "summary.json").read_text(encoding="utf-8"))
    overall, inds = s["overall"], s["industries"]
    a, b = overall[0], overall[-1]
    # waves sit on a true time axis: Q1 was fielded in February, Q2 in May, and so on
    when = lambda w: int(w[3:]) + (int(w[1]) * 3 - 2) / 12
    img, d = canvas()
    # chart panel on the right: the 10 industries in gray, all employees in orange
    cx0, cy0, cx1, cy1 = panel(d, "Employees using AI at work")
    px0, py0, px1, py1 = cx0 + 44, cy0 + 76, cx1 - 104, cy1 - 78
    t0, t1 = when(a["wave"]), when(b["wave"])
    X = lambda w: px0 + (when(w) - t0) / (t1 - t0) * (px1 - px0)
    Y = lambda v: py1 - v / 100 * (py1 - py0)
    d.line([p(px0), p(py1 + 14), p(px1), p(py1 + 14)], fill=(92, 85, 74), width=p(1))
    for ind in inds:
        d.line([(p(X(r["wave"])), p(Y(r["total"]))) for r in ind["series"]], fill=(84, 78, 68), width=p(2), joint="curve")
    pts = [(X(r["wave"]), Y(r["total"])) for r in overall]
    d.line([(p(x), p(y)) for x, y in pts], fill=ORANGE, width=p(5), joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([p(x - 8), p(y - 8), p(x + 8), p(y + 8)], fill=ORANGE)
    lab = font("sans", CHART_LABEL, 600)
    d.text((p(pts[0][0] - 8), p(pts[0][1] + 12)), f"{a['total']}%", font=lab, fill=INK)
    d.text((p(pts[-1][0] + 16), p(pts[-1][1] - 19)), f"{b['total']}%", font=lab, fill=INK)
    tick = font("sans", TICK)
    d.text((p(px0 - 10), p(py1 + 26)), "2023", font=tick, fill=DIM)
    d.text((p(px1 + 10 - width(d, "2026", tick)), p(py1 + 26)), "2026", font=tick, fill=DIM)

    left_column(d, "DATA ANALYSIS  ·  DEREK NYE", ["AI Adoption", "by Industry"],
                f"{a['total']}% to {b['total']}%",
                "U.S. employees using AI at work, 2023 to 2026, from Gallup data")
    footer(d, f"{len(s['checks'])} automated checks on the data", check=True)
    save(img, "share-ai-adoption.png")


def satellites_card():
    import math
    s = json.loads((ROOT / "data" / "satellites" / "summary.json").read_text(encoding="utf-8"))
    g = {x["name"]: x for x in s["groups"]}
    c = s["constants"]
    ping = lambda h: 4 * h / c["c_kms"] * 1000
    img, d = canvas()
    # chart panel on the right: every drawn satellite's period against its altitude, on the physics curve
    cx0, cy0, cx1, cy1 = panel(d, "Hours per orbit, by altitude")
    px0, py0, px1, py1 = cx0 + 32, cy0 + 84, cx1 - 32, cy1 - 36
    lo, hi, ymax = 150, 100000, 50  # km (log), hours
    X = lambda h: px0 + (math.log10(h) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (px1 - px0)
    Y = lambda v: py1 - min(v, ymax) / ymax * (py1 - py0)
    for v in (0, 12, 24, 36, 48):
        d.line([p(px0), p(Y(v)), p(px1), p(Y(v))], fill=(46, 42, 36), width=p(1))
    for alt, period, _ in s["points"]:
        x, y = X(alt), Y(period / 60)
        d.ellipse([p(x - 2.5), p(y - 2.5), p(x + 2.5), p(y + 2.5)], fill=(84, 78, 68))
    pts = [(p(X(r["alt"])), p(Y(r["period_min"] / 60))) for r in s["curve"] if lo <= r["alt"] <= hi and r["period_min"] / 60 <= ymax]
    d.line(pts, fill=ORANGE, width=p(4), joint="curve")
    lab = font("sans", CHART_LABEL, 600)
    for name, text, side in (("Starlink", "Starlink", "right"), ("Geostationary belt", "Geostationary", "left")):
        x, y = X(g[name]["alt"]), Y(g[name]["period"] / 60)
        d.ellipse([p(x - 8), p(y - 8), p(x + 8), p(y + 8)], fill=ORANGE, outline=PANEL, width=p(2))
        tx = x + 10 if side == "right" else x - 12 - width(d, text, lab)
        d.text((p(tx), p(y - 48)), text, font=lab, fill=INK)

    left_column(d, "DATA ANALYSIS  ·  DEREK NYE", ["Satellite", "Physics"],
                f"{ping(g['Starlink']['alt']):.0f} ms vs {ping(g['Geostationary belt']['alt']):.0f} ms",
                "Signal round trip: low orbit vs. the geostationary belt")
    footer(d, f"{len(s['checks'])} automated checks on {s['total']:,} satellites", check=True)
    save(img, "share-satellites.png")


def anatomy_channel_card():
    # figures as written on anatomy-channel.html (YouTube view counts, October 19, 2026)
    img, d = canvas()
    # poster panel on the right: the channel's most-watched lesson
    cx0, cy0, cx1, cy1 = panel(d, "Top lesson: 124,000+ views")
    pw = cx1 - cx0 - 56
    ph = round(pw * 9 / 16)
    px, py = cx0 + 28, cy1 - 28 - ph
    poster = Image.open(ROOT / "posters" / "ditw-anatomy-physiology.jpg").convert("RGB").resize((p(pw), p(ph)), Image.LANCZOS)
    mask = Image.new("L", poster.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, poster.size[0] - 1, poster.size[1] - 1], radius=p(8), fill=255)
    img.paste(poster, (p(px), p(py)), mask)

    left_column(d, "DITW ON YOUTUBE  ·  DEREK NYE", ["Anatomy and Physiology", "Educational Channel"],
                "400,000+ views",
                "73 short, plain lessons for nursing and health students")
    footer(d, "Lessons since 2017, and still active")
    save(img, "share-anatomy-channel.png")


if __name__ == "__main__":
    site_card()
    get_help_card()
    brand_race_card()
    ai_adoption_card()
    satellites_card()
    anatomy_channel_card()
