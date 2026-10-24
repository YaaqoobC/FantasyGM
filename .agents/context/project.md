# Project context

## Purpose

FantasyGM predicts 11 next-game NBA statistics and uses league scoring to support roster recommendations. It is also a learning project: explain the reasoning behind important modeling and engineering decisions.

## Implemented

- `src/collectors/nba_collector.py`: regular-season NBA player logs, multi-season imports, retries, raw CSV output, SQLite storage.
- `data/nba.db`, table `player_game_stats`: one row per `(player_id, game_id)` primary key. Includes `team_id`, `season`, `game_date`, `matchup`, minutes, and target stats.
- `src/features/build_features.py`: 52 numerical inputs: 12 historical stats times three rolling windows (3/5/10), 12 season averages, `games_played`, `rest_days`, `is_home`, and `opponent_pts_allowed_avg_10`.
- Opponent scoring defense is built from full player-log team totals, reciprocal game pairings, and the opponent's previous 10 games. Join checks preserve player-game rows and reject invalid pairings or ambiguous same-day team games.
- `opponent` is categorical metadata extracted from matchup strings alongside `is_home`.
- Validation checks required inputs, valid matchup context, sufficient history, and nonmissing training-ready inputs/targets.
- `tests/test_features.py`: 13 tests covering matchup, player/opponent averages, leakage, opponent identity, join cardinality, ordering, season resets, warm-up, invalid data, validation, and temporary CSV export.

## Data contracts

- Targets: `pts, reb, ast, stl, blk, tov, fgm, fga, fg3m, ftm, fta`. `min` is historical input only.
- `load_game_data()` and `build_features()` parse dates and sort by player, season, date, and game ID; direct feature builds also accept shuffled input.
- Player history groups by `(player_id, season)` and resets each season. Rolling and expanding averages shift by one game before aggregation.
- Rows require 10 previous player games and 10 previous opponent team games for CSV export. Internal `opponent_games_played` controls eligibility and is not exported. Warm-up missing historical values are intentional; no future imputation is used. Validation and export share `FEATURE_COLUMNS` and `training_ready_rows()`.
- `rest_days` is elapsed calendar days since the player's previous appearance minus one.
- Metadata exported: player ID/name, season, game ID/date, opponent. Output: `data/processed/player_game_features.csv`.

## Experimental feature: opponent points allowed

`opponent_pts_allowed_avg_10` is flagged as experimental, with unverified predictive value. The user questioned whether this signal is too vague. Treat it as coarse scoring-environment context, not a reliable defensive-strength measure or an established predictor of individual stats. Pace, opponent quality, overtime, and lineup changes can affect it; the 10-game window is an untested choice.

Before retaining it, compare the same model with and without the input using identical chronological splits, eligible player-game rows, preprocessing, and training settings. Compare per-statistic and league fantasy-point errors on validation data; reserve the test set for final evaluation. Identical rows matter because opponent warm-up currently excludes extra examples. Drop or revise the feature if it does not demonstrate useful validation gains. No such experiment has run yet. This is a quality flag; computation and inclusion remain unchanged.

## Planned

Opponent points allowed is implemented. Further defense metrics remain optional future work; prediction benefits have not yet been measured.

Following milestones: chronological splits, league scoring, rolling-average baseline, XGBoost/MLP comparisons, GRU, and hybrid GRU + MLP. Compare on the same splits using per-stat MAE/RMSE and fantasy-point error. Yahoo integration and roster optimization follow; architecture complexity must earn its place through measured performance.

League scoring from the handoff: `2*fgm - fga + ftm - fta + fg3m + pts + reb + 2*ast + 4*stl + 4*blk - 2*tov`.

## Verification and limitations

On 2026-10-23, all 13 synthetic tests passed. SQLite `quick_check` passed and a full in-memory feature build validated all 154,345 stored player-game records across six seasons. It preserved all rows; 122,141 were training-ready. Opponent warm-up excluded 427 additional rows beyond player warm-up. The earlier disk I/O error did not recur.

The existing processed CSV was not rebuilt and still contains the previous feature set. Run the documented feature command when the dataset is needed for the next experiment.

Points allowed per game is not adjusted for pace or opponent strength. Team totals assume complete player logs: pairing checks cannot detect an individually missing player record. No predictive improvement has been established yet.
