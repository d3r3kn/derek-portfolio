"""Engraved ambient header scenes for the three data pages: one ink, hatch and cross-hatch
fills, slow looping motion. Run: python -I scripts/gen_ambient.py  (rewrites each page's .ambient block)."""
import math, random, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H = 1200, 180

# shared defs: hatch patterns and the 1200-wide clip used by every scrolling layer
PAT = (
    '<pattern id="amb-h1" width="6" height="6" patternUnits="userSpaceOnUse"><path d="M-1 7L7-1M-1 1L1-1M5 7L7 5" fill="none" stroke="currentColor" stroke-width=".7"/></pattern>'
    '<pattern id="amb-h2" width="6" height="6" patternUnits="userSpaceOnUse"><path d="M-1 7L7-1M-1 1L1-1M5 7L7 5M-1-1L7 7M-1 5L1 7M5-1L7 1" fill="none" stroke="currentColor" stroke-width=".7"/></pattern>'
    '<pattern id="amb-h3" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 2H4" fill="none" stroke="currentColor" stroke-width=".6"/></pattern>'
    '<pattern id="amb-hv" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M2 0V4" fill="none" stroke="currentColor" stroke-width=".6"/></pattern>'
    '<pattern id="amb-dots" width="5" height="5" patternUnits="userSpaceOnUse"><circle cx="2.5" cy="2.5" r=".55" fill="currentColor"/></pattern>'
    f'<clipPath id="amb-c"><rect width="{W}" height="{H}"/></clipPath>'
)
INK = 'fill="none" stroke="currentColor" stroke-linejoin="round" stroke-linecap="round"'

def wrap(cls, defs, body):
    return (f'<div class="ambient {cls}" aria-hidden="true">'
            f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" focusable="false">'
            f'<defs>{PAT}{defs}</defs>{body}</svg></div>')

def layer(id_, fn):
    """A scrolling layer: fn(dx) draws its content shifted by dx; drawn three times and clipped
    to the 1200 window so the two <use> copies tile without a seam."""
    return f'<g id="{id_}" clip-path="url(#amb-c)">{fn(-W)}{fn(0)}{fn(W)}</g>'

def tile(id_):
    return f'<use href="#{id_}"/><use href="#{id_}" x="{W}"/>'

def scallop(cx, cy, r, n=9, bulge=1.22, start=0.0):
    pts = [(cx + r * math.cos(start + 2 * math.pi * i / n), cy + r * math.sin(start + 2 * math.pi * i / n)) for i in range(n)]
    d = [f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(n):
        a = start + 2 * math.pi * (i + .5) / n
        c = (cx + r * bulge * math.cos(a), cy + r * bulge * math.sin(a)); p = pts[(i + 1) % n]
        d.append(f"Q{c[0]:.1f} {c[1]:.1f} {p[0]:.1f} {p[1]:.1f}")
    return "".join(d) + "Z"

def tree(x, g, r, lean=0):
    """A round tree on ground y=g: solid paper under a cross-hatched crown, denser on the shadow side."""
    cy = g - r * 1.9
    crown = scallop(x, cy, r, n=10, start=.3)
    shade = scallop(x + r * .3, cy + r * .1, r * .62, n=8, start=1)
    trunk = f"M{x-1.8} {g}L{x-1.3+lean} {cy+r*.3}H{x+1.3+lean}L{x+1.8} {g}Z"
    return (f'<path d="{trunk}" fill="url(#amb-hv)" stroke-width="1.1"/>'
            f'<path d="{crown}" fill="var(--bg)" stroke="none"/>'
            f'<path d="{crown}" fill="url(#amb-h2)" stroke-width="1.1"/>'
            f'<path d="{shade}" fill="url(#amb-h2)" stroke="none"/>'
            f'<path d="{shade}" fill="url(#amb-h3)" stroke="none" opacity=".8"/>')

def cypress(x, g, h):
    d = (f"M{x} {g}L{x-4} {g-h*.35}L{x-3} {g-h*.6}L{x-1.5} {g-h*.85}L{x} {g-h}"
         f"L{x+1.5} {g-h*.85}L{x+3} {g-h*.6}L{x+4} {g-h*.35}Z")
    return (f'<path d="{d}" fill="var(--bg)" stroke="none"/>'
            f'<path d="{d}" fill="url(#amb-h2)" stroke-width="1"/>'
            f'<path d="{d}" fill="url(#amb-hv)" stroke="none" opacity=".8"/>')

def bush(x, g, r):
    d = scallop(x, g - r * .4, r, n=7, start=3.3)
    return (f'<path d="{d}" fill="var(--bg)" stroke="none"/>'
            f'<path d="{d}" fill="url(#amb-h2)" stroke-width=".9"/>')

def wheel(wx, wy, r=8):
    return (f'<g transform="translate({wx} {wy})"><circle r="{r}" fill="var(--bg)" stroke-width="1.6"/>'
            f'<circle r="{r*.55:.1f}" stroke-width=".8"/><g class="amb-spin"><path d="M-{r*.55:.1f} 0H{r*.55:.1f}M0-{r*.55:.1f}V{r*.55:.1f}" stroke-width=".8"/></g>'
            f'<circle r="1.1" fill="currentColor" stroke="none"/></g>')

# ---------------------------------------------------------------- Brand Race
CARS = {
    "sedan": dict(L=92, body="M2-9V-20L14-22 26-38H58L72-23 86-20Q90-19 90-14V-9Z",
                  glass="M28-35H42V-24H20ZM46-35H57L68-24H46Z", lines="M44-24V-10M47-17H51M84-9H92M4-16H10", light=(87, -15), wheels=(18, 70)),
    "coupe": dict(L=100, body="M2-9V-16L18-18 34-32H62L78-19 94-16Q98-15 98-11V-9Z",
                  glass="M36-29H48V-21H28ZM52-29H61L72-21H52Z", lines="M50-21V-10M53-15H57M92-9H100", light=(95, -13), wheels=(20, 76)),
    "suv": dict(L=88, body="M2-9V-24L10-26 16-44H50L56-26 82-24Q86-23 86-15V-9Z",
                  glass="M18-41H30V-28H12ZM33-41H48L52-28H33Z", lines="M31-28V-10M34-20H38M16-46H50M80-9H88M4-18H10", light=(83, -17), wheels=(18, 66)),
    "wagon": dict(L=94, body="M2-9V-22L8-24 16-38H52L66-23 86-21Q90-20 90-13V-9Z",
                  glass="M18-35H34V-25H12ZM37-35H52L62-25H37Z", lines="M35-25V-10M38-18H42M84-9H92M4-16H9", light=(87, -15), wheels=(16, 70)),
}

def car(kind, x, dur, delay):
    c = CARS[kind]; lx, ly = c["light"]
    return (f'<g transform="translate({x} 176)"><g class="amb-sway" style="animation-duration:{dur}s;animation-delay:{delay}s">'
            f'<ellipse cx="{c["L"]/2}" cy="0" rx="{c["L"]/2+6}" ry="3.2" fill="url(#amb-h3)" stroke="none" opacity=".75"/>'
            f'<path d="{c["body"]}" fill="var(--bg)" stroke-width="1.5"/>'
            f'<path d="{c["glass"]}" fill="url(#amb-h1)" stroke-width="1"/>'
            f'<path d="{c["lines"]}" stroke-width="1"/><circle cx="{lx}" cy="{ly}" r="1.7" stroke-width="1"/>'
            + "".join(wheel(wx, -8) for wx in c["wheels"]) + '</g></g>')

def road():
    rnd = random.Random(5)
    # far mountains: lit face left (paper), shadow face right (hatch)
    peaks = [(80, 50), (200, 68), (330, 44), (470, 78), (600, 54), (720, 72), (860, 46), (980, 64), (1110, 58)]
    def mts(dx):
        out = []
        for x, h in sorted(peaks, key=lambda p: p[1]):
            x += dx; bw = h * 1.5; top = 146 - h
            out.append(f'<path d="M{x-bw} 146L{x} {top}V146Z" fill="var(--bg)" stroke="none"/>'
                       f'<path d="M{x} {top}L{x+bw} 146H{x}Z" fill="url(#amb-h1)" stroke="none"/>'
                       f'<path d="M{x-bw} 146L{x} {top}L{x+bw} 146" stroke-width="1"/>'
                       f'<path d="M{x} {top}L{x+bw*.45} {146-h*.25}M{x} {top}L{x-bw*.25} {146-h*.45}M{x+h*.1} {top+h*.35}L{x+bw*.7} {146-h*.1}" stroke-width=".7" opacity=".7"/>')
        return "".join(out)
    # mid hills with contour hatching under the ridge
    def ridge(x):
        t = 2 * math.pi * x / W
        return 118 - 20 * math.sin(t + .6) - 10 * math.sin(2 * t + 1.9) - 5 * math.sin(3 * t + 4.1) - 3 * math.sin(5 * t)
    pts = [f"{x} {ridge(x):.1f}" for x in range(-W, 2 * W + 1, 16)]
    hill = "M" + "L".join(pts) + f"V146H{-W}Z"
    contours = "".join(f'<path d="{"M" + "L".join(f"{x} {ridge(x)+k:.1f}" for x in range(-W, 2*W+1, 16))}" stroke-width=".8" opacity="{op}"/>'
                       for k, op in ((5, .5), (10, .4), (15, .3), (20, .22), (25, .15), (30, .09)))
    hills = (f'<g id="amb-hills" clip-path="url(#amb-c)"><path d="{hill}" fill="var(--bg)" stroke-width="1.1"/>'
             f'<g clip-path="url(#amb-hillc)">{contours}</g></g>')
    # near: trees, bushes, a rail fence, grass
    objs = []
    x = 0
    while x < W:
        k = rnd.random()
        if k < .18: objs.append(("cy", x, rnd.uniform(26, 40)))
        elif k < .62: objs.append(("tr", x, rnd.uniform(8, 14)))
        else: objs.append(("bu", x, rnd.uniform(5, 9)))
        x += rnd.uniform(26, 70)
    fences = [(300, 560), (880, 1080)]
    def near(dx):
        out = []
        for a, b in fences:
            out.append(f'<path d="M{a+dx} 141H{b+dx}M{a+dx} 136H{b+dx}" stroke-width=".9"/>')
            out += [f'<path d="M{px+dx} 146V132" stroke-width="1.2"/>' for px in range(a, b + 1, 26)]
        for kind, ox, s in objs:
            if kind == "cy": out.append(cypress(ox + dx, 146, s))
            elif kind == "tr": out.append(tree(ox + dx, 146, s))
            else: out.append(bush(ox + dx, 146, s))
        out.append("".join(f'<path d="M{gx+dx} 152l-2-4M{gx+dx} 152l2-5M{gx+dx} 152v-4" stroke-width=".7"/>' for gx in range(7, W, 23)))
        return "".join(out)
    # clouds with a hatched underside
    CLOUD = "M0 0c-2-12 10-20 22-14 4-10 20-12 28-2 10-4 20 4 18 12 6 0 10 6 8 10H2C-2 8-2 2 0 0Z"
    cloud = (f'<clipPath id="amb-cc"><path d="{CLOUD}"/></clipPath>'
             f'<g id="amb-cloud"><path d="{CLOUD}" fill="var(--bg)" stroke-width="1"/>'
             f'<rect x="-4" y="2" width="90" height="10" fill="url(#amb-h1)" stroke="none" clip-path="url(#amb-cc)"/></g>')
    rays = "".join(f'<path d="M{1010+math.cos(a)*21:.1f} {50+math.sin(a)*21:.1f}L{1010+math.cos(a)*(29 if i%2 else 25):.1f} {50+math.sin(a)*(29 if i%2 else 25):.1f}"/>'
                   for i, a in enumerate(2 * math.pi * i / 16 for i in range(16)))
    sun = f'<g stroke-width=".9" opacity=".55"><circle cx="1010" cy="50" r="15" fill="url(#amb-dots)"/>{rays}</g>'
    skylines = "".join(f"<path d='M0 {y}H1200'/>" for y in (88, 93, 98, 103, 108))
    sky = f'<g stroke-width=".7" opacity=".16">{skylines}</g>'
    bird = ('<g class="amb-flap"><path d="M-7 0Q-3.5-4 0 0Q3.5-4 7 0" stroke-width="1"/></g>')
    birds = (f'<g class="amb-birds" stroke-width="1" opacity=".7">'
             f'<g transform="translate(0 40)">{bird}</g><g transform="translate(22 32)">{bird}</g><g transform="translate(38 46)">{bird}</g></g>')
    defs = (f'<g id="amb-mts" clip-path="url(#amb-c)">{mts(-W)}{mts(0)}{mts(W)}</g>'
            f'<clipPath id="amb-hillc"><path d="{hill}"/></clipPath>{hills}'
            f'<g id="amb-nearobj">{near(0)}</g>'
            f'<g id="amb-near" clip-path="url(#amb-c)"><use href="#amb-nearobj" x="{-W}"/><use href="#amb-nearobj"/><use href="#amb-nearobj" x="{W}"/></g>{cloud}')
    body = (f'<g {INK}>{sky}{sun}{birds}'
            f'<g class="amb-drift">' + "".join(f'<use href="#amb-cloud" x="{x}" y="{y}" opacity=".8"/>' for x, y in
            ((160, 46), (620, 24), (980, 60), (1360, 46), (1820, 24), (2180, 60))) + '</g>'
            f'<g class="amb-slower" opacity=".5">{tile("amb-mts")}</g>'
            f'<g class="amb-slow" opacity=".85">{tile("amb-hills")}</g>'
            f'<g class="amb-near">{tile("amb-near")}</g>'
            f'<path d="M0 146H1200" stroke-width="1"/>'
            f'<rect x="0" y="147" width="1200" height="5" fill="url(#amb-dots)" stroke="none" opacity=".5"/>'
            f'<rect x="0" y="153" width="1200" height="27" fill="url(#amb-h3)" stroke="none" opacity=".16"/>'
            f'<path class="amb-lane" d="M0 164H1200" stroke-width="1.6" stroke-dasharray="34 30" opacity=".5"/>'
            + car("coupe", 120, 29, -4) + car("sedan", 390, 23, -15) + car("suv", 680, 36, -9) + car("wagon", 950, 27, -21)
            + '</g>')
    return wrap("sc-road", defs, body)

# ---------------------------------------------------------------- Medicaid: an engraved hospital street
def window(x, y, w, h, arch=False, hatch="amb-h1"):
    if arch:
        d = f"M{x} {y+h}V{y+w/2}A{w/2} {w/2} 0 0 1 {x+w} {y+w/2}V{y+h}Z"
    else:
        d = f"M{x} {y}h{w}v{h}h-{w}Z"
    return f'<path d="{d}" fill="url(#{hatch})" stroke-width=".9"/><path d="M{x+w/2} {y+(w/2 if arch else 0)}V{y+h}" stroke-width=".5" opacity=".6"/>'

def box(x, top, w, bottom=H, depth=12, roof=True):
    """Front face, hatched side face in slight perspective, dotted roof; bottom defaults to the ground."""
    d = depth; sh = d * .5
    out = f'<path d="M{x+w} {top}L{x+w+d} {top-sh}V{bottom-sh}L{x+w} {bottom}Z" fill="url(#amb-h2)" stroke-width="1"/>'
    if roof: out += f'<path d="M{x} {top}H{x+w}L{x+w+d} {top-sh}H{x+d}Z" fill="url(#amb-dots)" stroke-width="1"/>'
    out += f'<path d="M{x} {top}H{x+w}V{bottom}H{x}Z" fill="var(--bg)" stroke-width="1.3"/>'
    return out

def block(x, top, w, depth=12, roof=True):
    return box(x, top, w, H, depth, roof)

def gable(x, top, w, rise, depth, over=4):
    """A pitched roof with depth: the near slope as a hatched parallelogram, then the front triangle."""
    d = depth; sh = d * .5
    return (f'<path d="M{x+w/2} {top-rise}L{x+w+over} {top}L{x+w+over+d} {top-sh}L{x+w/2+d} {top-rise-sh}Z" fill="url(#amb-h2)" stroke-width="1"/>'
            f'<path d="M{x-over} {top}L{x+w/2} {top-rise}L{x+w+over} {top}Z" fill="url(#amb-h1)" stroke-width="1.2"/>')

def ecg():
    g = H
    # hospital: wide block with a central bay (its own roof and side), pediment, cross, steps and a flag
    hx, hw, ht = 70, 230, 80
    hosp = block(hx, g - ht, hw)
    hosp += f'<path d="M{hx} {g-ht+8}H{hx+hw}" stroke-width=".8"/>'
    for yy, arch in ((g - ht + 14, True), (g - ht + 38, False), (g - ht + 58, False)):
        for cx in list(range(hx + 12, hx + 80, 18)) + list(range(hx + 152, hx + 220, 18)):
            hosp += window(cx, yy, 10, 16, arch)
    bx, bw_, bt = hx + 85, 60, g - ht - 12
    hosp += (box(bx, bt, bw_, g, depth=12)
             + gable(bx, bt, bw_, 16, 12, over=3)
             + f'<circle cx="{bx+bw_/2}" cy="{bt+20}" r="10" fill="var(--bg)" stroke-width="1.2"/>'
             f'<path d="M{bx+bw_/2} {bt+14}V{bt+26}M{bx+bw_/2-6} {bt+20}H{bx+bw_/2+6}" stroke-width="3"/>'
             f'{window(bx+8, bt+40, 10, 16, True)}{window(bx+bw_-18, bt+40, 10, 16, True)}'
             f'<path d="M{bx+20} {g}V{bt+58}A10 10 0 0 1 {bx+40} {bt+58}V{g}Z" fill="url(#amb-h2)" stroke-width="1.1"/>'
             f'<path d="M{bx+30} {bt+58}V{g}" stroke-width=".8"/>'
             f'<path d="M{bx-6} {g-3}H{bx+bw_+6}M{bx-10} {g-6}H{bx+bw_+10}" stroke-width=".9"/>'
             f'<path d="M{bx+bw_/2} {bt-16}V{bt-34}" stroke-width="1.1"/>'
             f'<path d="M{bx+bw_/2} {bt-33}q7 2 14 0v8q-7 2-14 0Z" fill="url(#amb-h3)" stroke-width="1"/>')
    # clinic with a pitched roof and a signpost
    cx, cw, ct = 390, 110, g - 54
    clinic = (block(cx, ct, cw, depth=10, roof=False) + gable(cx, ct, cw, 26, 10, over=6)
              + f'{window(cx+12, ct+14, 14, 18)}{window(cx+cw-26, ct+14, 14, 18)}'
              f'<path d="M{cx+cw/2-9} {g}V{ct+16}H{cx+cw/2+9}V{g}" fill="url(#amb-hv)" stroke-width="1.1"/>'
              f'<path d="M{cx+cw/2+9} {ct-14}V{ct-22}M{cx+cw/2+3} {ct-18}H{cx+cw/2+15}" stroke-width="2.6"/>'
              f'<path d="M{cx-26} {g}V{g-40}M{cx-36} {g-40}H{cx-16}V{g-56}H{cx-36}Z" fill="var(--bg)" stroke-width="1.1"/>'
              f'<path d="M{cx-26} {g-45}V{g-51}M{cx-29} {g-48}H{cx-23}" stroke-width="2"/>')
    # pharmacy: scalloped awning, big window with mortar and pestle, sign board
    px, pw, pt = 600, 150, g - 62
    awn = "".join("a7 5 0 0 1 14 0" for _ in range(pw // 14))
    pharm = (block(px, pt, pw, depth=12)
             + f'<path d="M{px} {pt+14}H{px+pw}V{pt+6}H{px}Z" fill="url(#amb-h3)" stroke-width="1"/>'
             f'<path d="M{px-4} {pt+30}L{px+8} {pt+20}H{px+pw-8}L{px+pw+4} {pt+30}Z" fill="url(#amb-h1)" stroke-width="1"/>'
             f'<path d="M{px-4} {pt+30}{awn}" fill="var(--bg)" stroke-width="1"/>'
             f'<path d="M{px+12} {g-6}V{pt+38}H{px+90}V{g-6}Z" fill="url(#amb-dots)" stroke-width="1.1"/>'
             f'<path d="M{px+36} {pt+52}h30l-5 14h-20zM{px+58} {pt+44}l10-9" stroke-width="1.3" fill="var(--bg)"/>'
             f'<path d="M{px+104} {g}V{pt+42}A11 11 0 0 1 {px+126} {pt+42}V{g}Z" fill="url(#amb-h2)" stroke-width="1.1"/>'
             f'<path d="M{px+12} {g-6}H{px+90}M{px+12} {g-3}H{px+90}" stroke-width=".8"/>')
    # lamp post, a modern wing with a helipad sign and a blinking mast, trees
    lamp = ('<path d="M820 180V116M814 116H826M820 116V108a6 6 0 0 1 12 0v8h-12" stroke-width="1.3" fill="var(--bg)"/>'
            '<path d="M814 180H826" stroke-width="1.4"/>')
    wx, ww, wt = 880, 150, g - 104
    wing = block(wx, wt, ww, depth=14)
    for yy in range(wt + 12, g - 18, 18):
        for xx in range(wx + 10, wx + ww - 14, 20):
            wing += window(xx, yy, 12, 11)
    wing += (f'<path d="M{wx+10} {wt-2}V{wt-24}" stroke-width="1.2"/><circle cx="{wx+10}" cy="{wt-27}" r="3" fill="var(--bg)" stroke-width="1"/>'
             f'<g class="amb-fa"><circle cx="{wx+10}" cy="{wt-27}" r="2" fill="currentColor" stroke="none"/></g>'
             f'<circle cx="{wx+ww-30}" cy="{wt-12}" r="10" fill="var(--bg)" stroke-width="1.2"/><path d="M{wx+ww-30} {wt-2}V{wt}" stroke-width="1.2"/>'
             f'<path d="M{wx+ww-34} {wt-17}V{wt-7}M{wx+ww-26} {wt-17}V{wt-7}M{wx+ww-34} {wt-12}H{wx+ww-26}" stroke-width="1.6"/>')
    trees = tree(348, g, 13) + tree(545, g, 11) + bush(575, g, 7) + tree(1118, g, 14, lean=2) + bush(1150, g, 8) + bush(30, g, 9) + bush(52, g, 6)
    # the trace, kept clear above the rooftops
    beat = "M0 30L62 30Q72 22 82 30L112 30L118 36L126 4L134 44L140 30L184 30Q198 18 212 30L300 30"
    parts = []
    for i in range(4):
        seg = re.sub(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)", lambda m: f"{float(m.group(1))+i*300:g} {m.group(2)}", beat)
        parts.append(seg if i == 0 else seg.replace("M", "L", 1))
    trace = " ".join(parts)
    # the ambulance: box body, cab, belt stripe, cross, alternating light bar, spinning wheels
    amb = ('<g transform="translate(0 180)">'
           '<ellipse cx="38" cy="0" rx="44" ry="3.2" fill="url(#amb-h3)" stroke="none" opacity=".75"/>'
           '<path d="M1-9V-36Q1-38 3-38H45Q47-38 47-36V-31H52L62-20 72-18Q75-17 75-12V-9Z" fill="var(--bg)" stroke-width="1.5"/>'
           '<path d="M53-30H58L66-21H53ZM38-34H45V-27H38Z" fill="url(#amb-h1)" stroke-width="1"/>'
           '<path d="M1-25H47V-21H1Z" fill="url(#amb-h3)" stroke-width=".9"/>'
           '<path d="M49-31V-10M55-18H59M70-9H78" stroke-width="1"/>'
           '<path d="M22-18V-9M17.5-13.5H26.5" stroke-width="2.6"/>'
           '<circle cx="73" cy="-14" r="1.6" stroke-width="1"/>'
           '<path d="M13-41H35V-38H13Z" fill="var(--bg)" stroke-width="1"/>'
           '<g class="amb-fa"><path d="M14-40h9v1.5h-9z" fill="currentColor" stroke="none"/></g>'
           '<g class="amb-fb"><path d="M25-40h9v1.5h-9z" fill="currentColor" stroke="none"/></g>'
           + wheel(13, -7, 7) + wheel(61, -7, 7) + '</g>')
    defs = ('<pattern id="amb-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="currentColor" stroke-width="1"/></pattern>'
            f'<path id="amb-beat" d="{trace}"/>')
    body = (f'<rect width="{W}" height="{H}" fill="url(#amb-grid)" opacity=".08"/>'
            f'<g {INK}>{hosp}{clinic}{pharm}{lamp}{wing}{trees}'
            f'<rect x="0" y="172" width="1200" height="8" fill="url(#amb-h3)" stroke="none" opacity=".25"/>'
            f'<g class="amb-scroll" stroke-width="1.7" opacity=".85"><use href="#amb-beat"/><use href="#amb-beat" x="1200"/></g>'
            f'<g class="amb-cross">{amb}</g></g>')
    return wrap("sc-ecg", defs, body)

# ---------------------------------------------------------------- AI Adoption: signals over industries
def net():
    rnd = random.Random(3)
    G = H
    b, w = [], []
    def windows(x0, top, cols, rows, ww=7, hh=9, cx=15, cy=13, pad=9):
        for r in range(rows):
            for c in range(cols):
                w.append(f'<rect class="amb-win" x="{x0+pad+c*cx}" y="{top+pad+r*cy}" width="{ww}" height="{hh}" '
                         f'style="--d:-{rnd.uniform(0,14):.1f}s;--p:{rnd.uniform(8,15):.1f}s"/>')
    # tech tower with an antenna
    x = 20; b.append(block(x, G-120, 70, depth=10)); windows(x, G-120, 4, 8)
    b.append(f'<path d="M{x+35} {G-120}V{G-150}M{x+29} {G-140}H{x+41}" stroke-width="1.2"/><g class="amb-fa"><circle cx="{x+35}" cy="{G-152}" r="2.2" fill="currentColor" stroke="none"/></g>')
    # hospital
    x = 120; b.append(block(x, G-58, 110, depth=10) + box(x+38, G-80, 34, G-58, depth=10)
                      + f'<path d="M{x+55} {G-75}v12M{x+49} {G-69}h12" stroke-width="2.6"/>'); windows(x, G-58, 6, 3, cx=16, cy=15, pad=10)
    # factory with sawtooth roof and chimney
    x = 262; saw = "".join(f"L{x+i*30} {G-70}L{x+i*30+30} {G-48}" for i in range(4))
    b.append(f'<path d="M{x+120} {G-48}L{x+130} {G-53}V{G-5}L{x+120} {G}Z" fill="url(#amb-h2)" stroke-width="1"/>'
             f'<path d="M{x} {G}V{G-48}{saw}V{G}Z" fill="var(--bg)" stroke-width="1.3"/>'
             + "".join(f'<path d="M{x+i*30} {G-48}V{G-70}L{x+i*30+30} {G-48}Z" fill="url(#amb-h1)" stroke="none"/>' for i in range(4))
             + f'<path d="M{x+90} {G-70}L{x+120} {G-48}L{x+130} {G-53}L{x+100} {G-75}Z" fill="url(#amb-h2)" stroke-width="1"/>'
             + f'<path d="M{x+100} {G-96}h9v30h-9z" fill="url(#amb-hv)" stroke-width="1.1"/><path d="M{x+109} {G-96}l4-2v30l-4 2z" fill="url(#amb-h2)" stroke-width="1"/>')
    windows(x, G-48, 7, 2, cx=16, cy=16, pad=10, ww=9, hh=8)
    smoke = "".join(f'<path class="amb-smoke" d="M{x+104.5} {G-100}c-3-3 2-7 0-10s3-6 0-9" stroke-width="1.1" style="animation-delay:-{d}s"/>' for d in (0, 2.5, 5))
    # retail with awning
    x = 412; b.append(block(x, G-44, 90, depth=8) + f'<path d="M{x-4} {G-44}' + "".join("a5 5 0 0 0 10 0" for _ in range(9)) + f'" fill="url(#amb-h1)" stroke-width="1"/>'
                      f'<path d="M{x+14} {G-30}h26v22h-26zM{x+50} {G-30}h26v22h-26z" fill="url(#amb-dots)" stroke-width="1"/>')
    w.append(f'<rect class="amb-win" x="{x+16}" y="{G-28}" width="22" height="18" style="--d:-3s;--p:11s"/>'
             f'<rect class="amb-win" x="{x+52}" y="{G-28}" width="22" height="18" style="--d:-9s;--p:13s"/>')
    # school with a gable, bell tower and clock
    x = 532; b.append(block(x, G-56, 100, depth=8, roof=False) + gable(x, G-56, 100, 28, 8, over=2)
                      + f'<path d="M{x+42} {G-80}V{G-98}H{x+58}V{G-80}M{x+42} {G-98}L{x+50} {G-108}L{x+58} {G-98}" fill="var(--bg)" stroke-width="1.1"/>'
                      f'<circle cx="{x+50}" cy="{G-90}" r="5" stroke-width=".9"/><path d="M{x+50} {G-90}v-3.5M{x+50} {G-90}h2.5" stroke-width=".9"/>')
    windows(x, G-56, 5, 3, cx=17, cy=15, pad=11)
    # bank with pediment and columns
    x = 662; b.append(block(x, G-64, 100, depth=8, roof=False) + gable(x, G-64, 100, 22, 8, over=4)
                      + "".join(f'<path d="M{x+11+i*18} {G-58}h6V{G-8}h-6z" fill="url(#amb-hv)" stroke-width="1"/>' for i in range(5))
                      + f'<path d="M{x-2} {G-4}H{x+102}" stroke-width="1"/>')
    windows(x+2, G-64, 4, 1, cx=18, cy=14, pad=21, ww=10, hh=24)
    # government dome with a flag
    x = 792; b.append(block(x, G-60, 110, depth=10) + f'<path d="M{x+30} {G-60}A25 25 0 0 1 {x+80} {G-60}Z" fill="url(#amb-h1)" stroke-width="1.2"/>'
                      f'<path d="M{x+55} {G-85}V{G-104}M{x+55} {G-103}q6 2 12 0v7q-6 2-12 0Z" fill="url(#amb-h3)" stroke-width="1"/>')
    windows(x, G-60, 6, 3, cx=16, cy=15, pad=11)
    # warehouse with barrel roof
    x = 932; b.append(f'<path d="M{x+110} {G-50}L{x+120} {G-55}V{G-5}L{x+110} {G}Z" fill="url(#amb-h2)" stroke-width="1"/>'
                      f'<path d="M{x+110} {G-50}A55 30 0 0 0 {x+55} {G-80}L{x+65} {G-85}A55 30 0 0 1 {x+120} {G-55}Z" fill="url(#amb-h2)" stroke-width="1"/>'
                      f'<path d="M{x} {G}V{G-50}A55 30 0 0 1 {x+110} {G-50}V{G}Z" fill="var(--bg)" stroke-width="1.3"/>'
                      f'<path d="M{x} {G-50}A55 30 0 0 1 {x+110} {G-50}V{G-44}A55 30 0 0 0 {x} {G-44}Z" fill="url(#amb-h1)" stroke="none"/>'
                      f'<path d="M{x+38} {G-34}h34v34h-34z" fill="url(#amb-h3)" stroke-width="1"/><path d="M{x+38} {G-24}H{x+72}M{x+38} {G-14}H{x+72}" stroke-width=".8"/>')
    windows(x, G-50, 2, 1, cx=84, cy=0, pad=12, ww=14, hh=10)
    # mid tower and a short tower at the edge
    x = 1072; b.append(block(x, G-90, 60, depth=10)); windows(x, G-90, 3, 6, cx=16, cy=13, pad=9)
    x = 1152; b.append(block(x, G-70, 56, depth=8)); windows(x, G-70, 3, 4, cx=16, cy=14, pad=8)
    trees = tree(105, G, 9) + tree(245, G, 10) + bush(400, G, 6) + tree(520, G, 8) + bush(648, G, 6) + tree(778, G, 10) + bush(918, G, 7) + tree(1058, G, 8)

    nodes = [(96, 38), (170, 22), (300, 60), (430, 26), (545, 62), (665, 20), (790, 56),
             (905, 24), (1020, 62), (1125, 28), (1190, 64)]
    edges = [(0, 1), (1, 2), (1, 3), (0, 2), (2, 3), (2, 4), (3, 5), (3, 4), (4, 5), (4, 6), (5, 6), (5, 7),
             (6, 7), (6, 8), (7, 9), (7, 8), (8, 9), (8, 10), (9, 10)]
    drops = [(0, 55, G-150), (2, 300, G-70), (4, 545, G-108), (6, 847, G-104), (8, 1020, G-80), (10, 1102, G-90)]
    base, pk, nd = [], [], []
    for a, c in edges:
        (x1, y1), (x2, y2) = nodes[a], nodes[c]
        base.append(f'<path d="M{x1} {y1}L{x2} {y2}"/>')
        pk.append(f'<path d="M{x1} {y1}L{x2} {y2}" pathLength="100" class="amb-pkt" style="animation-duration:{rnd.uniform(7,14):.1f}s;animation-delay:-{rnd.uniform(0,14):.1f}s"/>')
    for n, x2, y2 in drops:
        x1, y1 = nodes[n]
        base.append(f'<path d="M{x1} {y1}L{x2} {y2}" stroke-dasharray="2 4"/>')
        pk.append(f'<path d="M{x1} {y1}L{x2} {y2}" pathLength="100" class="amb-pkt" style="animation-duration:{rnd.uniform(9,16):.1f}s;animation-delay:-{rnd.uniform(0,14):.1f}s"/>')
    for x1, y1 in nodes:
        nd.append(f'<g transform="translate({x1} {y1})"><circle class="amb-ring" r="8" style="animation-delay:-{rnd.uniform(0,6):.1f}s"/>'
                  f'<circle r="5" fill="url(#amb-dots)" stroke-width="1"/><circle r="2.2" fill="var(--bg)" stroke-width="1"/></g>')
    body = (f'<g {INK}>'
            f'<g stroke-width="1" opacity=".3">{"".join(base)}</g>'
            f'<g stroke-width="2.2" opacity=".9">{"".join(pk)}</g>'
            f'<g stroke-width="1.2">{"".join(nd)}</g>'
            f'<rect x="0" y="172" width="1200" height="8" fill="url(#amb-h3)" stroke="none" opacity=".25"/>'
            f'<g stroke-width="1" opacity=".8">{"".join(b)}</g>'
            f'<g fill="currentColor" stroke="none">{"".join(w)}</g>{trees}'
            f'<g opacity=".5">{smoke}</g></g>')
    return wrap("sc-net", "", body)

SCENES = {"data-analysis.html": ecg(), "brand-race.html": road(), "ai-adoption.html": net()}

def insert():
    for name, svg in SCENES.items():
        p = ROOT / name
        s = p.read_text(encoding="utf-8")
        s = re.sub(r'<div class="ambient[^\n]*</div>\n', "", s)
        s = s.replace("<header>", '<header class="scene">', 1)
        s = re.sub(r'(<p class="tag">.*?</p>\n)', lambda m: m.group(1) + svg + "\n", s, count=1, flags=re.S)
        s = s.replace("styles.css?v=20261026", "styles.css?v=20261105")
        p.write_text(s, encoding="utf-8")
        print(name, len(svg), "bytes of svg")

if __name__ == "__main__":
    insert()
