# RB-draft-visualization

Visualization of Real Ballerz fantasy football draft.

## Setup

Requires Python 3.10+.

```bash
bash setup_venv.sh
source venv/bin/activate
```

This creates a virtual environment and installs all dependencies (`pandas`, `streamlit`, `altair`, `pytest`, `pytest-bdd`).

---

## Scripts

### `scripts/clean_draft.py` — Data Cleaner

Reads the raw multi-round draft CSV and normalises it into a flat table. Adds computed columns, strips formatting artifacts, and writes a cleaned CSV alongside a data quality report.

**Added columns:**

| Column | Description |
|--------|-------------|
| `Round` | Round number (1–15) |
| `Pick-Num` | Overall sequential pick: `((Round - 1) × 12) + Pick` |
| `Position` | Extracted from the player string (QB / RB / WR / TE / K / DST) |
| `Keeper` | `True` if the pick was flagged as `(Keeper)` |
| `Starred` | `True` if the player was prefixed with `*` in the raw data |

**Usage:**

```bash
python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv
python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv --output path/to/output.csv
python scripts/clean_draft.py --help
```

Output is saved as `<input-stem>-cleaned.csv` beside the input file by default.

---

### `scripts/dashboard.py` — Streamlit Dashboard

Interactive dark-themed dashboard for exploring the cleaned draft data.

**Features:**
- Sidebar filters by round, position, keeper status, total/active fantasy points, and rank
- Bar chart of total fantasy points per overall pick number, coloured by position
- Filterable data table
- Download button to export the current filtered view as CSV

**Usage:**

```bash
# Auto-detects the cleaned CSV in the project root
streamlit run scripts/dashboard.py

# Specify a cleaned CSV explicitly
streamlit run scripts/dashboard.py -- --data path/to/cleaned.csv

# Show help
python scripts/dashboard.py --help
```

> **Note:** Run `clean_draft.py` first — the dashboard requires the cleaned CSV.

---

## Running both scripts end-to-end

```bash
source venv/bin/activate
python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv
streamlit run scripts/dashboard.py
```

---

## Testing

Tests are written in Gherkin format (`.feature` files) with step definitions in `pytest-bdd`.

```bash
source venv/bin/activate
pytest tests/
```

Feature files and what they cover:

| File | Covers |
|------|--------|
| `tests/features/clean_draft.feature` | Column presence, Pick-Num formula, separator/header row removal, keeper/position/asterisk extraction |
| `tests/features/dashboard.feature` | App load, widget rendering, download button, `--help` flag, slider safety, position filter completeness |

To add a test for a new defect: add a `Scenario:` to the relevant `.feature` file, verify it fails, fix the code, then verify it passes. See `.claude/skills/draft-visualization.md` for the full coding standards.

---

## Project structure

```
.
├── setup_venv.sh                          # One-shot venv + dependency setup
├── requirements.txt
├── data/
│   ├── 2025_Pre-season_Pre-season.csv     # Raw draft export
│   └── 2025_Pre-season_Pre-season-cleaned.csv  # Produced by clean_draft.py
├── scripts/
│   ├── clean_draft.py                     # Data cleaning script
│   ├── dashboard.py                       # Streamlit dashboard
│   └── MANIFEST.md                        # Script dependency table
├── tests/
│   ├── conftest.py                        # Shared pytest fixtures
│   ├── features/
│   │   ├── clean_draft.feature
│   │   └── dashboard.feature
│   └── step_defs/
│       ├── test_clean_draft.py
│       └── test_dashboard.py
└── .claude/
    └── skills/
        └── draft-visualization.md         # Project coding standards
```
