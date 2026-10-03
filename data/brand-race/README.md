# EPA data behind the Brand Race page

Every number on the Brand Race page ([brand-race.html](../../brand-race.html)) comes from the files in this folder.

| File | What it is |
|---|---|
| `raw/epa-trends-by-manufacturer.csv` | The untouched EPA export (see Source). Not edited by hand. Kept out of the repo; download it from EPA as described below and check its SHA-256. |
| `build_summary.py` | Reads the raw CSV, keeps the All/Car/Truck rows for the snapshot years, skips EPA's empty placeholder rows, ranks brands within each year, runs 26 checks, and writes `summary.json`. Exits with an error if any check fails. |
| `summary.json` | What the page charts: one row per brand, view and snapshot year (0–60, horsepower, MPG, weight, production, ranks), the industry row, the 14 brands' share of sales, and the check results. |
| `review.html` | One-page review of every number in `summary.json`, for sign-off before the charts are built. |

Run: download the CSV (see Source), save it as `raw/epa-trends-by-manufacturer.csv`, then `python build_summary.py` (standard library only). The script stops if the file's fingerprint doesn't match. EPA updates this data each year, so a later download will differ.

## Source

**EPA Automotive Trends Report data**, U.S. Environmental Protection Agency, [Explore the Automotive Trends Data](https://www.epa.gov/automotive-trends/explore-automotive-trends-data). Section "Explore Trends Detailed Data", table A, tab "A-1. View by Manufacturer", blue export button. Accessed October 3, 2026.

- 5,661 rows, 57 columns. Model years 1975 to 2025 (EPA labels 2025 "Prelim. 2025").
- 14 automakers at the parent-company level (for example, GM includes Chevrolet, Cadillac and GMC): BMW, Ford, GM, Honda, Hyundai, Kia, Mazda, Mercedes, Nissan, Stellantis, Subaru, Tesla, Toyota, VW. Plus an "All" industry total.
- One row per automaker, model year and vehicle type. Vehicle type "All" is EPA's production-weighted average for the automaker's whole lineup.
- Values are production-weighted averages of new vehicles. EPA estimates 0–60 times from vehicle specs; they start in model year 1978.
- SHA-256 of the raw file: `391a3bc9e939cc9dc751affda191b933c22801d90a76c088d48a734bb2cc9872`

## Decisions

| Date | Decision |
|---|---|
| 2026-10-03 | Scoreboard: 0–60 time, horsepower, real-world MPG. |
| 2026-10-03 | Include every automaker in the data. |
| 2026-10-03 | Snapshot years: 1980, 1990, 2000, 2010, 2020, 2025. |
| 2026-10-03 | Output: a portfolio page, built like the Data Analysis page. |
| 2026-10-03 | Chart types: bump chart, scatter plot, heatmap. |
| 2026-10-03 | Raw CSV stays out of the public repo (the pre-commit check blocks .csv files); the README keeps the download steps and SHA-256 instead. |
| 2026-10-03 | Bump chart: buttons switch the ranking between 0–60, horsepower and MPG. |
| 2026-10-03 | Late entrants (first year with production in the data: Hyundai 1986, Kia 1994, Tesla 2012) join the bump chart at their first snapshot (1990, 2000, 2020) with an "enters" marker. Ranks are out of the brands present that year. EPA's empty placeholder rows before a brand's first year are skipped, not treated as zero. |
| 2026-10-03 | Bump chart colors: every brand gets its own color, with its name labeled at the line's end. |
| 2026-10-03 | Scatter plot: horsepower vs. 0–60 time. |
| 2026-10-03 | Scatter plot time: then vs. now, a 1980 dot and a 2025 dot per brand joined by an arrow. Hyundai, Kia and Tesla start their arrow at their first snapshot (1990, 2000, 2020), labeled with that year. |
| 2026-10-03 | Heatmap: buttons switch the color between 0–60, horsepower and MPG (same as the bump chart). Columns are the six snapshot years. |
| 2026-10-03 | Default view is brand totals (EPA Vehicle Type "All": production-weighted across the brand's whole lineup). A filter switches all charts between All, Cars ("All Car") and Trucks ("All Truck"). Car vs. truck is EPA's regulatory class, so most SUVs and crossovers count as trucks. |
| 2026-10-03 | When a brand is missing for a snapshot and then returns (Subaru in the Trucks view: 1980, none in 1990, back in 2000), the bump chart joins the points with a dotted line, with a note saying it had no entry that year. It isn't ranked in the missing year. |
| 2026-10-03 | MPG stays exactly as EPA reports it, including electric vehicles at their energy-equivalent rating. Tesla (119.4 in 2025) ranks #1 on merit. The page notes that EV figures are energy-equivalent, and the MPG scale breaks so the other brands stay readable. |
| 2026-10-03 | 2025 stays as the last snapshot, labeled "2025 (prelim.)" in a lighter style, with a footnote: EPA's 2025 data are preliminary, based on automakers' projected production before the model year; 1975–2024 are final. |

## Known limitations

- Brand totals reflect each brand's sales mix. A brand that sells mostly trucks averages slower and thirstier even if its cars are quick.
- Model year 2025 is preliminary. Its rows have the averages but no production counts.
- In the Trucks view, several brands have no trucks in early snapshots (BMW, Honda, Kia, Mercedes before 2000; Hyundai before 2010). Subaru had trucks in 1980, none in 1990, and trucks again from 2000.
