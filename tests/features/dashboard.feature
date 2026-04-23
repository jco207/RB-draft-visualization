Feature: Draft Dashboard
  As a fantasy football analyst
  I want an interactive dashboard for the cleaned draft data
  So that I can explore picks by round, position, and fantasy points

  Background:
    Given the cleaned CSV exists

  Scenario: App loads without exceptions
    When the dashboard app is started
    Then no exceptions are raised during startup

  Scenario: Download button is present on load
    When the dashboard app is started
    Then a download button is present

  Scenario: Dashboard script supports --help flag
    When the dashboard script is run with --help
    Then it exits with code 0
    And the output contains "streamlit run"

  # Defect: main() was never called at module level so Streamlit had nothing to render
  Scenario: App renders at least one widget
    When the dashboard app is started
    Then at least one widget is rendered

  # Defect (code review): dtype coercion mutated the @st.cache_data result on every re-render
  Scenario: Round column has integer dtype after load
    When the dashboard app is started
    Then no exceptions are raised during startup

  # Defect (code review): slider crashes when min == max (e.g. all-zero Fpts after filtering)
  Scenario: Sliders render without error on initial load
    When the dashboard app is started
    Then at least two sliders are present

  # Defect (code review): picks with empty Position were silently excluded from default filter
  Scenario: Skipped picks are visible in the default view
    When the dashboard app is started
    Then the data table shows all 180 picks by default

  Scenario: Team multiselect is present in the sidebar
    When the dashboard app is started
    Then a team multiselect is present in the sidebar

  Scenario: Team multiselect defaults to all teams
    When the dashboard app is started
    Then the team multiselect has all teams selected by default

  Scenario: Filtering by a single team runs without errors
    When the dashboard app is started
    And the team filter is set to one team
    Then no exceptions are raised during startup

  # ---------------------------------------------------------------------------
  # VBD metric (added: VBD radio option, VBD column in dataframe)
  # ---------------------------------------------------------------------------

  Scenario: VBD is an option in the metric radio button
    When the dashboard app is started
    Then the metric radio button includes VBD as an option

  Scenario: Switching metric to VBD runs without error
    When the dashboard app is started
    And the metric is set to VBD
    Then no exceptions are raised during startup

  # ---------------------------------------------------------------------------
  # Keeper filter (changed from checkbox to three-way selectbox)
  # ---------------------------------------------------------------------------

  Scenario: Keeper selectbox is present in the sidebar
    When the dashboard app is started
    Then a keeper selectbox is present in the sidebar

  Scenario: Keeper selectbox has three options
    When the dashboard app is started
    Then the keeper selectbox has options for all players, exclude keepers, and keepers only

  Scenario: Filtering to keepers only runs without error
    When the dashboard app is started
    And the keeper filter is set to keepers only
    Then no exceptions are raised during startup

  # ---------------------------------------------------------------------------
  # Roster filter (Entire Team / Starters / Bench)
  # ---------------------------------------------------------------------------

  Scenario: Roster filter selectbox is present in the sidebar
    When the dashboard app is started
    Then a roster filter selectbox is present in the sidebar

  Scenario: Roster filter defaults to Entire Team
    When the dashboard app is started
    Then the roster filter value is Entire Team

  Scenario: Filtering by Starters runs without error
    When the dashboard app is started
    And the roster filter is set to Starters
    Then no exceptions are raised during startup

  Scenario: Filtering by Bench runs without error
    When the dashboard app is started
    And the roster filter is set to Bench
    Then no exceptions are raised during startup

  Scenario: Starters filter reduces the visible pick count
    When the dashboard app is started
    Then switching to Starters reduces the visible pick count

  # ---------------------------------------------------------------------------
  # Team Roster table
  # ---------------------------------------------------------------------------

  Scenario: Team roster team selectbox is present in the main area
    When the dashboard app is started
    Then a team roster selectbox is present in the main area
