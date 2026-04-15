Feature: Draft CSV Cleaning
  As a fantasy football analyst
  I want the raw draft CSV to be cleaned and normalised
  So that I can analyse draft data without manual preprocessing

  Background:
    Given the raw draft CSV exists
    And the cleaning script has been run

  Scenario: Cleaned CSV is created
    Then a cleaned CSV file exists beside the original

  Scenario: Pick-Num column is calculated correctly
    Then the cleaned CSV has a "Pick-Num" column
    And round 1 pick 1 has Pick-Num 1
    And round 1 pick 12 has Pick-Num 12
    And round 2 pick 1 has Pick-Num 13
    And round 15 pick 12 has Pick-Num 180

  Scenario: Round separator rows are removed
    Then no row in the cleaned CSV has "Round" as its Pick value

  Scenario: Repeated header rows are removed
    Then no row in the cleaned CSV has "Pick" as its Pick value

  Scenario: Keeper flag is extracted correctly
    Then players with "(Keeper)" in the raw name have Keeper equal to True
    And players without "(Keeper)" in the raw name have Keeper equal to False

  Scenario: Position is extracted from player string
    Then the Position column contains only recognised positions or is empty

  Scenario: Asterisks are stripped from player names
    Then no Player value in the cleaned CSV starts with an asterisk

  Scenario: Round column is present and valid
    Then the cleaned CSV has a "Round" column
    And all Round values are between 1 and 15

  Scenario: Cleaned CSV has expected column set
    Then the cleaned CSV contains the columns Round, Pick, Pick-Num, Team, Player, Position, Keeper, Starred, Elapsed Time, Rank, Total Fpts, Active Fpts

  # Defect: session-scoped conftest fixture could not depend on function-scoped step fixture
  Scenario: Test fixtures resolve without scope errors
    Then the cleaned CSV path is a valid file path

  # Defect (code review): PICKS_PER_ROUND constant was missing; formula used magic number 12
  Scenario: Pick-Num formula respects picks per round boundary
    Then round 3 pick 1 has Pick-Num 25
    And round 3 pick 12 has Pick-Num 36
