# Script Manifest

This file tracks every script in `scripts/`, its purpose, its dependencies,
and what (if anything) depends on it. Update this table whenever a script is
added, removed, or its inputs/outputs change.

| Script | What it does | Depends on | Depended on by |
|--------|-------------|------------|----------------|
| `clean_draft.py` | Auto-detects the input CSV format (A/B/C) and normalises it into a flat table with consistent columns: `Round`, `Pick`, `Pick-Num`, `Team`, `Player`, `Position`, `Keeper`, `Starred`, `Elapsed Time`, `Rank`, `Total Fpts`, `Active Fpts`. Prints a data-quality report and writes `<input>-cleaned.csv`. | `pandas` · raw draft CSV (Format A: 2025; Format B: 2021–2024; Format C: 2020) | `dashboard.py` |
| `dashboard.py` | Streamlit dashboard with sidebar filters (round, position, keeper, total/active fantasy points, rank), an Altair bar chart of Total Fantasy Points per pick, a team totals bar chart with metric toggle, a data table, and a CSV download button. Auto-detects the most recent cleaned CSV in `data/`. | `pandas` · `streamlit` · `altair` · cleaned CSV produced by `clean_draft.py` | — |

## Running scripts

```bash
# Activate the virtual environment first
source venv/bin/activate

# 1. Clean the raw draft data (format is auto-detected)
python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv
# or any other supported season
python scripts/clean_draft.py data/2021_Ballers_draft.csv

# 2. Launch the dashboard (requires the cleaned CSV from step 1)
streamlit run scripts/dashboard.py

# Help for any script
python scripts/clean_draft.py --help
python scripts/dashboard.py --help
```
