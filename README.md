# FantasyGM
An NBA fantasy basketball recommendation engine that automatically retrieves NBA statistics, understands your Yahoo fantasy league, predicts player performances, and recommends the best roster moves.

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

## Pick Optimizer:
- Given a large data set of different players and different predicted Fantasy Points, this layer must determine which player(s) are the best for the current situation.
- Some constraints we would factor, include (but not limited to):
  - Position eligibility (includes all position _UTIL_)
  - Players already on the roster
  - Players available through Yahoo
  - Starting lineups
  - \# of games during the week
