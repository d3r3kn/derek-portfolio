# Medicaid data behind the Data Analysis page

Every number on [data-analysis.html](../../data-analysis.html) comes from the files in this folder.

| File | What it is |
|---|---|
| `build_summary.py` | Reads the prepared Parquet file and writes `summary.json`: totals by month, procedure code, billing provider, and billing/servicing match. Runs the checks listed below and exits with an error if any fail. |
| `summary.json` | The aggregates the page charts. The only provider IDs in it are the top 20 billing NPIs for each date range. |
| `lookup_names.py` | Looks up those top NPIs in the public [CMS NPI Registry](https://npiregistry.cms.hhs.gov/) and writes `npi_names.json`. |
| `code_labels.json` | Short procedure descriptions, taken from HHS's own example chart for this dataset. |
| `hhs/` | HHS's published example-chart data for this release, used as an independent check. |

## Source

**Medicaid Provider Spending by HCPCS**, U.S. Department of Health and Human Services, [HHS Open Data](https://opendata.hhs.gov/datasets/medicaid-provider-spending/). Version published February 9, 2026; accessed May 19, 2026.

## Preparation

1. Download the official CSV (238,015,729 rows).
2. Convert to Parquet.
3. Standardize: missing NPIs set to `UNKNOWN`, `CLAIM_FROM_MONTH` cast to a date (`CLAIM_MONTH`).
4. Remove HCPCS code `20` (34 rows totaling about $20.28 trillion, roughly four times all U.S. health spending in 2024; treated as a data error).
5. Result: 238,015,695 rows, about $1.52 trillion.

## Checks run by `build_summary.py`

- Monthly totals sum to the overall total; all 84 months present.
- Each year's total matches the original exploration notebook.
- Every year's billing/servicing split sums to that year's total.
- Provider spending ranges plus spending with no billing provider sum to the total.
- Raw rows and dollars minus code 20 equal the final set.
- Recomputed on HHS's window (FY2019 to FY2024), the top 20 procedures, top 20 billing providers, and all 72 monthly totals match HHS's published example charts to the cent.

## Run

```bash
python build_summary.py path/to/filtered_data.parquet path/to/cleaned_data.parquet
python lookup_names.py
```

Requires `duckdb`. The full exploration notebook is available on request.
