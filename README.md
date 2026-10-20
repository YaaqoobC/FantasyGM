# FantasyGM
An NBA fantasy basketball recommendation engine that automatically retrieves NBA statistics, understands your Yahoo fantasy league, predicts player performances, and recommends the best roster moves.

<img width="979" height="921" alt="image" src="https://github.com/user-attachments/assets/b2d8fab9-cfa5-49e5-a81f-3a9e6e1d489b" />


## Data Pipeline:
- Historic data will be obtained from [nba_api](https://github.com/swar/nba_api)
- Current data will be obtained from [yahoo fantasy sports api](https://sports.yahoo.com/developer/)

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
