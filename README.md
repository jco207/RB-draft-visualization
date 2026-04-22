# RB-draft-visualization

Visualization of Real Ballerz fantasy football draft.

## Setup

Requires Python 3.9+.

```bash
bash setup_venv.sh
source venv/bin/activate
```

This creates a virtual environment and installs all dependencies (`pandas`, `streamlit`, `altair`, `pytest`, `pytest-bdd`).

---

## Scripts

### `scripts/clean_draft.py` — Data Cleaner

Reads a raw draft CSV and normalises it into a flat table with a consistent schema. Auto-detects the input format based on CSV structure, supporting all seasons from 2019 onwards.

**Supported input formats:**

| Format | Years | Structure |
|--------|-------|-----------|
| A | 2025 | Alternating "Round N" separators + repeated headers; columns: Pick, Team, Player, Elapsed Time, Rank, Total Fpts, Active Fpts |
| B | 2019–2024 | Flat CSV with a single header row; columns: Round, Pick, Team, Player, Position, NFL Team (Elapsed Time, Total Fpts, Active Fpts present in some seasons) |
| C | — | Alternating "Round N" separators + repeated headers; columns: Pick, Team, Player, Elig, Elapsed Time (supported for external files with this structure) |

**Output columns (all formats):**

`Round`, `Pick`, `Pick-Num`, `Team`, `Player`, `Position`, `Keeper`, `Starred`, `Elapsed Time`, `Rank`, `Total Fpts`, `Active Fpts`

Columns unavailable in a given format are written as empty (NaN).

**Computed columns:**

| Column | Description |
|--------|-------------|
| `Pick-Num` | Overall sequential pick: `((Round - 1) × 12) + Pick` |
| `Position` | Extracted from the player string (QB / RB / WR / TE / K / DST / DEF) |
| `Keeper` | `True` if the pick was flagged as `(Keeper)` |
| `Starred` | `True` if the player was prefixed with `*` in the raw data |

**Usage:**

```bash
python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv
python scripts/clean_draft.py data/2021-draft.csv --output path/to/output.csv
python scripts/clean_draft.py --help
```

Output is saved as `<input-stem>-cleaned.csv` beside the input file by default.

---

### `scripts/dashboard.py` — Streamlit Dashboard

Interactive dark-themed dashboard for exploring the cleaned draft data.

**Features:**
- Sidebar year picker to switch between all available seasons
- Sidebar filters: round, position, team, keeper status (all / exclude / only), total/active fantasy points range, rank substring
- Metric toggle shared by all charts and tables: Total Fpts, Active Fpts, VBD
- Bar chart of fantasy points per overall pick number, coloured by position, with x-axis labels grouped by round
- Team totals bar chart sorted by the selected metric
- Best & Worst Pick by Round table (only shown when fantasy-points data is present)
- Best & Worst Pick by Team table (only shown when fantasy-points data is present)
- Filterable data table with VBD and VBD/g columns
- Download button to export the current filtered view as CSV

**VBD (Value Based Drafting):**

Each player's VBD = Total Fpts − positional baseline, where the baseline is the Total Fpts of the *t*-th ranked player at that position (*t* = number of teams). RB and WR use ⌊*t* × 1.5⌋ to account for flex roster spots. VBD/g divides VBD by 17 (games per season).

**Usage:**

```bash
# Auto-detects the most recent cleaned CSV in data/
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
# Clean any supported season (format is auto-detected)
python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv
python scripts/clean_draft.py data/2021-draft.csv
# Launch the dashboard (auto-detects the most recent cleaned CSV in data/)
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
| `tests/features/clean_draft.feature` | Column presence, Pick-Num formula, separator/header row removal, keeper/position/asterisk extraction (Format A / 2025) |
| `tests/features/clean_draft_formats.feature` | Multi-format support: output schema, NaN columns, Pick-Num, position, and asterisk handling for Format B (2021) and Format C (2020) |
| `tests/features/dashboard.feature` | App load, widget rendering, download button, `--help` flag, slider safety, position filter completeness |

To add a test for a new defect: add a `Scenario:` to the relevant `.feature` file, verify it fails, fix the code, then verify it passes. See `.claude/skills/draft-visualization.md` for the full coding standards.

---

## Project structure

```
.
├── setup_venv.sh                          # One-shot venv + dependency setup
├── requirements.txt
├── data/
│   ├── 2019-draft.csv                     # Raw draft exports (one per season)
│   ├── 2019-draft-cleaned.csv             # Produced by clean_draft.py
│   ├── 2020-draft.csv
│   ├── 2020-draft-cleaned.csv
│   ├── 2021-draft.csv
│   ├── 2021-draft-cleaned.csv
│   ├── 2022-draft.csv
│   ├── 2022-draft-cleaned.csv
│   ├── 2023-draft.csv
│   ├── 2023-draft-cleaned.csv
│   ├── 2024_Ballers_draft.csv
│   ├── 2024_Ballers_draft-cleaned.csv
│   ├── 2025_Pre-season_Pre-season.csv
│   └── 2025_Pre-season_Pre-season-cleaned.csv
├── scripts/
│   ├── clean_draft.py                     # Data cleaning script (multi-format)
│   ├── dashboard.py                       # Streamlit dashboard
│   └── MANIFEST.md                        # Script dependency table
├── tests/
│   ├── conftest.py                        # Shared pytest fixtures (2020, 2021, 2025)
│   ├── features/
│   │   ├── clean_draft.feature
│   │   ├── clean_draft_formats.feature    # Multi-format (2020, 2021) scenarios
│   │   └── dashboard.feature
│   └── step_defs/
│       ├── test_clean_draft.py
│       ├── test_clean_draft_formats.py
│       └── test_dashboard.py
└── .claude/
    └── skills/
        └── draft-visualization.md         # Project coding standards
```
