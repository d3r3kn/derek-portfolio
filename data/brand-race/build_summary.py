"""Build the numbers behind the Brand Race page.

Input:  raw/epa-trends-by-manufacturer.csv, the untouched EPA Automotive Trends
        export (Detailed Data, A-1 View by Manufacturer; see README.md).
Output: summary.json: one row per brand, view and snapshot year with 0-60,
        horsepower and real-world MPG, each brand's rank within that year, the
        industry ("All") row for comparison, and the results of every check.

Usage:  python build_summary.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw" / "epa-trends-by-manufacturer.csv"
RAW_SHA256 = "391a3bc9e939cc9dc751affda191b933c22801d90a76c088d48a734bb2cc9872"

SNAPSHOTS = [1980, 1990, 2000, 2010, 2020, 2025]
PRELIMINARY = {"Prelim. 2025": 2025}
VIEWS = {"all": "All", "cars": "All Car", "trucks": "All Truck"}  # page filter -> EPA Vehicle Type
METRICS = {  # key -> (EPA column, better, decimals)
    "zero60": ("Acceleration (0-60 time in seconds)", "lower", 2),
    "hp": ("Horsepower (HP)", "higher", 1),
    "mpg": ("Real-World MPG", "higher", 1),
}
CONTEXT = {"weight": ("Weight (lbs)", 0), "production": ("Production (000)", 0)}
INDUSTRY = "All"


def num(s):
    s = s.strip().rstrip("%")
    return None if s in ("", "-") else float(s)


def year_of(label):
    return PRELIMINARY.get(label) or int(label)


def main():
    raw_bytes = RAW.read_bytes()
    with RAW.open(encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))
    by_key = {(r["Manufacturer"], year_of(r["Model Year"]), r["Vehicle Type"]): r for r in raw}

    rows, industry = [], []
    for view, vtype in VIEWS.items():
        for yr in SNAPSHOTS:
            present = []
            for (mfr, y, vt), r in by_key.items():
                if y != yr or vt != vtype:
                    continue
                vals = {k: num(r[col]) for k, (col, _, _) in METRICS.items()}
                if any(v is None for v in vals.values()):
                    continue  # EPA placeholder: no sales of this type that year
                entry = {"view": view, "brand": mfr, "year": yr, "preliminary": yr in PRELIMINARY.values(),
                         **vals, **{k: num(r[col]) for k, (col, _) in CONTEXT.items()}}
                (industry if mfr == INDUSTRY else present).append(entry)
            for key, (_, better, _) in METRICS.items():
                order = sorted(present, key=lambda e: e[key], reverse=(better == "higher"))
                for i, e in enumerate(order, 1):
                    e.setdefault("rank", {})[key] = i
            rows.extend(sorted(present, key=lambda e: e["brand"]))

    coverage = []
    for ind in industry:
        if ind["production"] is None:
            continue
        brands = sum(e["production"] for e in rows
                     if e["view"] == ind["view"] and e["year"] == ind["year"] and e["production"])
        coverage.append({"view": ind["view"], "year": ind["year"], "share": brands / ind["production"]})

    # Row counts after each preparation step, shown on the page.
    typed = [r for r in raw if r["Vehicle Type"] in VIEWS.values()]
    snap = [r for r in typed if year_of(r["Model Year"]) in SNAPSHOTS]
    pipeline = {"raw": len(raw), "vehicle_types": len(typed), "snapshots": len(snap),
                "with_values": len(rows) + len(industry), "brand_rows": len(rows), "industry_rows": len(industry)}

    checks = run_checks(raw, raw_bytes, by_key, rows, industry)
    check_placeholders = sum(1 for r in snap if any(num(r[c]) is None for c, _, _ in METRICS.values()))
    checks.append({"name": "pipeline reconciles",
                   "ok": pipeline["snapshots"] - check_placeholders == pipeline["with_values"],
                   "detail": f"{pipeline['snapshots']} snapshot rows - {check_placeholders} empty placeholders "
                             f"= {pipeline['with_values']} ({pipeline['brand_rows']} brand + {pipeline['industry_rows']} industry)"})

    def rounded(e):
        out = dict(e)
        for k, (_, _, d) in METRICS.items():
            out[k] = round(e[k], d)
        for k, (_, d) in CONTEXT.items():
            out[k] = None if e[k] is None else round(e[k], d)
        return out

    out = {
        "source": {
            "publisher": "U.S. Environmental Protection Agency",
            "title": "EPA Automotive Trends Report data: Detailed Data, A-1 View by Manufacturer",
            "url": "https://www.epa.gov/automotive-trends/explore-automotive-trends-data",
            "accessed": "2026-10-03",
            "sha256": RAW_SHA256,
        },
        "pipeline": pipeline,
        "snapshots": SNAPSHOTS,
        "preliminary": sorted(PRELIMINARY.values()),
        "views": VIEWS,
        "metrics": {k: {"column": c, "better": b} for k, (c, b, _) in METRICS.items()},
        "rows": [rounded(e) for e in rows],
        "industry": [rounded(e) for e in industry],
        "coverage": [{**c, "share": round(c["share"], 3)} for c in coverage],
        "checks": checks,
    }
    (HERE / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + ": " + c["detail"])
    sys.exit(1 if any(not c["ok"] for c in checks) else 0)


def run_checks(raw, raw_bytes, by_key, rows, industry):
    checks = []
    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    sha = hashlib.sha256(raw_bytes).hexdigest()
    check("raw file unchanged", sha == RAW_SHA256, f"sha256 {sha[:12]}...")
    check("raw shape", len(raw) == 5661 and len(raw[0]) == 57, f"{len(raw):,} rows x {len(raw[0])} columns")

    for view in VIEWS:
        for yr in SNAPSHOTS:
            group = [e for e in rows if e["view"] == view and e["year"] == yr]
            brands = [e["brand"] for e in group]
            n = len(group)
            dupes = len(brands) != len(set(brands))
            gaps = any(sorted(e["rank"][k] for e in group) != list(range(1, n + 1)) for k in METRICS)
            ties = any(len({e[k] for e in group}) != n for k in METRICS)
            ind = [e for e in industry if e["view"] == view and e["year"] == yr]
            check(f"{view} {yr}: ranks", not dupes and not gaps and not ties and len(ind) == 1,
                  f"{n} brands ranked 1-{n}, no duplicates or ties, industry row present")

    lo_hi = {"zero60": (2, 25), "hp": (50, 1000), "mpg": (5, 150)}
    bad = [(e["view"], e["brand"], e["year"], k, e[k]) for e in rows + industry
           for k, (lo, hi) in lo_hi.items() if not lo <= e[k] <= hi]
    check("values in sensible ranges", not bad,
          "0-60 2-25 s, HP 50-1000, MPG 5-150" + (f"; outside: {bad}" if bad else ""))

    expected = {"all": 77, "cars": 77, "trucks": 68}
    for view, n in expected.items():
        got = sum(e["view"] == view for e in rows)
        check(f"{view}: brand rows", got == n, f"{got} (expected {n})")

    # EPA's "All" row should be the production-weighted blend of its car and truck rows:
    # arithmetic for horsepower, harmonic for MPG (fuel use adds up, MPG does not).
    worst = {"hp": 0.0, "mpg": 0.0}
    tested = 0
    for (mfr, yr, vt), r in by_key.items():
        if vt != "All" or yr not in SNAPSHOTS:
            continue
        car, truck = by_key.get((mfr, yr, "All Car")), by_key.get((mfr, yr, "All Truck"))
        parts = [(num(p["Production (000)"]), num(p["Horsepower (HP)"]), num(p["Real-World MPG"]))
                 for p in (car, truck) if p]
        parts = [p for p in parts if None not in p and p[0] > 0]
        total = num(r["Production (000)"])
        if not parts or total is None:
            continue
        tested += 1
        prod = sum(p[0] for p in parts)
        hp = sum(p[0] * p[1] for p in parts) / prod
        mpg = prod / sum(p[0] / p[2] for p in parts)
        worst["hp"] = max(worst["hp"], abs(hp / num(r["Horsepower (HP)"]) - 1))
        worst["mpg"] = max(worst["mpg"], abs(mpg / num(r["Real-World MPG"]) - 1))
    check("brand totals = weighted cars + trucks", tested and max(worst.values()) < 0.01,
          f"{tested} brand-years; largest gap HP {worst['hp']:.2%}, MPG {worst['mpg']:.2%}")
    return checks


if __name__ == "__main__":
    main()
