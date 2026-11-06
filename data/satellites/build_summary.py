"""Build the numbers behind the Satellite Physics page.

Input:  raw/celestrak-active.csv, CelesTrak's untouched "active satellites" catalog
        (general perturbations elements, CSV format; see README.md).
Output: summary.json: every active satellite's altitude, period and speed worked out
        from its mean motion, the catalog grouped by orbit band and constellation, a
        thinned set of points for the charts, the upper-atmosphere profile from the
        NRLMSIS 2.1 model (temperature, density, and how much heat that air can
        deliver to a satellite), the radiation budget in orbit, and every check.

Usage:  python build_summary.py        (needs numpy and pymsis)
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pymsis

HERE = Path(__file__).parent
RAW = HERE / "raw" / "celestrak-active.csv"
RAW_SHA256 = "fc9ce8c41dcc0ebf02ee26d81e5bbf5363c341ea12a0a16a238dacf74a436aff"
ACCESSED = "2026-11-06"

# Physical constants (CODATA 2018 / IERS / NASA) -- see README.md for each source.
MU = 398600.4418       # km^3/s^2, Earth's gravitational parameter
RE = 6378.137          # km, Earth's equatorial radius (altitudes are measured from here)
C = 299792.458         # km/s, speed of light
K_B = 1.380649e-23     # J/K, Boltzmann constant
SIGMA = 5.670374419e-8 # W/m^2/K^4, Stefan-Boltzmann constant
SOLAR = 1360.0         # W/m^2, total solar irradiance at Earth's distance (NASA: "about 1,360")
EARTH_IR = 240.0       # W/m^2, sunlight Earth absorbs on average, and so radiates back out as heat in balance
ALBEDO = 0.29          # fraction of sunlight Earth reflects
MIN_ELEVATION = 25.0   # degrees above the horizon a user antenna needs (Starlink's published minimum)

# Solar activity levels for the atmosphere model: F10.7 radio flux in solar flux units.
SOLAR_LEVELS = {"low": 70, "moderate": 150, "high": 250}

# Constellations and landmark satellites, matched on the start of the catalog name.
GROUPS = [
    ("Starlink", "STARLINK"), ("OneWeb", "ONEWEB"), ("Kuiper", "KUIPER"), ("Qianfan", "QIANFAN"),
    ("Guowang", "HULIANWANG"), ("Iridium", "IRIDIUM"), ("Globalstar", "GLOBALSTAR"),
    ("GPS", "NAVSTAR"), ("BeiDou", "BEIDOU"), ("Galileo", "GSAT"),
]
ISS_NAME = "ISS (ZARYA)"


def orbit(mean_motion, ecc):
    """Period (min), semi-major axis, mean altitude, perigee and apogee (km), speed (km/s)."""
    period = 1440.0 / mean_motion
    a = (MU * (period * 60 / (2 * math.pi)) ** 2) ** (1 / 3)
    return {"period": period, "a": a, "alt": a - RE, "peri": a * (1 - ecc) - RE,
            "apo": a * (1 + ecc) - RE, "speed": math.sqrt(MU / a)}


def band(o, ecc):
    if ecc > 0.25:
        return "elliptical"
    if o["alt"] < 2000:
        return "low"
    if abs(o["period"] - 1436.07) < 10:
        return "geostationary"
    if o["alt"] < 35000:
        return "medium"
    return "high"


def physics(h):
    """Everything that follows from altitude alone, for a circular orbit."""
    r = RE + h
    period = 2 * math.pi * math.sqrt(r ** 3 / MU) / 60
    speed = math.sqrt(MU / r)
    e = math.radians(MIN_ELEVATION)
    slant = math.sqrt(r * r - (RE * math.cos(e)) ** 2) - RE * math.sin(e)
    gamma = math.acos(RE * math.cos(e) / r) - e           # usable half-width of the footprint, radians
    horizon = math.acos(RE / r)
    view = (RE / r) ** 2                                   # how much of a flat plate's sky Earth fills
    return {
        "alt": h, "period_min": period, "speed_kms": speed,
        "ping_overhead_ms": 4 * h / C * 1000, "ping_edge_ms": 4 * slant / C * 1000,
        "footprint_share": (1 - math.cos(gamma)) / 2,       # share of Earth's surface, at 25 deg or higher
        "horizon_share": (1 - math.cos(horizon)) / 2,       # share of Earth's surface in line of sight
        "pass_min": gamma * period / math.pi,               # time overhead on a pass through the zenith
        "earth_ir_wm2": EARTH_IR * view, "albedo_max_wm2": ALBEDO * SOLAR * view,
    }


def atmosphere(alts_km):
    """NRLMSIS 2.1 at the equator, local noon, quiet geomagnetic conditions, three solar levels."""
    out = {}
    date = np.datetime64(f"{ACCESSED}T12:00")
    for level, f107 in SOLAR_LEVELS.items():
        res = np.squeeze(pymsis.calculate(date, 0, 0, np.array(alts_km, dtype=float),
                                          f107s=f107, f107as=f107, aps=[[4] * 7], version=2.1))
        rho = res[:, pymsis.Variable.MASS_DENSITY]
        temp = res[:, pymsis.Variable.TEMPERATURE]
        species = [pymsis.Variable.N2, pymsis.Variable.O2, pymsis.Variable.O, pymsis.Variable.HE,
                   pymsis.Variable.H, pymsis.Variable.AR, pymsis.Variable.N, pymsis.Variable.ANOMALOUS_O,
                   pymsis.Variable.NO]
        n = np.nansum(np.stack([res[:, s] for s in species]), axis=0)  # molecules per m^3
        rows = []
        for h, rh, t, nn in zip(alts_km, rho, temp, n):
            r = RE + h
            v = math.sqrt(MU / r) * 1000 if h >= 100 else None  # m/s, only meaningful where orbits exist
            m = rh / nn if nn > 0 else float("nan")             # mean molecular mass, kg
            vbar = math.sqrt(8 * K_B * t / (math.pi * m)) if m > 0 else 0
            thermal = nn * vbar / 4 * 2 * K_B * t                # W/m^2 the resting gas can deliver to a cold wall
            ram = 0.5 * rh * v ** 3 if v else None               # W/m^2 on the face plowing through it at orbital speed
            rows.append({"alt": h, "temp_k": float(t), "density": float(rh), "number_density": float(nn),
                         "thermal_wm2": float(thermal), "ram_wm2": None if ram is None else float(ram)})
        out[level] = rows
    return out


def main():
    raw_bytes = RAW.read_bytes()
    with RAW.open(encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))

    sats = []
    for r in raw:
        mm, ecc = float(r["MEAN_MOTION"]), float(r["ECCENTRICITY"])
        o = orbit(mm, ecc)
        sats.append({"name": r["OBJECT_NAME"], "id": int(r["NORAD_CAT_ID"]), "intl": r["OBJECT_ID"],
                     "epoch": r["EPOCH"], "ecc": ecc, "inc": float(r["INCLINATION"]),
                     **o, "band": band(o, ecc)})

    # Orbit bands
    band_order = ["low", "medium", "geostationary", "high", "elliptical"]
    bands = []
    for b in band_order:
        g = [s for s in sats if s["band"] == b]
        if g:
            bands.append({"band": b, "count": len(g), "alt_median": float(np.median([s["alt"] for s in g])),
                          "period_median": float(np.median([s["period"] for s in g]))})

    # Altitude histogram (log-spaced bins, 150 km to 100,000 km)
    edges = np.logspace(math.log10(150), math.log10(100000), 57)
    counts, _ = np.histogram([s["alt"] for s in sats], bins=edges)
    hist = [{"lo": float(edges[i]), "hi": float(edges[i + 1]), "n": int(counts[i])} for i in range(len(counts))]

    # Constellations and landmarks
    groups = []
    for label, prefix in GROUPS:
        g = [s for s in sats if s["name"].upper().startswith(prefix)]
        if not g:
            continue
        groups.append({"name": label, "count": len(g),
                       "alt": float(np.median([s["alt"] for s in g])),
                       "alt_lo": float(np.percentile([s["alt"] for s in g], 10)),
                       "alt_hi": float(np.percentile([s["alt"] for s in g], 90)),
                       "period": float(np.median([s["period"] for s in g])),
                       "speed": float(np.median([s["speed"] for s in g])),
                       "inc": float(np.median([s["inc"] for s in g]))})
    geo = [s for s in sats if s["band"] == "geostationary"]
    groups.append({"name": "Geostationary belt", "count": len(geo),
                   "alt": float(np.median([s["alt"] for s in geo])),
                   "alt_lo": float(np.percentile([s["alt"] for s in geo], 10)),
                   "alt_hi": float(np.percentile([s["alt"] for s in geo], 90)),
                   "period": float(np.median([s["period"] for s in geo])),
                   "speed": float(np.median([s["speed"] for s in geo])),
                   "inc": float(np.median([s["inc"] for s in geo]))})
    iss = next(s for s in sats if s["name"] == ISS_NAME)
    groups.append({"name": "Space station", "count": 1, "alt": iss["alt"], "alt_lo": iss["peri"], "alt_hi": iss["apo"],
                   "period": iss["period"], "speed": iss["speed"], "inc": iss["inc"]})

    # Thinned points for the scatter: every low-orbit satellite in a 1-in-8 sample, everything else whole.
    low = sorted([s for s in sats if s["band"] == "low"], key=lambda s: s["id"])
    rest = [s for s in sats if s["band"] != "low"]
    sample = low[::8] + rest
    points = [[round(s["alt"], 1), round(s["period"], 2), s["name"]] for s in sorted(sample, key=lambda s: s["alt"])]

    # Physics along an altitude axis, for the curves and the slider
    axis = sorted(set([float(x) for x in np.logspace(math.log10(150), math.log10(100000), 120)] +
                      [200, 400, 420, 550, 1200, 20200, 35786]))
    curve = [physics(h) for h in axis]

    # Atmosphere profile, 0 to 1,200 km
    atm_alts = list(range(0, 1201, 10))
    atm = atmosphere(atm_alts)

    # The radiation budget at a few altitudes, plus the air, for the energy-budget chart
    budget = []
    for h in (200, 400, 550, 1200):
        ph = physics(h)
        air = {lvl: next(r for r in rows if r["alt"] == h) for lvl, rows in atm.items()}
        budget.append({"alt": h, "sunlight": SOLAR, "earth_ir": ph["earth_ir_wm2"], "albedo_max": ph["albedo_max_wm2"],
                       "air_ram": {lvl: a["ram_wm2"] for lvl, a in air.items()},
                       "air_thermal": {lvl: a["thermal_wm2"] for lvl, a in air.items()},
                       "air_temp_k": {lvl: a["temp_k"] for lvl, a in air.items()}})

    # Equilibrium temperatures of a flat plate with equal absorptivity and emissivity
    temps = {
        "sun_plate_two_sides_c": (SOLAR / (2 * SIGMA)) ** 0.25 - 273.15,
        "sun_plate_one_side_c": (SOLAR / SIGMA) ** 0.25 - 273.15,
        "sphere_c": (SOLAR / (4 * SIGMA)) ** 0.25 - 273.15,
        "shadow_earth_glow_400km_c": (physics(400)["earth_ir_wm2"] / SIGMA) ** 0.25 - 273.15,
    }

    epochs = sorted(s["epoch"] for s in sats)
    pipeline = {"raw": len(raw), "with_orbit": len(sats), "low": sum(s["band"] == "low" for s in sats),
                "sampled": len(points), "groups": sum(g["count"] for g in groups if g["name"] not in ("Geostationary belt", "Space station"))}

    checks = run_checks(raw, raw_bytes, sats, geo, iss, atm, budget, bands, pipeline)

    def rnd(d, nd=4):
        return {k: (round(v, nd) if isinstance(v, float) else v) for k, v in d.items()}

    out = {
        "source": {
            "publisher": "CelesTrak (T.S. Kelso)",
            "title": "Current GP element sets, Active satellites, CSV",
            "url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=csv",
            "accessed": ACCESSED,
            "sha256": RAW_SHA256,
            "epoch_oldest": epochs[0][:10], "epoch_newest": epochs[-1][:10],
        },
        "model": {"name": "NRLMSIS 2.1", "package": f"pymsis {pymsis.__version__}",
                  "conditions": "equator, local noon, quiet geomagnetic field (Ap 4)", "solar_levels": SOLAR_LEVELS},
        "constants": {"mu_km3s2": MU, "earth_radius_km": RE, "c_kms": C, "solar_wm2": SOLAR, "earth_ir_wm2": EARTH_IR,
                      "albedo": ALBEDO, "min_elevation_deg": MIN_ELEVATION},
        "pipeline": pipeline,
        "total": len(sats),
        "bands": [rnd(b, 1) for b in bands],
        "histogram": hist,
        "groups": [rnd(g, 2) for g in groups],
        "points": points,
        "curve": [rnd(c, 5) for c in curve],
        "atmosphere": atm,
        "budget": budget,
        "temperatures_c": {k: round(v, 1) for k, v in temps.items()},
        "checks": checks,
    }
    (HERE / "summary.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + ": " + c["detail"])
    sys.exit(1 if any(not c["ok"] for c in checks) else 0)


def run_checks(raw, raw_bytes, sats, geo, iss, atm, budget, bands, pipeline):
    checks = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    sha = hashlib.sha256(raw_bytes).hexdigest()
    check("raw file unchanged", sha == RAW_SHA256, f"sha256 {sha[:12]}...")
    check("raw shape", len(raw) == 16872 and len(raw[0]) == 17, f"{len(raw):,} rows x {len(raw[0])} columns")

    ok_ids = len({s["id"] for s in sats}) == len(sats)
    ok_vals = all(s["period"] > 80 and 0 <= s["ecc"] < 1 and s["peri"] > 100 for s in sats)
    check("every satellite has one catalog number and a real orbit", ok_ids and ok_vals,
          "no duplicate catalog numbers; periods above 80 minutes; perigees above 100 km")

    # Textbook geostationary altitude is 35,786 km (semi-major axis 42,164 km).
    geo_alts = [s["alt"] for s in geo]
    med = float(np.median(geo_alts))
    check("24-hour satellites sit at the textbook geostationary altitude", abs(med - 35786) < 20 and len(geo) > 400,
          f"{len(geo)} satellites with a day-long period; median altitude {med:,.0f} km (textbook 35,786 km)")

    # NASA publishes the station's orbit as roughly 400 to 420 km.
    check("space station altitude matches NASA's published orbit", 395 <= iss["alt"] <= 430,
          f"{iss['alt']:.0f} km, {iss['period']:.1f} minutes per orbit, {iss['speed']:.2f} km/s")

    # Round trip: 4 legs of 35,786 km at the speed of light is about 477 ms.
    ping = 4 * 35786 / C * 1000
    check("geostationary light time works out to about half a second", 470 < ping < 485, f"{ping:.0f} ms")

    # Atmosphere: the standard sea-level air density is 1.225 kg/m^3 (ICAO / US Standard Atmosphere).
    mod = {r["alt"]: r for r in atm["moderate"]}
    sea = mod[0]["density"]
    check("model air density at sea level matches the standard atmosphere", abs(sea / 1.225 - 1) < 0.06,
          f"{sea:.3f} kg/m3 against the standard 1.225 kg/m3")
    ratio = sea / mod[400]["density"]
    check("air at 400 km is about a trillion times thinner than at sea level", 1e11 < ratio < 1e13,
          f"{ratio:.1e} times thinner at moderate solar activity")

    hot = max(r["temp_k"] for rows in atm.values() for r in rows if r["alt"] >= 300)
    check("the thermosphere really is hot", 1000 < hot < 2000, f"up to {hot:,.0f} K ({hot-273:,.0f} C) at high solar activity")

    worst = max(max(b["air_ram"].values()) + max(b["air_thermal"].values()) for b in budget if b["alt"] >= 400)
    check("above 400 km the air delivers under 1% of what sunlight does", worst < 0.01 * SOLAR,
          f"worst case {worst:.2f} W/m2 against {SOLAR:.0f} W/m2 of sunlight")

    check("orbit bands add up to the catalog", sum(b["count"] for b in bands) == len(sats),
          " + ".join(f"{b['count']:,} {b['band']}" for b in bands) + f" = {len(sats):,}")

    epochs = sorted(s["epoch"] for s in sats)
    check("element sets are fresh", epochs[0] >= "2026-09-20", f"oldest {epochs[0][:10]}, newest {epochs[-1][:10]}")

    check("pipeline reconciles", pipeline["with_orbit"] == pipeline["raw"] == len(sats),
          f"{pipeline['raw']:,} rows in, {pipeline['with_orbit']:,} orbits out, {pipeline['sampled']:,} drawn")
    return checks


if __name__ == "__main__":
    main()
