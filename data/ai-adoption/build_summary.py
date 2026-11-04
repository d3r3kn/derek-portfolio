"""Build summary.json for the AI adoption page from the two raw files and the
figures typed from publishers' pages. Needs openpyxl. Stops if any check fails."""
import hashlib
import json
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
GALLUP = HERE / "raw" / "AI-Use-Trends-by-Industry.xlsx"
CENSUS = HERE / "raw" / "Sector.xlsx"
GALLUP_SHA = "b124cdc77cb991b18a979b146a238082229deb09efa2664e553f3b7f0afec1b9"
CENSUS_SHA = "5e83d18cfd20408e5055dadbe5a32626f280192d993cc7df2b0c20a292194649"
PERIOD = "202609"  # collected Apr 20 to May 3, 2026, before the Sept 2026 renaming order
WAVES = ["Q2 2023", "Q2 2024", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026", "Q2 2026"]
# Middle of each wave's field dates, so the chart's time axis is true to the calendar.
WAVE_DATES = ["2023-05-18", "2024-05-18", "2025-05-11", "2025-08-12", "2025-11-07", "2026-02-11", "2026-05-13"]
SECTORS = {
    "11": "Agriculture", "21": "Mining", "22": "Utilities", "23": "Construction",
    "31": "Manufacturing", "42": "Wholesale trade", "44": "Retail trade",
    "48": "Transportation and warehousing", "51": "Information",
    "52": "Finance and insurance", "53": "Real estate",
    "54": "Professional services", "55": "Management of companies",
    "56": "Administrative and support", "61": "Educational services",
    "62": "Health care and social assistance", "71": "Arts and recreation",
    "72": "Accommodation and food", "81": "Other services",
}

checks = []


def check(name, ok):
    checks.append({"name": name, "ok": bool(ok)})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_gallup():
    ws = openpyxl.load_workbook(GALLUP, data_only=True, read_only=True)["Sheet1"]
    out, cur = {}, None
    for row in ws.iter_rows(values_only=True):
        v = [c for c in row if c is not None]
        if len(v) == 1:
            cur = v[0]
            out[cur] = []
        elif len(v) == 4 and isinstance(v[1], (int, float)):
            out[cur].append({"wave": v[0], "daily": round(v[1] * 100), "frequent": round(v[2] * 100), "total": round(v[3] * 100)})
    return out


def read_census():
    wb = openpyxl.load_workbook(CENSUS, data_only=True, read_only=True)
    est = list(wb["Response Estimates"].iter_rows(values_only=True))
    err = list(wb["Response Standard Errors"].iter_rows(values_only=True))
    head = [str(c) for c in est[0]]
    col = head.index(PERIOD)
    se = {r[0]: r[col] for r in err[1:] if r[1] == 7 and r[4] == "Yes"}
    rows, suppressed, first_filled = [], [], None
    for r in est[1:]:
        if r[1] != 7 or r[4] != "Yes" or str(r[0]) == "XX":
            continue
        filled = [head[i] for i in range(5, len(head)) if r[i] not in (".", None)]
        if filled:
            first_filled = min([first_filled, min(filled)]) if first_filled else min(filled)
        name = SECTORS[str(r[0])]
        if r[col] == "S":
            suppressed.append(name)
            continue
        rows.append({"sector": name, "pct": float(r[col].rstrip("%")), "se": float(se[r[0]].rstrip("%"))})
    rows.sort(key=lambda x: -x["pct"])
    return rows, suppressed, first_filled


def main():
    pub = json.loads((HERE / "published_figures.json").read_text(encoding="utf-8"))
    check("Gallup file fingerprint matches", sha(GALLUP) == GALLUP_SHA)
    check("Census file fingerprint matches", sha(CENSUS) == CENSUS_SHA)

    g = read_gallup()
    check("Gallup file has 10 industries", len(g) == 10)
    check("Every industry has all 7 waves, in order", all([x["wave"] for x in v] == WAVES for v in g.values()))
    flat = [x for v in g.values() for x in v]
    check("Every Gallup value is a percent from 0 to 100", all(0 <= x[k] <= 100 for x in flat for k in ("daily", "frequent", "total")))
    check("Daily is never above frequent, and frequent never above total", all(x["daily"] <= x["frequent"] <= x["total"] for x in flat))
    # Spot values read from Gallup's separate topline PDF and indicator page.
    check("Technology Q4 2025 matches Gallup's topline", g["Technology"][4] == {"wave": "Q4 2025", "daily": 31, "frequent": 57, "total": 77})
    check("Finance Q2 2023 matches Gallup's topline", g["Finance"][0] == {"wave": "Q2 2023", "daily": 4, "frequent": 10, "total": 23})
    check("Retail Q2 2024 matches Gallup's topline", g["Retail"][1] == {"wave": "Q2 2024", "daily": 5, "frequent": 12, "total": 21})
    top3 = (g["Technology"][6]["daily"], g["Finance"][6]["daily"], g["Professional Services"][6]["daily"])
    check("Top three Q2 2026 daily rates match Gallup's indicator page", top3 == (42, 27, 22))
    others = [v[6]["daily"] for k, v in g.items() if k not in ("Technology", "Finance", "Professional Services")]
    check("The other seven Q2 2026 daily rates run 9 to 15, as Gallup says", min(others) == 9 and max(others) == 15)

    overall = pub["gallup_overall"]["waves"]
    check("Overall Gallup series has the same 7 waves", [w["wave"] for w in overall] == WAVES)
    check("Overall total never falls", all(a["total"] <= b["total"] for a, b in zip(overall, overall[1:])))

    sectors, suppressed, first = read_census()
    by = {r["sector"]: r["pct"] for r in sectors}
    story = pub["census_story"]
    check("Information matches the Census story", by["Information"] == story["information_pct"])
    check("Finance and insurance matches the Census story", by["Finance and insurance"] == story["finance_pct"])
    check("Census AI rows start at 202524, the reworded question", first == "202524")

    pts = [p["pct"] for p in pub["pew_chatgpt"]["points"]]
    check("Pew ChatGPT series is 18, 23, 34, 44", pts == [18, 23, 34, 44])
    m = [x["pct"] for x in pub["late_2025"]["measures"]]
    check("Late 2025 measures are sorted, 18 to 78", m == sorted(m) and m[0] == 18 and m[-1] == 78)
    check("Late 2025 Gallup measure equals the overall Q4 2025 total", m[3] == overall[4]["total"])

    failed = [c["name"] for c in checks if not c["ok"]]
    if failed:
        raise SystemExit("Checks failed: " + "; ".join(failed))

    order = sorted(g, key=lambda k: -g[k][6]["total"])
    summary = {
        "accessed": pub["accessed"],
        "waves": [{"wave": w, "date": d} for w, d in zip(WAVES, WAVE_DATES)],
        "overall": overall,
        "industries": [{"name": k, "series": g[k]} for k in order],
        "pew_chatgpt": pub["pew_chatgpt"]["points"],
        "pew_chatbots": {k: pub["pew_chatbots"][k] for k in ("pct_2024", "pct_2026", "daily_2026")},
        "rps": {k: pub["rps"][k] for k in ("aug_2026_any_use_18_64", "aug_2026_work_employed")},
        "late_2025": pub["late_2025"]["measures"],
        "census_sectors": {
            "period": PERIOD,
            "collected": "April 20 to May 3, 2026",
            "national_pct": story["national_pct"],
            "rows": sectors,
            "suppressed": suppressed,
        },
        "checks": checks,
    }
    text = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    (HERE / "summary.json").write_text(text, encoding="utf-8", newline="\n")
    print(len(checks), "checks passed;", len(sectors), "sectors; suppressed:", suppressed)


if __name__ == "__main__":
    main()
