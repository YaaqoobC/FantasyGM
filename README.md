# FantasyGM
An NBA fantasy basketball recommendation engine that automatically retrieves NBA statistics, understands your Yahoo fantasy league, predicts player performances, and recommends the best roster moves.

<img width="979" height="921" alt="image" src="https://github.com/user-attachments/assets/b2d8fab9-cfa5-49e5-a81f-3a9e6e1d489b" />


## Data Pipeline:
- Historic data will be obtained from [nba_api](https://github.com/swar/nba_api)
- Current data will be obtained from [yahoo fantasy sports api](https://sports.yahoo.com/developer/)

#### Features Matrix: (AI guided)

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
  - Starting linups
  - \# of games durring the week
