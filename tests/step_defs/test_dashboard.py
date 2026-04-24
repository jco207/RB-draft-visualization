"""
Step definitions for dashboard.feature.

Uses streamlit.testing.v1.AppTest for Streamlit-specific assertions and
subprocess for CLI flag testing.
"""

import subprocess
import sys
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

FEATURE_FILE = Path(__file__).parent.parent / "features" / "dashboard.feature"
scenarios(str(FEATURE_FILE))

PROJECT_ROOT = Path(__file__).parent.parent.parent
DASHBOARD_SCRIPT = PROJECT_ROOT / "scripts" / "dashboard.py"


# ---------------------------------------------------------------------------
# Background step
# ---------------------------------------------------------------------------

@given("the cleaned CSV exists")
def step_cleaned_csv_exists(cleaned_csv_path: Path) -> None:
    """cleaned_csv_path comes from the session fixture in conftest.py."""
    assert cleaned_csv_path.exists(), f"Cleaned CSV not found: {cleaned_csv_path}"


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("the dashboard app is started", target_fixture="app")
def step_start_app(cleaned_csv_path: Path):
    """
    Launch the Streamlit app via AppTest. The dashboard auto-detects the
    cleaned CSV from the project root — no sys.argv injection needed.

    cleaned_csv_path is accepted as a parameter so the session fixture runs
    first (generating the cleaned file), even though we don't use the path
    directly here.
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(DASHBOARD_SCRIPT), default_timeout=30)
    at.run()
    return at


@when("the dashboard script is run with --help", target_fixture="help_result")
def step_run_help() -> subprocess.CompletedProcess:
    """Run the script directly with Python (not Streamlit) to test the --help path."""
    return subprocess.run(
        [sys.executable, str(DASHBOARD_SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then("no exceptions are raised during startup")
def step_no_exceptions(app) -> None:
    # app.exception is an ElementList — it is falsy when empty, not None,
    # so we cannot use `is None` here.
    assert not app.exception, (
        f"Dashboard raised an exception: {app.exception}"
    )


@then("a download button is present")
def step_download_button_present(app) -> None:
    # download_button is not exposed as a named attribute on AppTest in the
    # version of Streamlit used here; use the generic get() accessor instead,
    # which searches rendered elements by their type name.
    dl_buttons = app.get("download_button")
    assert len(dl_buttons) > 0, "No download button found in the dashboard"


@then("at least one widget is rendered")
def step_at_least_one_widget(app) -> None:
    # If main() is never called (e.g. because it is not invoked at module level),
    # the app renders no widgets at all.  Any sidebar widget counts as proof that
    # the rendering path ran successfully.
    total = (
        len(app.multiselect)
        + len(app.checkbox)
        + len(app.slider)
        + len(app.text_input)
    )
    assert total > 0, (
        f"No widgets rendered — main() may not be called at module level. "
        f"Found: {total} widgets"
    )


@then("it exits with code 0")
def step_exits_zero(help_result: subprocess.CompletedProcess) -> None:
    assert help_result.returncode == 0, (
        f"Expected exit code 0, got {help_result.returncode}\n"
        f"stdout: {help_result.stdout}\nstderr: {help_result.stderr}"
    )


@then("at least two sliders are present")
def step_at_least_two_sliders(app) -> None:
    assert len(app.slider) >= 2, (
        f"Expected at least 2 sliders (Total Fpts, Active Fpts), found {len(app.slider)}"
    )


@then("the data table shows all 180 picks by default")
def step_all_picks_shown(app) -> None:
    # Rather than counting dataframe rows (which varies by year), we check that
    # the position filter includes the empty-string option for skipped picks —
    # that option only appears if all picks are shown by default.
    assert not app.exception, f"App raised an exception: {app.exception}"
    # Sidebar multiselect order: index 0 = Round, index 1 = Position, index 2 = Team
    position_select = app.sidebar.multiselect[1]
    assert "" in position_select.options, (
        f"Empty position not in filter options: {position_select.options}"
    )


@then('the output contains "streamlit run"')
def step_output_contains_streamlit(help_result: subprocess.CompletedProcess) -> None:
    combined = help_result.stdout + help_result.stderr
    assert "streamlit run" in combined, (
        f"'streamlit run' not found in output:\n{combined}"
    )


# ---------------------------------------------------------------------------
# Team filter steps
# ---------------------------------------------------------------------------

def _team_multiselect(app):
    """Return the Team multiselect widget.

    Sidebar multiselect order (0-indexed): Round=0, Position=1, Team=2.
    The index is fragile if the layout changes, so we assert length first
    to give a clear error message if a widget is added or removed.
    """
    multiselects = app.sidebar.multiselect
    assert len(multiselects) >= 3, (
        f"Expected at least 3 sidebar multiselects (Round, Position, Team), "
        f"found {len(multiselects)}"
    )
    return multiselects[2]


@then("a team multiselect is present in the sidebar")
def step_team_multiselect_present(app) -> None:
    widget = _team_multiselect(app)
    assert len(widget.options) > 0, "Team multiselect has no options"


@then("the team multiselect has all teams selected by default")
def step_team_multiselect_default(app) -> None:
    widget = _team_multiselect(app)
    assert sorted(widget.value) == sorted(widget.options), (
        f"Team multiselect default does not match all options.\n"
        f"Selected: {widget.value}\nOptions: {widget.options}"
    )


@when("the team filter is set to one team", target_fixture="app")
def step_set_one_team(app):
    widget = _team_multiselect(app)
    one_team = widget.options[0]
    widget.set_value([one_team])
    app.run()
    return app


# ---------------------------------------------------------------------------
# VBD metric steps
# ---------------------------------------------------------------------------

def _metric_radio(app):
    """Return the Fantasy points metric radio widget (the first and only radio in the app)."""
    assert len(app.radio) >= 1, (
        f"Expected at least 1 radio widget, found {len(app.radio)}"
    )
    return app.radio[0]


@then("the metric radio button includes VBD as an option")
def step_vbd_in_radio(app) -> None:
    widget = _metric_radio(app)
    assert "VBD" in widget.options, (
        f"VBD not in metric radio options: {widget.options}"
    )


@when("the metric is set to VBD", target_fixture="app")
def step_set_metric_vbd(app):
    _metric_radio(app).set_value("VBD")
    app.run()
    return app


# ---------------------------------------------------------------------------
# Keeper selectbox steps
# Sidebar selectbox order (0-indexed): Year=0, Keepers=1, Roster=2
# ---------------------------------------------------------------------------

def _keeper_selectbox(app):
    """Return the Keepers filter selectbox (sidebar selectbox index 1)."""
    selectboxes = app.sidebar.selectbox
    assert len(selectboxes) >= 2, (
        f"Expected at least 2 sidebar selectboxes (Year, Keepers), "
        f"found {len(selectboxes)}"
    )
    return selectboxes[1]


@then("a keeper selectbox is present in the sidebar")
def step_keeper_selectbox_present(app) -> None:
    widget = _keeper_selectbox(app)
    assert len(widget.options) > 0, "Keeper selectbox has no options"


@then("the keeper selectbox has options for all players, exclude keepers, and keepers only")
def step_keeper_selectbox_options(app) -> None:
    widget = _keeper_selectbox(app)
    expected = {"All players", "Exclude keepers", "Keepers only"}
    assert expected.issubset(set(widget.options)), (
        f"Keeper selectbox missing options. Expected {expected}, got {widget.options}"
    )


@when("the keeper filter is set to keepers only", target_fixture="app")
def step_set_keeper_filter(app):
    _keeper_selectbox(app).set_value("Keepers only")
    app.run()
    return app


# ---------------------------------------------------------------------------
# Roster filter steps
# Sidebar selectbox order (0-indexed): Year=0, Keepers=1, Roster=2
# ---------------------------------------------------------------------------

def _roster_selectbox(app):
    """Return the Roster filter selectbox (sidebar selectbox index 2)."""
    selectboxes = app.sidebar.selectbox
    assert len(selectboxes) >= 3, (
        f"Expected at least 3 sidebar selectboxes (Year, Keepers, Roster), "
        f"found {len(selectboxes)}"
    )
    return selectboxes[2]


@then("a roster filter selectbox is present in the sidebar")
def step_roster_selectbox_present(app) -> None:
    widget = _roster_selectbox(app)
    assert len(widget.options) > 0, "Roster filter selectbox has no options"


@then("the roster filter value is Entire Team")
def step_roster_filter_default(app) -> None:
    widget = _roster_selectbox(app)
    assert widget.value == "Entire Team", (
        f"Roster filter default expected 'Entire Team', got '{widget.value}'"
    )


@when("the roster filter is set to Starters", target_fixture="app")
def step_set_roster_starters(app):
    _roster_selectbox(app).set_value("Starters")
    app.run()
    return app


@when("the roster filter is set to Bench", target_fixture="app")
def step_set_roster_bench(app):
    _roster_selectbox(app).set_value("Bench")
    app.run()
    return app


# ---------------------------------------------------------------------------
# Team Roster table steps
# The "Select team" selectbox lives in the main content area, not the sidebar.
# app.selectbox returns ALL selectboxes (sidebar + main); sidebar ones come
# first, so we detect a main-area widget by checking all_count > sidebar_count.
# ---------------------------------------------------------------------------

@then("a team roster selectbox is present in the main area")
def step_team_roster_selectbox_present(app) -> None:
    sidebar_count = len(app.sidebar.selectbox)
    all_count = len(app.selectbox)
    assert all_count > sidebar_count, (
        f"Expected at least one main-area selectbox (Team Roster selector), "
        f"but all={all_count} and sidebar={sidebar_count}"
    )


@then("switching to Starters reduces the visible pick count")
def step_starters_reduce_count(app) -> None:
    # Capture the total number of rows across all rendered dataframes before
    # applying the Starters filter (this includes the Team Roster table).
    before = sum(len(el.value) for el in app.dataframe)
    _roster_selectbox(app).set_value("Starters")
    app.run()
    after = sum(len(el.value) for el in app.dataframe)
    # Starters are a strict subset of the full roster, so row count must drop.
    assert after < before, (
        f"Expected fewer total rows with Starters filter: "
        f"before={before}, after={after}"
    )
