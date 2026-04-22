# Script Manifest

This file tracks every script in `scripts/`, its purpose, its dependencies,
and what (if anything) depends on it. Update this table whenever a script is
added, removed, or its inputs/outputs change.

| Script | What it does | Depends on | Depended on by |
|--------|-------------|------------|----------------|
| `clean_draft.py` | Auto-detects the input CSV format (A/B/C) and normalises it into a flat table with consistent columns: `Round`, `Pick`, `Pick-Num`, `Team`, `Player`, `Position`, `Keeper`, `Starred`, `Elapsed Time`, `Rank`, `Total Fpts`, `Active Fpts`. Prints a data-quality report and writes `<input>-cleaned.csv`. | `pandas` · raw draft CSV (Format A: 2025; Format B: 2019–2024; Format C: external files with Elig column) | `dashboard.py` |
| `dashboard.py` | Streamlit dashboard with a sidebar year picker; sidebar filters (round, position, team, keeper status, total/active fantasy points range, rank); a metric toggle (Total Fpts / Active Fpts / VBD); an Altair bar chart of the selected metric per pick with x-axis labels grouped by round; a team totals bar chart; Best & Worst Pick by Round and by Team tables (when fpts data is present); a data table with VBD and VBD/g columns; and a CSV download button. Auto-detects the most recent cleaned CSV in `data/`. VBD baseline = *t*-th ranked player at each position (⌊*t* × 1.5⌋ for RB/WR); VBD/g = VBD ÷ 17. | `pandas` · `streamlit` · `altair` · cleaned CSV produced by `clean_draft.py` | — |

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
