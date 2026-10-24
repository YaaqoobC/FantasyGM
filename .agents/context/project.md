# Project context

## Purpose

FantasyGM predicts 11 next-game NBA statistics and uses league scoring to support roster recommendations. It is also a learning project: explain the reasoning behind important modeling and engineering decisions.

## Implemented

- `src/collectors/nba_collector.py`: regular-season NBA player logs, multi-season imports, retries, raw CSV output, SQLite storage.
- `data/nba.db`, table `player_game_stats`: one row per `(player_id, game_id)` primary key. Includes `team_id`, `season`, `game_date`, `matchup`, minutes, and target stats.
- `src/features/build_features.py`: 51 numerical inputs: 12 historical stats times three rolling windows (3/5/10), 12 season averages, `games_played`, `rest_days`, and `is_home`.
- `opponent` is categorical metadata extracted from matchup strings alongside `is_home`.
- Validation checks required inputs, valid matchup context, sufficient history, and nonmissing training-ready inputs/targets.
- `tests/test_features.py`: synthetic matchup, historical-average, leakage, and validation checks.

## Data contracts

- Targets: `pts, reb, ast, stl, blk, tov, fgm, fga, fg3m, ftm, fta`. `min` is historical input only.
- `load_game_data()` parses dates and sorts by player, season, date, and game ID. `build_features()` currently expects that chronological ordering.
- Player history groups by `(player_id, season)` and resets each season. Rolling and expanding averages shift by one game before aggregation.
- Rows require 10 previous player games for CSV export; warm-up missing historical values are intentional.
- `rest_days` is elapsed calendar days since the player's previous appearance minus one.
- Metadata exported: player ID/name, season, game ID/date, opponent. Output: `data/processed/player_game_features.csv`.

## Planned

Next feature milestone: opponent historical defense, starting with points allowed over the opponent's previous 10 team games. This is not implemented yet.

Then: chronological splits, league scoring, rolling-average baseline, XGBoost/MLP comparisons, GRU, and hybrid GRU + MLP. Compare on the same splits using per-stat MAE/RMSE and fantasy-point error. Yahoo integration and roster optimization follow; architecture complexity must earn its place through measured performance.

League scoring from the handoff: `2*fgm - fga + ftm - fta + fg3m + pts + reb + 2*ast + 4*stl + 4*blk - 2*tov`.

## Known verification limit

SQLite reads encountered a disk I/O error during initial inspection. The stored dataset has not been revalidated in this session; do not infer database integrity from passing synthetic tests.
