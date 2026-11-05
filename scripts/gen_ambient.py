"""Generate the three ambient header scenes as inline SVG and insert them into the data pages."""
import math, random, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H = 1200, 180

def wrap(cls, body):
    return (f'<div class="ambient {cls}" aria-hidden="true">'
            f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" focusable="false">'
            f'{body}</svg></div>')

# ---------------------------------------------------------------- Medicaid: monitor trace
def ecg():
    rnd = random.Random(7)
    # one beat is 300 wide, baseline y=84
    beat = ("M0 84 L62 84 Q72 72 82 84 L112 84 L118 91 L126 30 L134 106 L140 84 "
            "L184 84 Q198 66 212 84 L300 84")
    d = []
    for i in range(4):
        d.append(beat if i == 0 else beat.replace("M0 84", f"M{i*300} 84").replace("L", "L"))
    # absolute coords: shift each beat by i*300
    parts = []
    for i in range(4):
        seg = re.sub(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)",
                     lambda m: f"{float(m.group(1))+i*300:g} {m.group(2)}", beat)
        parts.append(seg if i == 0 else seg.replace("M", "L", 1))
    trace = " ".join(parts)
    # 75 faint bars, slow upward trend with noise, bottoms on the ground
    bars = []
    for i in range(75):
        h = 22 + i * 0.5 + rnd.uniform(-9, 9) + 8 * math.sin(i / 6)
        x = i * 16 + 3
        bars.append(f"M{x} {H}v{-h:.0f}h9v{h:.0f}z")
    body = (
        '<defs><pattern id="amb-grid" width="24" height="24" patternUnits="userSpaceOnUse">'
        '<path d="M24 0H0V24" fill="none" stroke="currentColor" stroke-width="1"/></pattern>'
        '<pattern id="amb-grid2" width="120" height="120" patternUnits="userSpaceOnUse">'
        '<path d="M120 0H0V120" fill="none" stroke="currentColor" stroke-width="1"/></pattern>'
        f'<path id="amb-bars" d="{"".join(bars)}"/>'
        f'<path id="amb-beat" d="{trace}"/></defs>'
        f'<rect width="{W}" height="{H}" fill="url(#amb-grid)" opacity=".09"/>'
        f'<rect width="{W}" height="{H}" fill="url(#amb-grid2)" opacity=".12"/>'
        '<g class="amb-slow" fill="currentColor" opacity=".13">'
        '<use href="#amb-bars"/><use href="#amb-bars" x="1200"/></g>'
        '<g class="amb-scroll" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linejoin="round" stroke-linecap="round" opacity=".85">'
        '<use href="#amb-beat"/><use href="#amb-beat" x="1200"/></g>'
    )
    return wrap("sc-ecg", body)

# ---------------------------------------------------------------- Brand Race: the road
CARS = {
    "sedan": dict(body="M0-7V-16L12-18 22-32H50L62-19 78-16Q82-15 82-10V-7Z",
                  glass="M24-30H48L58-19H18Z", wheels=(16, 64)),
    "coupe": dict(body="M0-7V-13L16-15 30-27H56L70-16 86-13Q90-12 90-9V-7Z",
                  glass="M32-25H54L64-16H24Z", wheels=(18, 70)),
    "suv":   dict(body="M0-7V-20L8-21 14-36H46L50-21 76-20Q80-19 80-12V-7Z",
                  glass="M16-34H28V-22H10ZM31-34H44L47-22H31Z", wheels=(16, 62)),
    "wagon": dict(body="M0-7V-19L6-21 14-32H48L60-19 74-17Q78-16 78-10V-7Z",
                  glass="M16-30H30V-20H10ZM33-30H46L56-20H33Z", wheels=(14, 60)),
}

def car(kind, x, dur, delay):
    c = CARS[kind]
    wheels = "".join(
        f'<g transform="translate({wx} -7)"><circle r="7" fill="var(--bg)"/>'
        f'<g class="amb-spin"><path d="M-7 0H7M0-7V7" stroke-width="1"/></g></g>'
        for wx in c["wheels"])
    return (f'<g transform="translate({x} 176)"><g class="amb-sway" style="animation-duration:{dur}s;animation-delay:{delay}s">'
            f'<path d="{c["body"]}" fill="var(--bg)"/><path d="{c["glass"]}" stroke-width="1"/>{wheels}</g></g>')

def hills():
    # far ridge: seamless over 1200 (all terms have whole periods), sampled into a polyline
    pts = []
    for i in range(0, 1201, 15):
        t = 2 * math.pi * i / 1200
        y = 112 - 26 * math.sin(t + .6) - 13 * math.sin(2 * t + 1.9) - 6 * math.sin(3 * t + 4.1) - 4 * math.sin(5 * t)
        pts.append(f"{i} {y:.1f}")
    far = "M" + "L".join(pts) + "V146H0Z"
    # near treeline: rounded tree crowns of varied size, ending where it starts
    rnd = random.Random(11)
    x, d = 0, ["M0 146V134"]
    while x < 1200:
        w = rnd.choice((22, 28, 34, 40)); h = rnd.uniform(9, 20)
        if x + w > 1200: w = 1200 - x
        d.append(f"Q{x+w/4:.0f} {134-h:.0f} {x+w/2:.0f} {134-h:.0f}Q{x+3*w/4:.0f} {134-h:.0f} {x+w} 134")
        x += w
    near = "".join(d) + "V146Z"
    return far, near

def road():
    far, near = hills()
    cyp = "".join(f'<path d="M{x} 146 L{x+3} {146-h} L{x+6} 146Z"/>' for x, h in
                  ((150, 30), (158, 24), (430, 34), (437, 22), (715, 28), (1010, 36), (1017, 26)))
    cloud = ('<path d="M0 0c-2-12 10-20 22-14 4-10 20-12 28-2 10-4 20 4 18 12 6 0 10 6 8 10H2C-2 8-2 2 0 0Z"/>')
    body = (
        f'<defs><path id="amb-far" d="{far}"/><path id="amb-near" d="{near}"/>'
        f'<g id="amb-cyp">{cyp}</g><g id="amb-cloud">{cloud}</g></defs>'
        '<g class="amb-drift" fill="var(--bg)" stroke="currentColor" stroke-width="1" opacity=".45">'
        '<use href="#amb-cloud" x="160" y="46"/><use href="#amb-cloud" x="620" y="22"/>'
        '<use href="#amb-cloud" x="980" y="54"/><use href="#amb-cloud" x="1360" y="46"/>'
        '<use href="#amb-cloud" x="1820" y="28"/><use href="#amb-cloud" x="2180" y="54"/></g>'
        '<g class="amb-slower" fill="currentColor" fill-opacity=".07" stroke="currentColor" stroke-width="1" opacity=".55">'
        '<use href="#amb-far"/><use href="#amb-far" x="1200"/></g>'
        '<g class="amb-slow" fill="currentColor" fill-opacity=".1" stroke="currentColor" stroke-width="1" stroke-linejoin="round" opacity=".7">'
        '<use href="#amb-near"/><use href="#amb-near" x="1200"/><use href="#amb-cyp"/><use href="#amb-cyp" x="1200"/></g>'
        '<path d="M0 146H1200" stroke="currentColor" stroke-width="1" opacity=".5"/>'
        '<path class="amb-lane" d="M0 160H1200" stroke="currentColor" stroke-width="1.5" stroke-dasharray="34 30" opacity=".45"/>'
        '<g fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round">'
        + car("coupe", 130, 29, -4) + car("sedan", 400, 23, -15) + car("suv", 690, 36, -9) + car("wagon", 960, 27, -21)
        + '</g>'
    )
    return wrap("sc-road", body)

# ---------------------------------------------------------------- AI Adoption: signals over industries
def windows(rnd, x0, top, cols, rows, w=7, h=9, cx=15, cy=13, pad=9):
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append(f'<rect class="amb-win" x="{x0+pad+c*cx}" y="{top+pad+r*cy}" width="{w}" height="{h}" '
                       f'style="--d:-{rnd.uniform(0,14):.1f}s;--p:{rnd.uniform(8,15):.1f}s"/>')
    return "".join(out)

def net():
    rnd = random.Random(3)
    G = H  # ground
    b = []   # building outlines (stroke)
    w = []   # windows
    # tower (tech)
    x = 20; b.append(f'<rect x="{x}" y="{G-120}" width="70" height="120"/>'); w.append(windows(rnd, x, G-120, 4, 8))
    # hospital
    x = 120; b.append(f'<rect x="{x}" y="{G-58}" width="110" height="58"/><rect x="{x+38}" y="{G-80}" width="34" height="22"/>'
                      f'<path d="M{x+55} {G-75}v12M{x+49} {G-69}h12"/>'); w.append(windows(rnd, x, G-58, 6, 3, cx=16, cy=15, pad=10))
    # factory with chimney
    x = 262; b.append(f'<path d="M{x} {G}V{G-48}L{x} {G-70}L{x+30} {G-48}L{x+30} {G-70}L{x+60} {G-48}L{x+60} {G-70}L{x+90} {G-48}L{x+90} {G-70}L{x+120} {G-48}V{G}Z"/>'
                      f'<rect x="{x+100}" y="{G-96}" width="9" height="30"/>')
    w.append(windows(rnd, x, G-48, 7, 2, cx=16, cy=16, pad=10, w=9, h=8))
    smoke = "".join(f'<circle class="amb-smoke" cx="{x+104.5}" cy="{G-100}" r="{r}" style="animation-delay:-{d}s"/>'
                    for r, d in ((3, 0), (3.5, 2.5), (3, 5)))
    # retail with awning
    x = 412; b.append(f'<rect x="{x}" y="{G-44}" width="90" height="44"/>'
                      f'<path d="M{x-4} {G-44}' + "".join("a5 5 0 0 0 10 0" for _ in range(9)) + '"/>'
                      f'<rect x="{x+14}" y="{G-30}" width="26" height="22"/><rect x="{x+50}" y="{G-30}" width="26" height="22"/>')
    w.append(f'<rect class="amb-win" x="{x+16}" y="{G-28}" width="22" height="18" style="--d:-3s;--p:11s"/>'
             f'<rect class="amb-win" x="{x+52}" y="{G-28}" width="22" height="18" style="--d:-9s;--p:13s"/>')
    # school with gable and bell tower
    x = 532; b.append(f'<rect x="{x}" y="{G-56}" width="100" height="56"/><path d="M{x-2} {G-56}L{x+50} {G-84}L{x+102} {G-56}"/>'
                      f'<path d="M{x+42} {G-80}V{G-98}H{x+58}V{G-80}M{x+42} {G-98}L{x+50} {G-108}L{x+58} {G-98}"/>')
    w.append(windows(rnd, x, G-56, 5, 3, cx=17, cy=15, pad=11))
    # bank with columns and pediment
    x = 662; b.append(f'<rect x="{x}" y="{G-64}" width="100" height="64"/><path d="M{x-4} {G-64}L{x+50} {G-86}L{x+104} {G-64}"/>'
                      + "".join(f'<path d="M{x+14+i*18} {G-58}V{G-8}"/>' for i in range(5)))
    w.append(windows(rnd, x+2, G-64, 4, 1, cx=18, cy=14, pad=21, w=10, h=24))
    # government dome
    x = 792; b.append(f'<rect x="{x}" y="{G-60}" width="110" height="60"/><path d="M{x+30} {G-60}A25 25 0 0 1 {x+80} {G-60}"/>'
                      f'<path d="M{x+55} {G-85}V{G-96}"/>')
    w.append(windows(rnd, x, G-60, 6, 3, cx=16, cy=15, pad=11))
    # warehouse with barrel roof and door
    x = 932; b.append(f'<path d="M{x} {G}V{G-50}A55 30 0 0 1 {x+110} {G-50}V{G}Z"/><rect x="{x+38}" y="{G-34}" width="34" height="34"/>'
                      f'<path d="M{x+38} {G-24}H{x+72}M{x+38} {G-14}H{x+72}"/>')
    w.append(windows(rnd, x, G-50, 2, 1, cx=84, cy=0, pad=12, w=14, h=10))
    # mid tower
    x = 1072; b.append(f'<rect x="{x}" y="{G-90}" width="60" height="90"/>'); w.append(windows(rnd, x, G-90, 3, 6, cx=16, cy=13, pad=9))
    # small tower at the edge
    x = 1150; b.append(f'<rect x="{x}" y="{G-70}" width="56" height="70"/>'); w.append(windows(rnd, x, G-70, 3, 4, cx=16, cy=14, pad=8))

    nodes = [(60, 46), (170, 22), (300, 60), (430, 26), (545, 62), (665, 20), (790, 56),
             (905, 24), (1020, 62), (1125, 28), (1190, 64)]
    edges = [(0, 1), (1, 2), (1, 3), (0, 2), (2, 3), (2, 4), (3, 5), (3, 4), (4, 5), (4, 6), (5, 6), (5, 7),
             (6, 7), (6, 8), (7, 9), (7, 8), (8, 9), (8, 10), (9, 10)]
    # drop lines from nodes to roofs
    drops = [(0, 55, G-120), (2, 300, G-70), (4, 545, G-108), (6, 790+55, G-96), (8, 1020, G-80), (10, 1102, G-90)]
    base, pk, nd = [], [], []
    for a, c in edges:
        (x1, y1), (x2, y2) = nodes[a], nodes[c]
        base.append(f'<path d="M{x1} {y1}L{x2} {y2}"/>')
        pk.append(f'<path d="M{x1} {y1}L{x2} {y2}" pathLength="100" class="amb-pkt" '
                  f'style="animation-duration:{rnd.uniform(7,14):.1f}s;animation-delay:-{rnd.uniform(0,14):.1f}s"/>')
    for n, x2, y2 in drops:
        x1, y1 = nodes[n]
        base.append(f'<path d="M{x1} {y1}L{x2} {y2}" stroke-dasharray="2 4"/>')
        pk.append(f'<path d="M{x1} {y1}L{x2} {y2}" pathLength="100" class="amb-pkt" '
                  f'style="animation-duration:{rnd.uniform(9,16):.1f}s;animation-delay:-{rnd.uniform(0,14):.1f}s"/>')
    for i, (x1, y1) in enumerate(nodes):
        nd.append(f'<g transform="translate({x1} {y1})"><circle class="amb-ring" r="8" style="animation-delay:-{rnd.uniform(0,6):.1f}s"/>'
                  f'<circle r="3.5" fill="var(--bg)"/></g>')
    body = (
        f'<g fill="none" stroke="currentColor" stroke-width="1" opacity=".3">{"".join(base)}</g>'
        f'<g fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" opacity=".9">{"".join(pk)}</g>'
        f'<g fill="none" stroke="currentColor" stroke-width="1.2">{"".join(nd)}</g>'
        f'<g fill="currentColor">{"".join(w)}</g>'
        f'<g fill="none" stroke="currentColor" stroke-width="1" stroke-linejoin="round" opacity=".7">{"".join(b)}</g>'
        f'<g fill="currentColor" opacity=".3">{smoke}</g>'
    )
    return wrap("sc-net", body)

SCENES = {"data-analysis.html": ecg(), "brand-race.html": road(), "ai-adoption.html": net()}

def insert():
    for name, svg in SCENES.items():
        p = ROOT / name
        s = p.read_text(encoding="utf-8")
        s = re.sub(r'<div class="ambient[^\n]*</div>\n', "", s)          # replace an earlier run
        s = s.replace("<header>", '<header class="scene">', 1)
        s = re.sub(r'(<p class="tag">.*?</p>\n)', lambda m: m.group(1) + svg + "\n", s, count=1, flags=re.S)
        s = s.replace("styles.css?v=20261026", "styles.css?v=20261105")
        p.write_text(s, encoding="utf-8")
        print(name, len(svg), "bytes of svg")

if __name__ == "__main__":
    insert()
