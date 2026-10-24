# FantasyGM
An NBA fantasy basketball recommendation engine that automatically retrieves NBA statistics, understands your Yahoo fantasy league, predicts player performances, and recommends the best roster moves.

## Agentic development

Exploring agentic software development is a central goal of this project. FantasyGM relies heavily on coding agents for implementation, testing, documentation, and investigation, with human direction, guidance, and management. The aim is to develop practical skill in defining outcomes, directing agents, reviewing their work, and evaluating the resulting system.

The workflow is maintained in [AGENTS.md](AGENTS.md), [project context](.agents/context/project.md), and [repository skills](.agents/skills). These capture coding standards, data contracts, roadmap reviews, and the proposal-to-delivery process. Reproducible experiments and chronological evaluation provide evidence for engineering and modeling decisions; agent-generated code is assessed through tests, review, and measured results.

<img width="979" height="921" alt="image" src="https://github.com/user-attachments/assets/b2d8fab9-cfa5-49e5-a81f-3a9e6e1d489b" />


## Data Pipeline:
- Historic data will be obtained from [nba_api](https://github.com/swar/nba_api)
- Current data will be obtained from [yahoo fantasy sports api](https://sports.yahoo.com/developer/)

#### Collecting Historic Season Data:
- Using `nba_collector.py` we can collect the data for every player in the league for a specified season over a specified amount of years. This data is then written to a csv file and the SQLITE DB.
- Using `validate.py` we can do an initial validation on the saved data. 

Running:
  1. Start a virtual environment
  2. Install dependencies in `requirements.txt`
  3. Run the script: `python src/collectors/nba_collector.py --start <start-year eg.2020> --end <end-year eg.2024>`
  4. Run the script: `python python src/database/validate.py`

#### Building the Features:
- Using build_features.py, historical game data is converted into features that can be used to train our ML models.
- For each player, we calculate rolling averages over their last 3, 5, and 10 games, season-to-date averages, games played, and rest days.
- Each row represents one player-game, with historical features as inputs and the actual game statistics as prediction targets.
- Players and their upcoming opponents must each have at least 10 previous games in the season to be included in the training dataset.
- The processed data is saved to data/processed/player_game_features.csv.

#### Current Features (52 Total)

- 12 historical statistics: MIN, PTS, REB, AST, STL, BLK, TOV, FGM, FGA, FG3M, FTM, FTA.
- Rolling averages (36): Last 3, 5, and 10 games for each statistic.
- Season averages (12): Season-to-date average for each statistic.
- Additional features (4):
  - `games_played`: Games completed in the current season.
  - `rest_days`: Days of rest before the game.
  - `is_home`: If it was a home game
  - `opponent_pts_allowed_avg_10` (**experimental; predictive value unverified**): Points allowed per game by the upcoming opponent over its previous 10 team games.

**Total:** (12 × 3) + 12 + 4 = **52 input features**.

Opponent defense is calculated from complete player logs: player points are summed into team-game totals, paired with the opposing team, and averaged over strictly earlier games. Team and player history reset each season. This measures scoring allowed per game; it is not adjusted for pace or opponent strength.

**Feature quality flag:** Treat this as a coarse scoring-environment signal, not a reliable measure of defense or a proven predictor of individual player stats. Pace, opponent quality, overtime, and lineup changes can affect it, and the 10-game window has not been tuned. Before retaining it, compare the same model with and without this input on identical chronological splits and eligible rows, using per-statistic and fantasy-point errors. Choose using validation results and reserve the test set for final evaluation. It remains included in the pipeline pending evaluation.

`opponent` remains categorical metadata. An internal `opponent_games_played` count controls the 10-game warm-up; it is not an exported model input. Rows without enough player or opponent history remain in memory but are excluded from the training CSV. Historical values are never filled using future games.

The pipeline rejects duplicate player-games, incomplete or inconsistent game pairings, and multiple games for one team on the same date. Each source game must contain the full player logs for both teams; pairing checks cannot detect individual missing player records.

Run the feature tests with `PYTHONDONTWRITEBYTECODE=1 fantasy_gm_env/bin/python tests/test_features.py`. They check historical averages, opponent identity, leakage, season resets, validation, and CSV export using synthetic games.

Data Leakage:
  - This is the issue where information that is not available during prediction is used to train the model.
  - When building training data we cannot use the actual points for the day we are predicting.

#### Objective Features Matrix: (AI guided)

| Category | Feature Name | Description |
| :--- | :--- | :--- |
| **Historic Data** | PTS, REB, AST, STL, BLK, TO | Historical values of each statistic |
| | FGM, FGA, FTM, FTA, 3PM | Shooting volume and efficiency |
| | Minutes played | Recent and seasonal minutes |
| | Last 3/5/10 averages | Short-term and medium-term performance |
| | Season averages | Longer-term baseline |
| | Standard deviation | Consistency or volatility |
| | Usage rate | Involvement in team possessions |
| | Games started | Starter versus bench role |
| | | |
| **Opponent & Matchup** | Opponent defensive rating | Defensive quality |
| | Opponent pace | Possessions per game |
| | Opponent rebounds allowed | Rebounding opportunities |
| | Opponent assists allowed | Playmaking environment |
| | Opponent turnovers forced | Turnover risk |
| | Opponent steals/blocks allowed | Defensive-stat opportunities |
| | Recent opponent defense | Current defensive performance |
| | Home/away | Venue advantage |
| | | |
| **Role & Opportunity** | Projected minutes | Expected court time |
| | Recent minutes trend | Growing or shrinking role |
| | Recent starts | Starting lineup changes |
| | Usage trend | Change in offensive involvement |
| | Available teammates | Which teammates are playing |
| | Missing teammate usage | Offensive opportunities potentially freed |
| | Missing teammate minutes | Court time potentially freed |
| | | |
| **Injuries & Availability**| Player injury status | Available, questionable, doubtful, out |
| | Recent missed games | Availability history |
| | Teammates ruled out | Changes to rotation |
| | Teammates questionable | Possible role changes |
| | Opposing starters unavailable | Changes in opponent strength |
| | Days since last appearance | Possible return or inactivity effects |
| | | |
| **Schedule & Fatigue** | Rest days | Days since previous game |
| | Back-to-back | Playing two consecutive days |
| | Games in last 7 days | Recent workload |
| | Home/away | Travel context |
| | Travel distance | Potential fatigue |
| | Days until next game | Rest and rotation context |
| | | |
| **Team Context** | Team pace | Number of possessions |
| | Team offensive rating | Offensive efficiency |
| | Expected lineup | Which teammates are expected to play |
| | Recent team performance | Team-level trends |
| | Rotation stability | How consistent player roles are |

## ML Points Prediction Model:
- The initial objective for the model it to predict the stats (points, rebounds, assists, steals, turnovers, etc.) for each players next game.
- Using the points breakdown of a specific fantasy league, the stats will be converted into _Fantasy Points_ using the corresponding weights.
- This process can be repeated and aggregated for the week.

### First prediction benchmark

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 fantasy_gm_env/bin/python -m src.evaluation.baseline
```

Direct execution is also supported: `python src/evaluation/baseline.py` with the project environment activated. Both commands produce the same report.

This predicts each of the 11 statistics using the player's previous 10 games in the same season. For example, if a player's last 10 games average 20 points, the next prediction is 20 points. No parameters are fitted and no scaling or encoding is needed.

The split is fixed: **2020-21 through 2023-24 for training**, **2024-25 for validation**, and **2025-26 reserved for final testing**. The baseline does not fit on the training partition; that partition is established for future model comparisons. Season dates must be ordered and cannot overlap, including on the same calendar day. Missing or unexpected seasons raise an error rather than silently changing the split.

The command opens SQLite read-only, checks season/date metadata, and loads only training and validation game results. It builds features in memory, prints a JSON report with source/eligible/excluded row counts, date ranges, and validation MAE/RMSE, and saves an interactive dashboard to `reports/baseline/index.html` with a companion `metrics.json`. It does not score the reserved test season or overwrite the existing processed CSV. Use `--db /path/to/nba.db` for another database following the same contract.

### Visual validation

Install dependencies in the project environment with `python -m pip install -r requirments.txt`, then run the benchmark and open `reports/baseline/index.html` in your browser. Plotly and the validation data are embedded in this file, so it works offline without a web server. Generated reports are ignored by Git. Re-running replaces the report at the same location; use `--report-dir reports/experiment-name` to keep separate runs, or `--no-report` for JSON-only output.

From WSL, run this from the repository root to open the report through Windows:

```bash
explorer.exe "$(wslpath -w "$PWD/reports/baseline/index.html")"
```

The benchmark also prints a copyable opening command for the report it generated, including custom report directories. Alternatively, double-click `index.html` in your file explorer.

Filter by statistic, player, and date range. For a player, type a name and choose the suggestion showing their ID; leave the field empty for all players. All charts and metric cards update to match the selection. Every eligible selected appearance is included, with no sampling. Hover for details, drag to zoom, and use the chart toolbar to save images.

| View | What to look for |
| --- | --- |
| Predicted versus actual | Points near the diagonal are better. Above the diagonal means overprediction; below it means underprediction. Hover identifies the player and game. |
| Error distribution | Errors close to zero are better. Wide tails reveal large misses; a shift away from zero suggests bias. |
| Performance over time | Compare actual and predicted values for one player. For all players, these are daily averages, which can hide individual misses. |
| Error over time | Daily MAE shows the size of misses, while mean signed error shows overprediction or underprediction. Hover shows the daily sample size. |

The cards show the selected appearance count, MAE, RMSE, and mean signed error. A signed average near zero can hide large errors in opposite directions; use MAE and RMSE to judge accuracy. Small filtered samples are noisy, and selecting a player or date range changes the population being evaluated. These are diagnostics on validation data, not a new model or a final test result.

**MAE** is the average absolute prediction error; **RMSE** gives more weight to large misses. Lower is better. Fantasy scoring is applied separately to predicted and actual stat lines, then their difference is measured. The documented league formula is `2*fgm - fga + ftm - fta + fg3m + pts + reb + 2*ast + 4*stl + 4*blk - 2*tov`.

Evaluation follows the season game by game: earlier completed validation games may inform later predictions, while the current game's results cannot inform its own prediction. History resets each season. Only recorded player appearances with at least 10 previous player games and 10 previous opponent games are evaluated, matching the existing feature pipeline's eligibility rules. Non-appearances, early-season games, and some low-history players are outside this benchmark.

The baseline uses only player stat averages. It does not use the experimental opponent signal, so these results cannot establish that signal's usefulness. Future models should use the same eligible examples and split; selecting features or models belongs on validation data, with the test set reserved for final evaluation.

Validation run on 2026-10-23: **20,868 eligible player-games** from 2024-25, with 5,438 excluded by history warm-up. The four training seasons contain 80,128 eligible examples, unused for fitting this baseline. Errors below are per player appearance and rounded to three decimals:

| Statistic | MAE | RMSE |
| --- | ---: | ---: |
| Points | 4.786 | 6.266 |
| Rebounds | 1.985 | 2.619 |
| Assists | 1.397 | 1.899 |
| Steals | 0.745 | 0.971 |
| Blocks | 0.525 | 0.760 |
| Turnovers | 0.922 | 1.221 |
| Field goals made | 1.834 | 2.394 |
| Field goals attempted | 2.891 | 3.789 |
| Three-pointers made | 0.928 | 1.306 |
| Free throws made | 1.332 | 1.880 |
| Free throws attempted | 1.614 | 2.230 |
| Fantasy points | 10.239 | 13.125 |

These establish a reference, not evidence that predictions are adequate for roster decisions. The test season has not been evaluated.

Run the focused benchmark tests with:

```bash
PYTHONDONTWRITEBYTECODE=1 fantasy_gm_env/bin/python tests/test_baseline.py
```

## Pick Optimizer:
- Given a large data set of different players and different predicted Fantasy Points, this layer must determine which player(s) are the best for the current situation.
- Some constraints we would factor, include (but not limited to):
  - Position eligibility (includes all position _UTIL_)
  - Players already on the roster
  - Players available through Yahoo
  - Starting lineups
  - \# of games during the week
