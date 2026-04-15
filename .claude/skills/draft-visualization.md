---
name: draft-visualization
description: Coding standards and workflow rules for the RB-draft-visualization project
triggers:
  - "when working on clean_draft.py"
  - "when working on dashboard.py"
  - "when adding a new script"
  - "when a defect is found"
---

# Draft Visualization — Project Coding Standards

## Virtual Environment

- **Always use the project venv.** Create it once with `bash setup_venv.sh`.
- **Always activate before running scripts or tests:**
  ```bash
  source venv/bin/activate
  ```
- Never install packages globally; always add them to `requirements.txt` first.

## Libraries

| Purpose | Library |
|---------|---------|
| Data manipulation | `pandas` |
| Dashboard / UI | `streamlit` |
| Charts | `altair` (bundled with Streamlit; import directly) |
| Testing | `pytest` + `pytest-bdd` |

## Script Standards

Every script in `scripts/` must follow these rules:

1. **`--help` / `-h` flag** via `argparse`.  
   The help text must document:
   - What the script does (one-line summary)
   - Every argument (name, type, default, purpose)
   - At least one usage example

2. **`MANIFEST.md` must be kept current.**  
   When you add, remove, or modify a script, update `scripts/MANIFEST.md`:
   - Script name
   - What it does
   - What it depends on (libraries + other scripts/files)
   - What depends on it

3. **Executable permissions.**  
   Every script in `scripts/` and `setup_venv.sh` must be executable:
   ```bash
   chmod +x scripts/<new_script>.py
   ```
   Commit the mode change so permissions are preserved in the repository.

4. **`README.md` must be kept current.**  
   When you add, remove, or materially change a script, update `README.md`:
   - Add or update the script's section (what it does, usage examples, arguments)
   - Update the project structure tree if files were added or removed

5. **Type hints** on all function signatures.

6. **Docstrings** on all public functions (one-line summary is enough for simple functions).

7. **No bare `except`** clauses — always catch a specific exception type.

8. **No global mutable state** — pass data through function arguments and return values.

## Testing Standards

- Tests live in `tests/` using **Gherkin (`.feature`) format** with `pytest-bdd`.
- Feature files: `tests/features/<script_name>.feature`
- Step definitions: `tests/step_defs/test_<script_name>.py`
- Run all tests: `pytest tests/`

### Defect Workflow

When a defect is found — by a developer, a user, or Claude:

1. **Add a new Gherkin `Scenario`** to the relevant `.feature` file that reproduces the bug.
2. **Verify the scenario fails** before fixing (`pytest tests/` should show a failure).
3. **Fix the code.**
4. **Verify the scenario passes** (`pytest tests/` green).
5. Commit with a message referencing the scenario title.

### Code Review Checklist

Before marking any implementation complete, verify:

- [ ] `--help` / `-h` is implemented and accurate
- [ ] `scripts/MANIFEST.md` is up to date
- [ ] `README.md` is up to date
- [ ] Script has executable permissions (`chmod +x`) and mode is committed
- [ ] All public functions have type hints and docstrings
- [ ] No bare `except` clauses
- [ ] `pytest tests/` passes with no warnings
- [ ] New scenarios were added for any bugs fixed during review
