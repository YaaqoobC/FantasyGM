---
name: add-historic-features
description: Add or modify pregame historical player, team, or opponent features in FantasyGM, including leakage checks, validation, and CSV integration. Use for feature engineering rather than model training or data collection.
---

# Add historical features

Read the repository's `AGENTS.md` and `.agents/context/project.md` if they are not already in context. Inspect `src/features/build_features.py`, its tests, and the relevant collector columns before choosing an implementation.

## Define the feature

Explain its basketball meaning, source columns, aggregation unit (player-game or team-game), grouping keys, lookback window, season-boundary behavior, and when its value becomes available. Distinguish numerical inputs from categorical metadata and targets. Preserve existing seasonal resets and 10-game player warm-up unless the requested feature requires an explicitly explained change.

Use data already collected when it supports the feature. Do not invent unavailable advanced metrics such as pace or defensive rating from insufficient columns. Explain additional data needs when relevant.

## Construct pregame history

- Establish chronological ordering before historical operations. Date ties must not allow same-game or later information into a prediction.
- For player history, group by player and season and exclude the current game before rolling or expanding aggregation.
- For team/opponent features, first create one row per team-game from the full player logs, before filtering players by their individual history length. Do not treat individual player rows as separate team games.
- To derive points allowed, aggregate each team's scored points and match the opposing team in the same game. Check that game pairings and join keys are complete and unambiguous.
- Calculate historical opponent summaries from strictly earlier team games. Join the upcoming opponent's pregame summary to the player-game using game and opponent identity. Current-game totals may supply future targets but must not enter that game's features.
- Guard join cardinality: enrichment must preserve one row per `(player_id, game_id)` and must not silently multiply or drop examples.
- Define insufficient-history behavior for the new feature explicitly. Never fill early history using future games, full-season means, or backward filling.

## Integrate and verify

Keep the change modular. Update `validate_features()` and `save_features()` when introducing a model input; retain metadata separately. Align warm-up filtering, validation, and export if the new feature changes row eligibility.

Use small deterministic fixtures with hand-computable expected values. For changed history behavior, check relevant cases such as multiple players/teams, season boundaries, ordering, and incomplete history. Change a current or future game's result and verify that the new feature for that game and earlier games remains unchanged. Confirm earlier history can affect later predictions. For team joins, verify opponent identity and preserved row counts/keys.

Run the relevant feature tests using the command in `AGENTS.md`. If export behavior changes, check the saved columns and eligible rows using a temporary output location rather than overwriting the user's dataset during a unit test.

Update the feature inventory and milestone state in `.agents/context/project.md` and relevant README descriptions. Report the implemented behavior, leakage protections, test results, and any remaining data limitations. Do not mark a planned feature complete until it is implemented and verified.
