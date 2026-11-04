# Data behind the AI Adoption page

Every number on the AI Adoption page ([ai-adoption.html](../../ai-adoption.html)) comes from the files in this folder.

| File | What it is |
|---|---|
| `raw/AI-Use-Trends-by-Industry.xlsx` | Gallup's untouched file. Kept out of the repo; download it from the link below and check its SHA-256. |
| `raw/Sector.xlsx` | Census's untouched Business Trends and Outlook Survey sector file. Kept out of the repo for the same reason. |
| `published_figures.json` | Figures typed from publishers' pages, with each source link. |
| `build_summary.py` | Reads the above, runs the checks, and writes `summary.json`. Stops if any check fails. |
| `summary.json` | What the page charts. |

Run: save both raw files in `raw/`, then `python build_summary.py` (needs openpyxl).

## Sources (all accessed 2026-11-04)

- Gallup, [AI Use Trends by Industry](https://www.gallup.com/file/education/712643/AI-Use-Trends-by-Industry.xlsx). 10 industries, 7 surveys, Q2 2023 to Q2 2026. SHA-256 `b124cdc77cb991b18a979b146a238082229deb09efa2664e553f3b7f0afec1b9`. A script's header-only check returned 404, but the file downloads normally.
- Census Bureau, [BTOS Sector.xlsx](https://www.census.gov/hfp/btos/downloads/Sector.xlsx), updated 2026-10-22. SHA-256 `5e83d18cfd20408e5055dadbe5a32626f280192d993cc7df2b0c20a292194649`. The file replaces itself every two weeks, so a later download will fail the fingerprint check. Update the fingerprint only after reviewing the new file.
- All other sources are linked in `published_figures.json` and on the page.

## Decisions

| Date | Decision |
|---|---|
| 2026-11-04 | Start in 2023, US data only. Eurostat reaches 2021 for firms but was left out. |
| 2026-11-04 | Main chart: Gallup AI use by industry, as small multiples on a true time axis. |
| 2026-11-04 | Page order: headline numbers, industries, frequency, adults, why numbers differ, Census snapshot. |
| 2026-11-04 | Census is one snapshot only: its AI rows in this file start 2025-11-17, after the wording change. |
| 2026-11-04 | Census period 202609 (Apr 20 to May 3, 2026): it can be checked against the Census story and predates Executive Order 14434. The page says AI and explains the newer "Super Intelligence or SI" label. |
| 2026-11-04 | ChatGPT and other company user counts are left out: they could not be confirmed with the companies. |
| 2026-11-04 | No user head count. Sources give shares, and a head count would be an estimate. |
| 2026-11-04 | Series are never joined across definitions or wording changes. |
