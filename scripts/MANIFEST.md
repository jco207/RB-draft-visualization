# Script Manifest

This file tracks every script in `scripts/`, its purpose, its dependencies,
and what (if anything) depends on it. Update this table whenever a script is
added, removed, or its inputs/outputs change.

| Script | What it does | Depends on | Depended on by |
|--------|-------------|------------|----------------|
| `clean_draft.py` | Parses the raw multi-round draft CSV, normalises it into a flat table, adds `Round`, `Pick-Num`, `Position`, `Keeper`, and `Starred` columns, prints a data-quality report, and writes `<input>-cleaned.csv`. | `pandas` · raw draft CSV | `dashboard.py` |
| `dashboard.py` | Streamlit dashboard with sidebar filters (round, position, keeper, total/active fantasy points, rank), an Altair bar chart of Total Fantasy Points per pick, a data table, and a CSV download button. | `pandas` · `streamlit` · `altair` · cleaned CSV produced by `clean_draft.py` | — |

## Running scripts

```bash
# Activate the virtual environment first
source venv/bin/activate

# 1. Clean the raw draft data
python scripts/clean_draft.py 2025_Pre-season_Pre-season.csv

# 2. Launch the dashboard (requires the cleaned CSV from step 1)
streamlit run scripts/dashboard.py

# Help for any script
python scripts/clean_draft.py --help
python scripts/dashboard.py --help
```
