# FantasyGM agent instructions

Read [.agents/context/project.md](.agents/context/project.md) for the project state and data contracts. Inspect the relevant source and tests before editing; code is the source of truth when documentation differs.

## Working rules

- Work incrementally and preserve working collector and feature behavior unless the task requires a change.
- Explain meaningful ML concepts, algorithms, and design decisions; skip basic Python syntax explanations.
- Use only information available before the predicted game. Fit encoders, scalers, and other learned preprocessing on training data only.
- Add focused tests for changed feature behavior, historical grouping, and leakage. Run the relevant checks and report actual outcomes and limitations.
- Keep numerical inputs, categorical metadata, and prediction targets distinct. Update feature validation, CSV export, and documentation together when adding inputs.
- Keep generated CSVs, raw downloads, databases, credentials, and local environments out of commits. Use synthetic fixtures for tests.
- Update the project context when a milestone or data contract changes. Label planned work separately from implemented behavior.

## Repository skills

For project prioritization or requests to determine the next task, read [.agents/skills/next-step/SKILL.md](.agents/skills/next-step/SKILL.md).

For requests to add or modify historical player, team, or opponent features, read [.agents/skills/add-historic-features/SKILL.md](.agents/skills/add-historic-features/SKILL.md).

## Checks

Run `PYTHONDONTWRITEBYTECODE=1 fantasy_gm_env/bin/python tests/test_features.py` from the repository root. The tests use standard-library unittest and pandas; pytest is not required.

The dependency file is currently named `requirments.txt`. Use the existing environment when available. The full feature command, `fantasy_gm_env/bin/python src/features/build_features.py`, reads SQLite and overwrites the processed CSV; use it when a dataset rebuild is part of the task.
