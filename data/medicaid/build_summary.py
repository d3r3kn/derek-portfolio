"""Build the summary numbers behind the Data Analysis page.

Input:  the filtered Parquet file (the HHS "Medicaid Provider Spending by HCPCS"
        release of Feb 9, 2026, converted to Parquet, missing NPIs set to
        'UNKNOWN', and HCPCS code '20' removed; see the page for each step).
Output: summary.json, aggregates only. The only provider IDs written are the
        top 20 billing NPIs by total paid, which the page names.

Usage:  python build_summary.py path/to/filtered_data.parquet [path/to/raw.parquet]
"""
import json
import sys
from pathlib import Path

import duckdb

PRESETS = {"all": (2018, 2024), "pre": (2018, 2020), "post": (2021, 2024)}
TOP_N = 20
BINS = [  # lower bound of each total-paid range, per billing provider
    ("Under $10K", None), ("$10K to $100K", 1e4), ("$100K to $1M", 1e5),
    ("$1M to $10M", 1e6), ("$10M to $100M", 1e7), ("Over $100M", 1e8),
]

# Yearly totals as printed by the original exploration notebook (cleaned data,
# code 20 included) minus its printed code-20 totals. Used as an independent check.
NOTEBOOK_YEARLY_PAID = {
    2018: 20383877394626.75 - 20231113688394.43,
    2019: 222929227068.29 - 49782181401.59,
    2020: 182725957403.39,
    2021: 220840385815.94 - 4765387.71,
    2022: 244655272048.06,
    2023: 276433297242.47,
    2024: 267938154373.65,
}


def main(src, raw=None):
    con = duckdb.connect()
    con.execute(f"CREATE VIEW f AS SELECT * FROM read_parquet('{src}')")

    # One scan per grain; everything else is derived from these small tables.
    con.execute("""
        CREATE TABLE monthly AS
        SELECT CLAIM_MONTH AS month, SUM(TOTAL_PAID) AS paid, SUM(TOTAL_CLAIM_LINES) AS claims,
               SUM(TOTAL_PATIENTS) AS patients, COUNT(*) AS n_rows
        FROM f GROUP BY 1 ORDER BY 1""")
    con.execute("""
        CREATE TABLE yearly_code AS
        SELECT YEAR(CLAIM_MONTH) AS yr, HCPCS_CODE AS code, SUM(TOTAL_PAID) AS paid,
               SUM(TOTAL_CLAIM_LINES) AS claims, SUM(TOTAL_PATIENTS) AS patients, COUNT(*) AS n_rows
        FROM f GROUP BY 1, 2""")
    con.execute("""
        CREATE TABLE yearly_billing AS
        SELECT YEAR(CLAIM_MONTH) AS yr, BILLING_PROVIDER_NPI_NUM AS npi, SUM(TOTAL_PAID) AS paid,
               SUM(TOTAL_CLAIM_LINES) AS claims, COUNT(*) AS n_rows
        FROM f GROUP BY 1, 2""")
    con.execute("""
        CREATE TABLE yearly_split AS
        SELECT YEAR(CLAIM_MONTH) AS yr,
               CASE WHEN BILLING_PROVIDER_NPI_NUM = 'UNKNOWN' THEN 'billing_not_listed'
                    WHEN SERVICING_PROVIDER_NPI_NUM = 'UNKNOWN' THEN 'servicing_not_listed'
                    WHEN BILLING_PROVIDER_NPI_NUM = SERVICING_PROVIDER_NPI_NUM THEN 'same'
                    ELSE 'different' END AS kind,
               SUM(TOTAL_PAID) AS paid, COUNT(*) AS n_rows
        FROM f GROUP BY 1, 2""")
    con.execute("""
        CREATE TABLE quality AS
        SELECT COUNT(*) AS n_rows, SUM(TOTAL_PAID) AS paid,
               COUNT(*) FILTER (WHERE TOTAL_PAID < 0) AS neg_rows,
               SUM(TOTAL_PAID) FILTER (WHERE TOTAL_PAID < 0) AS neg_paid,
               COUNT(*) FILTER (WHERE TOTAL_PAID = 0) AS zero_rows,
               COUNT(*) FILTER (WHERE BILLING_PROVIDER_NPI_NUM = 'UNKNOWN') AS billing_unknown_rows,
               COUNT(*) FILTER (WHERE SERVICING_PROVIDER_NPI_NUM = 'UNKNOWN') AS servicing_unknown_rows,
               MIN(CLAIM_MONTH) AS first_month, MAX(CLAIM_MONTH) AS last_month
        FROM f""")

    q = lambda sql, *a: con.execute(sql, a).fetchall()
    out = {"source": {"dataset": "Medicaid Provider Spending by HCPCS", "version": "2026-02-09",
                      "accessed": "2026-05-19", "url": "https://opendata.hhs.gov/datasets/medicaid-provider-spending/"}}

    (n_rows, paid, neg_rows, neg_paid, zero_rows, b_unk, s_unk, first, last) = q("SELECT * FROM quality")[0]
    out["quality"] = {"rows": n_rows, "paid": paid, "negative_rows": neg_rows, "negative_paid": neg_paid,
                      "zero_paid_rows": zero_rows, "billing_unknown_rows": b_unk,
                      "servicing_unknown_rows": s_unk, "first_month": str(first), "last_month": str(last)}
    if raw:
        r = q(f"SELECT COUNT(*), SUM(TOTAL_PAID), COUNT(*) FILTER (WHERE HCPCS_CODE = '20'), "
              f"SUM(TOTAL_PAID) FILTER (WHERE HCPCS_CODE = '20') FROM read_parquet('{raw}')")[0]
        out["pipeline"] = {"raw_rows": r[0], "raw_paid": r[1], "code20_rows": r[2], "code20_paid": r[3],
                           "final_rows": n_rows, "final_paid": paid}

    out["monthly"] = [{"month": str(m)[:7], "paid": p, "claims": c, "patients": pt}
                      for m, p, c, pt, _ in q("SELECT * FROM monthly")]

    out["split"] = {}
    for yr, kind, p, _ in q("SELECT * FROM yearly_split ORDER BY yr, kind"):
        out["split"].setdefault(str(yr), {})[kind] = p

    out["presets"] = {}
    for key, (y0, y1) in PRESETS.items():
        pr = {"years": [y0, y1]}
        pr["billing_providers"] = q("SELECT COUNT(DISTINCT npi) FROM yearly_billing "
                                    "WHERE yr BETWEEN ? AND ? AND npi <> 'UNKNOWN'", y0, y1)[0][0]
        pr["billing_providers_by_year"] = dict((str(y), n) for y, n in q(
            "SELECT yr, COUNT(DISTINCT npi) FROM yearly_billing WHERE yr BETWEEN ? AND ? "
            "AND npi <> 'UNKNOWN' GROUP BY 1 ORDER BY 1", y0, y1))
        pr["top_codes"] = [dict(zip(["code", "paid", "claims", "patients"], r)) for r in q(
            "SELECT code, SUM(paid), SUM(claims), SUM(patients) FROM yearly_code "
            "WHERE yr BETWEEN ? AND ? GROUP BY 1 ORDER BY 2 DESC LIMIT ?", y0, y1, TOP_N)]
        pr["top_billing"] = [dict(zip(["npi", "paid", "claims"], r)) for r in q(
            "SELECT npi, SUM(paid), SUM(claims) FROM yearly_billing WHERE yr BETWEEN ? AND ? "
            "AND npi <> 'UNKNOWN' GROUP BY 1 ORDER BY 2 DESC LIMIT ?", y0, y1, TOP_N)]
        totals = [t for (t,) in q("SELECT SUM(paid) FROM yearly_billing WHERE yr BETWEEN ? AND ? "
                                  "AND npi <> 'UNKNOWN' GROUP BY npi", y0, y1)]
        bins = [{"label": lbl, "providers": 0, "paid": 0.0} for lbl, _ in BINS]
        for t in totals:
            i = max(i for i, (_, lo) in enumerate(BINS) if lo is None or t >= lo)
            bins[i]["providers"] += 1
            bins[i]["paid"] += t
        totals.sort()
        median = totals[len(totals) // 2]
        pr["distribution"] = {"bins": bins, "median_provider_paid": median,
                              "median_bin": max(i for i, (_, lo) in enumerate(BINS) if lo is None or median >= lo)}
        out["presets"][key] = pr

    checks = run_checks(out, con)
    out["checks"] = checks
    Path(__file__).with_name("summary.json").write_text(json.dumps(out, indent=1, default=float))
    failed = [c for c in checks if not c["ok"]]
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + ": " + c["detail"])
    sys.exit(1 if failed else 0)


def run_checks(out, con):
    checks = []
    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
    close = lambda a, b: abs(a - b) <= max(1.0, abs(b) * 1e-9)

    total = out["quality"]["paid"]
    check("monthly sums to total", close(sum(m["paid"] for m in out["monthly"]), total),
          f"{sum(m['paid'] for m in out['monthly']):,.2f} vs {total:,.2f}")
    check("84 months present", len(out["monthly"]) == 84, f"{len(out['monthly'])} months")
    yearly = {}
    for m in out["monthly"]:
        yearly[int(m["month"][:4])] = yearly.get(int(m["month"][:4]), 0) + m["paid"]
    for y, exp in NOTEBOOK_YEARLY_PAID.items():
        check(f"{y} matches notebook", close(yearly[y], exp), f"{yearly[y]:,.2f} vs {exp:,.2f}")
    for y, parts in out["split"].items():
        check(f"split {y} sums to year", close(sum(parts.values()), yearly[int(y)]),
              f"{sum(parts.values()):,.2f} vs {yearly[int(y)]:,.2f}")
    unk = con.execute("SELECT SUM(paid) FROM yearly_billing WHERE npi = 'UNKNOWN'").fetchone()[0]
    dist = sum(b["paid"] for b in out["presets"]["all"]["distribution"]["bins"])
    check("distribution + unknown billing = total", close(dist + unk, total), f"{dist + unk:,.2f} vs {total:,.2f}")
    # HHS publishes its own example charts for this release (data from opendata.hhs.gov
    # saved under hhs/). Recompute them on the same window and filters; they must match.
    hhs = Path(__file__).with_name("hhs")
    if hhs.is_dir():
        fy = "CLAIM_MONTH BETWEEN DATE '2018-10-01' AND DATE '2024-09-01'"
        comparisons = [
            ("top-procedures.json", "hcpcsCode", f"SELECT HCPCS_CODE, SUM(TOTAL_PAID) FROM f WHERE {fy} GROUP BY 1 ORDER BY 2 DESC LIMIT 20"),
            ("top-providers.json", "npi", f"SELECT BILLING_PROVIDER_NPI_NUM, SUM(TOTAL_PAID) FROM f WHERE {fy} "
                                          "AND BILLING_PROVIDER_NPI_NUM <> 'UNKNOWN' GROUP BY 1 ORDER BY 2 DESC LIMIT 20"),
            ("monthly-spending.json", "month", f"SELECT strftime(CLAIM_MONTH, '%Y-%m'), SUM(TOTAL_PAID) FROM f WHERE {fy} "
                                               "AND BILLING_PROVIDER_NPI_NUM <> 'UNKNOWN' AND SERVICING_PROVIDER_NPI_NUM <> 'UNKNOWN' "
                                               "GROUP BY 1 ORDER BY 1"),
        ]
        for fname, key, sql in comparisons:
            theirs = json.loads((hhs / fname).read_text())
            ours = con.execute(sql).fetchall()
            same_order = [t[key] for t in theirs] == [k for k, _ in ours]
            worst = max(abs(v - t["totalPaid"]) for t, (_, v) in zip(theirs, ours))
            check(f"matches HHS {fname}", same_order and worst <= 1.0,
                  f"{len(theirs)} items, same order: {same_order}, largest difference ${worst:,.2f}")
    if "pipeline" in out:
        p = out["pipeline"]
        check("pipeline rows reconcile", p["raw_rows"] - p["code20_rows"] == p["final_rows"],
              f"{p['raw_rows']:,} - {p['code20_rows']:,} = {p['final_rows']:,}")
        check("pipeline dollars reconcile", close(p["raw_paid"] - p["code20_paid"], p["final_paid"]),
              f"{p['raw_paid'] - p['code20_paid']:,.2f} vs {p['final_paid']:,.2f}")
    return checks


if __name__ == "__main__":
    main(*sys.argv[1:3])
