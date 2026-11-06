"""Draw the 1200x627 link-preview images (Open Graph cards) for dereknye.com.

Writes, with no embedded metadata:
  shots/share-site.png       general card (Home, Resume, projects, creative, freelance, data hub)
  shots/share-get-help.png   Get help page
  shots/share-brand-race.png Brand Race page; figures come from data/brand-race/summary.json
  shots/share-ai-adoption.png AI Adoption page; figures come from data/ai-adoption/summary.json
  shots/share-satellites.png Satellite Physics page; figures come from data/satellites/summary.json

Uses the site's own self-hosted fonts (Fraunces, Source Sans 3) and Field Notebook colors.
The Medicaid card is drawn separately by data/medicaid/make_share_card.py.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
SHOTS = ROOT / "shots"
W, H, M = 1200, 627, 64
S = 2  # draw at 2x, then downsample for smooth edges
BG, PANEL, LINE = (246, 243, 236), (255, 253, 248), (227, 220, 205)
INK, DIM, ACCENT, CLAY, OK = (31, 29, 26), (90, 85, 76), (47, 93, 80), (154, 91, 46), (46, 125, 50)
ORANGE = (194, 83, 28)
FACES = {"serif": "fraunces-var.woff2", "serif-italic": "fraunces-var-italic.woff2", "sans": "source-sans-3-var.woff2"}


def font(face, size, weight=400):
    f = ImageFont.truetype(str(FONTS / FACES[face]), size * S)
    # Fraunces axes are (optical size, weight); Source Sans 3 has weight only
    f.set_variation_by_axes([min(144, size), weight] if face.startswith("serif") else [weight])
    return f


def p(v):
    return v * S


def canvas():
    img = Image.new("RGB", (W * S, H * S), BG)
    return img, ImageDraw.Draw(img)


def footer(d, left, url, check=False):
    d.line([p(M), p(510), p(W - M), p(510)], fill=LINE, width=p(1))
    x = M
    if check:
        cx, cy, r = M + 11, 548, 11
        d.ellipse([p(cx - r), p(cy - r), p(cx + r), p(cy + r)], outline=OK, width=p(2))
        d.line([p(cx - 5), p(cy), p(cx - 1), p(cy + 4), p(cx + 6), p(cy - 4)], fill=OK, width=p(2), joint="curve")
        x = M + 34
    d.text((p(x), p(535)), left, font=font("sans", 20, 600), fill=INK)
    uf = font("sans", 19)
    d.text((p(W - M) - d.textlength(url, font=uf), p(536)), url, font=uf, fill=DIM)


def photo(img, d, x, y, size, round_=False):
    ph = Image.open(ROOT / "img" / "derek-nye.jpg").convert("RGB").resize((p(size), p(size)), Image.LANCZOS)
    if round_:
        mask = Image.new("L", ph.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, ph.size[0] - 1, ph.size[1] - 1], fill=255)
        img.paste(ph, (p(x), p(y)), mask)
    else:
        d.rectangle([p(x + 14), p(y + 14), p(x + size + 14), p(y + size + 14)], fill=(221, 211, 191))
        img.paste(ph, (p(x), p(y)))


def save(img, name):
    out = SHOTS / name
    img.resize((W, H), Image.LANCZOS).save(out, format="PNG", optimize=True)
    print(out)


def site_card():
    img, d = canvas()
    d.text((p(M), p(M - 4)), "DEREKNYE.COM", font=font("sans", 15, 700), fill=ACCENT)
    d.text((p(M), p(M + 28)), "Derek Nye", font=font("serif", 84, 650), fill=INK)
    sub = font("sans", 30)
    d.text((p(M), p(214)), "Computer and AI help,", font=sub, fill=INK)
    d.text((p(M), p(254)), "training and tools", font=sub, fill=INK)
    small = font("sans", 20)
    d.text((p(M), p(330)), "Teaching people new tools, especially AI", font=font("serif-italic", 22, 500), fill=CLAY)
    d.text((p(M), p(372)), "Registered Nurse  ·  MS, Data Science  ·  MBA", font=small, fill=DIM)
    photo(img, d, 802, 110, 320)
    footer(d, "Based in Middle Tennessee", "dereknye.com")
    save(img, "share-site.png")


def get_help_card():
    img, d = canvas()
    d.text((p(M), p(M - 4)), "COMPUTER AND AI HELP  ·  MIDDLE TENNESSEE", font=font("sans", 15, 700), fill=ACCENT)
    head = font("serif", 60, 650)
    d.text((p(M), p(M + 30)), "Technology doesn't", font=head, fill=INK)
    d.text((p(M), p(M + 100)), "have to feel", font=head, fill=INK)
    d.text((p(M), p(M + 170)), "intimidating.", font=font("serif-italic", 60, 650), fill=ACCENT)
    sub = font("sans", 23)
    d.text((p(M), p(338)), "One-on-one help by phone or video, at your pace.", font=sub, fill=DIM)
    d.text((p(M), p(370)), "For people, creators, and small businesses.", font=sub, fill=DIM)
    photo(img, d, 860, 120, 260, round_=True)
    footer(d, "Free 20-minute intro call", "dereknye.com/get-help", check=True)
    save(img, "share-get-help.png")


def brand_race_card():
    s = json.loads((ROOT / "data" / "brand-race" / "summary.json").read_text())
    ind = sorted([r for r in s["industry"] if r["view"] == "all"], key=lambda r: r["year"])
    a, b = ind[0], ind[-1]
    img, d = canvas()
    # chart panel on the right: industry-average 0 to 60 time at each snapshot
    cx0, cy0, cx1, cy1 = 640, 150, W - M, 470
    d.rounded_rectangle([p(cx0), p(cy0), p(cx1), p(cy1)], radius=p(14), fill=PANEL, outline=LINE, width=p(1))
    d.text((p(cx0 + 28), p(cy0 + 22)), "Average 0 to 60 time, all new vehicles", font=font("sans", 17, 600), fill=INK)
    px0, py0, px1, py1 = cx0 + 40, cy0 + 70, cx1 - 70, cy1 - 50
    hi, lo = max(r["zero60"] for r in ind) + 1, min(r["zero60"] for r in ind) - 1
    X = lambda y: px0 + (y - ind[0]["year"]) / (ind[-1]["year"] - ind[0]["year"]) * (px1 - px0)
    Y = lambda v: py0 + (hi - v) / (hi - lo) * (py1 - py0)
    d.line([p(px0), p(py1 + 14), p(px1), p(py1 + 14)], fill=(185, 176, 158), width=p(1))
    pts = [(X(r["year"]), Y(r["zero60"])) for r in ind]
    d.line([(p(x), p(y)) for x, y in pts], fill=ORANGE, width=p(3), joint="curve")
    for (x, y), r in zip(pts, ind):
        if r["preliminary"]:
            d.ellipse([p(x - 6), p(y - 6), p(x + 6), p(y + 6)], fill=PANEL, outline=ORANGE, width=p(2))
        else:
            d.ellipse([p(x - 5), p(y - 5), p(x + 5), p(y + 5)], fill=ORANGE)
    lab = font("sans", 18, 600)
    d.text((p(pts[0][0] + 14), p(pts[0][1] - 26)), f"{a['zero60']:.1f}s", font=lab, fill=INK)
    d.text((p(pts[-1][0] + 12), p(pts[-1][1] - 12)), f"{b['zero60']:.1f}s", font=lab, fill=INK)
    tick = font("sans", 14)
    d.text((p(px0 - 10), p(py1 + 24)), str(a["year"]), font=tick, fill=DIM)
    last = f"{b['year']} (prelim.)" if b["preliminary"] else str(b["year"])
    d.text((p(px1) - d.textlength(last, font=tick) + p(30), p(py1 + 24)), last, font=tick, fill=DIM)

    # left column
    d.text((p(M), p(M - 4)), "DATA ANALYSIS  ·  DEREK NYE", font=font("sans", 15, 700), fill=ACCENT)
    title = font("serif", 48, 650)
    d.text((p(M), p(M + 30)), "Brand Race,", font=title, fill=INK)
    d.text((p(M), p(M + 86)), f"{a['year']} to {b['year']}", font=title, fill=INK)
    d.text((p(M), p(262)), f"{a['zero60']:.1f}s to {b['zero60']:.1f}s", font=font("serif", 60, 650), fill=INK)
    sub = font("sans", 20)
    brands = len({r["brand"] for r in s["rows"]})
    d.text((p(M), p(338)), f"How {brands} automakers changed on 0 to 60 time,", font=sub, fill=DIM)
    d.text((p(M), p(364)), "horsepower, and fuel economy, from EPA data", font=sub, fill=DIM)
    footer(d, f"{len(s['checks'])} automated checks against EPA's raw file", "dereknye.com/brand-race", check=True)
    save(img, "share-brand-race.png")


def ai_adoption_card():
    s = json.loads((ROOT / "data" / "ai-adoption" / "summary.json").read_text(encoding="utf-8"))
    overall, inds = s["overall"], s["industries"]
    a, b = overall[0], overall[-1]
    # waves sit on a true time axis: Q1 was fielded in February, Q2 in May, and so on
    when = lambda w: int(w[3:]) + (int(w[1]) * 3 - 2) / 12
    img, d = canvas()
    # chart panel on the right: the 10 industries in gray, all employees in orange
    cx0, cy0, cx1, cy1 = 640, 110, W - M, 470
    d.rounded_rectangle([p(cx0), p(cy0), p(cx1), p(cy1)], radius=p(14), fill=PANEL, outline=LINE, width=p(1))
    d.text((p(cx0 + 28), p(cy0 + 22)), "Employees who use AI at work", font=font("sans", 17, 600), fill=INK)
    px0, py0, px1, py1 = cx0 + 40, cy0 + 66, cx1 - 142, cy1 - 56
    t0, t1 = when(a["wave"]), when(b["wave"])
    X = lambda w: px0 + (when(w) - t0) / (t1 - t0) * (px1 - px0)
    Y = lambda v: py1 - v / 100 * (py1 - py0)
    d.line([p(px0), p(py1 + 14), p(px1), p(py1 + 14)], fill=(185, 176, 158), width=p(1))
    for ind in inds:
        d.line([(p(X(r["wave"])), p(Y(r["total"]))) for r in ind["series"]], fill=(205, 198, 184), width=p(2), joint="curve")
    pts = [(X(r["wave"]), Y(r["total"])) for r in overall]
    d.line([(p(x), p(y)) for x, y in pts], fill=ORANGE, width=p(4), joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([p(x - 6), p(y - 6), p(x + 6), p(y + 6)], fill=ORANGE)
    lab, small = font("sans", 18, 600), font("sans", 16)
    d.text((p(pts[0][0] - 8), p(pts[0][1] + 12)), f"{a['total']}%", font=lab, fill=INK)
    d.text((p(pts[-1][0] + 12), p(pts[-1][1] - 13)), f"All {b['total']}%", font=lab, fill=INK)
    ranked = sorted(inds, key=lambda i: i["series"][-1]["total"])
    for ind in (ranked[-1], ranked[0]):
        last = ind["series"][-1]
        d.text((p(px1 + 12), p(Y(last["total"]) - 11)), f"{ind['name']} {last['total']}%", font=small, fill=DIM)
    tick = font("sans", 14)
    d.text((p(px0 - 10), p(py1 + 24)), "2023", font=tick, fill=DIM)
    d.text((p(px1) - d.textlength("2026", font=tick) + p(10), p(py1 + 24)), "2026", font=tick, fill=DIM)

    # left column
    d.text((p(M), p(M - 4)), "DATA ANALYSIS  ·  DEREK NYE", font=font("sans", 15, 700), fill=ACCENT)
    title = font("serif", 48, 650)
    d.text((p(M), p(M + 30)), "AI Adoption", font=title, fill=INK)
    d.text((p(M), p(M + 86)), "by Industry", font=title, fill=INK)
    d.text((p(M), p(262)), f"{a['total']}% to {b['total']}%", font=font("serif", 60, 650), fill=INK)
    sub = font("sans", 20)
    d.text((p(M), p(338)), "U.S. employees using AI at work at least a few", font=sub, fill=DIM)
    d.text((p(M), p(364)), f"times a year, 2023 to 2026, from Gallup data", font=sub, fill=DIM)
    footer(d, f"{len(s['checks'])} automated checks on the data", "dereknye.com/ai-adoption", check=True)
    save(img, "share-ai-adoption.png")


def satellites_card():
    import math
    s = json.loads((ROOT / "data" / "satellites" / "summary.json").read_text(encoding="utf-8"))
    g = {x["name"]: x for x in s["groups"]}
    c = s["constants"]
    ping = lambda h: 4 * h / c["c_kms"] * 1000
    img, d = canvas()
    # chart panel on the right: every drawn satellite's period against its altitude, on the physics curve
    cx0, cy0, cx1, cy1 = 620, 110, W - M, 470
    d.rounded_rectangle([p(cx0), p(cy0), p(cx1), p(cy1)], radius=p(14), fill=PANEL, outline=LINE, width=p(1))
    d.text((p(cx0 + 28), p(cy0 + 22)), "Hours per orbit against altitude", font=font("sans", 17, 600), fill=INK)
    px0, py0, px1, py1 = cx0 + 60, cy0 + 66, cx1 - 36, cy1 - 56
    lo, hi, ymax = 150, 100000, 50  # km (log), hours
    X = lambda h: px0 + (math.log10(h) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (px1 - px0)
    Y = lambda v: py1 - min(v, ymax) / ymax * (py1 - py0)
    tick = font("sans", 14)
    for v in (0, 12, 24, 36, 48):
        d.line([p(px0), p(Y(v)), p(px1), p(Y(v))], fill=(236, 230, 218), width=p(1))
        d.text((p(px0 - 10) - d.textlength(str(v), font=tick), p(Y(v) - 9)), str(v), font=tick, fill=DIM)
    for h, lab in ((200, "200"), (1000, "1,000"), (5000, "5,000"), (20000, "20,000"), (50000, "50,000")):
        d.text((p(X(h)) - d.textlength(lab, font=tick) / 2, p(py1 + 10)), lab, font=tick, fill=DIM)
    d.text((p(px1) - d.textlength("km above Earth (log scale)", font=tick), p(py1 + 30)), "km above Earth (log scale)", font=tick, fill=DIM)
    for alt, period, _ in s["points"]:
        x, y = X(alt), Y(period / 60)
        d.ellipse([p(x - 2.5), p(y - 2.5), p(x + 2.5), p(y + 2.5)], fill=(205, 198, 184))
    pts = [(p(X(r["alt"])), p(Y(r["period_min"] / 60))) for r in s["curve"] if lo <= r["alt"] <= hi and r["period_min"] / 60 <= ymax]
    d.line(pts, fill=ORANGE, width=p(3), joint="curve")
    lab = font("sans", 17, 600)
    for name, text, dx, dy in (("Starlink", "Starlink", 8, -34), ("Geostationary belt", "Geostationary", -150, -34)):
        x, y = X(g[name]["alt"]), Y(g[name]["period"] / 60)
        d.ellipse([p(x - 6), p(y - 6), p(x + 6), p(y + 6)], fill=ORANGE, outline=PANEL, width=p(2))
        d.text((p(x + dx), p(y + dy)), text, font=lab, fill=INK)

    # left column
    d.text((p(M), p(M - 4)), "DATA ANALYSIS  ·  DEREK NYE", font=font("sans", 15, 700), fill=ACCENT)
    title = font("serif", 48, 650)
    d.text((p(M), p(M + 30)), "Satellite", font=title, fill=INK)
    d.text((p(M), p(M + 86)), "Physics", font=title, fill=INK)
    d.text((p(M), p(262)), f"{ping(g['Starlink']['alt']):.0f} ms vs {ping(g['Geostationary belt']['alt']):.0f} ms", font=font("serif", 56, 650), fill=INK)
    sub = font("sans", 20)
    d.text((p(M), p(338)), "The shortest signal round trip in low orbit", font=sub, fill=DIM)
    d.text((p(M), p(364)), f"vs. the geostationary belt, from {s['total']:,} satellites", font=sub, fill=DIM)
    footer(d, f"{len(s['checks'])} automated checks on the data", "dereknye.com/satellites", check=True)
    save(img, "share-satellites.png")


if __name__ == "__main__":
    site_card()
    get_help_card()
    brand_race_card()
    ai_adoption_card()
    satellites_card()
