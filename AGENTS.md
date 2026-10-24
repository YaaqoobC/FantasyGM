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

## Coding practices

- Prefer simple, readable solutions, clear names, and small functions with a single purpose. Add abstractions or dependencies only when the task justifies them.
- Make code understandable through simple, descriptive names. Use consistent domain terms across functions, variables, tests, and documentation; avoid cryptic abbreviations and unnecessarily elaborate names.
- Keep comments consistent in style and terminology. Use concise sentence-style comments for intent, assumptions, constraints, and non-obvious decisions; avoid narrating obvious operations. Add short docstrings describing a function's purpose and important contracts where names alone are insufficient. Update comments and docstrings with the code so they remain accurate.
- Keep shared data contracts and feature definitions consistent; avoid duplicating business rules across build, validation, and export paths.
- Validate assumptions at data boundaries and raise actionable errors. Do not silently drop invalid data or hide exceptions.
- Test observable behavior and important failure cases with deterministic fixtures. Keep model experiments reproducible and evaluate chronologically.
- Keep changes scoped and review the diff before finishing. Preserve unrelated user edits; avoid opportunistic rewrites.

## Communication and context

- Be concise and direct. Use plain language, concrete claims, and a natural colleague-to-colleague tone. Avoid canned introductions, hype, filler, and repeated summaries.
- Lead proposals with the outcome and why it matters; describe the implementation approach separately and briefly.
- Explain consequential ML reasoning and tradeoffs when needed, without verbose tutorials or narration of routine edits.
- Treat explanations as part of delivery. Explain meaningful changes in enough depth to understand what was done, how it works, why it was chosen, and what results mean. Use concrete examples, distinguish fixed statistical rules from trained models, and state limitations. Keep the language concise; scale depth to the change rather than omitting necessary detail.
- Make prediction validation visual as well as numerical. Provide charts that support inspecting individual predictions, error distributions, and patterns over time, with clear units, sample sizes, and explanations. Keep validation and reserved test data separate in reports.
- Keep durable project state in `.agents/context/project.md`, working rules here, and reusable task workflows in skills. Link to the source rather than copying the same instructions between files.
- Record verified outcomes and explicit decisions, including relevant limitations. Do not record suggestions as approved plans or planned work as complete.
- Read relevant context before acting, reuse settled decisions, and update stale context when new evidence changes it. Load additional files only as needed for the current task.

## Repository skills

For a high-level review of roadmap progress, completed outcomes, and remaining milestones, read [.agents/skills/roadmap-status/SKILL.md](.agents/skills/roadmap-status/SKILL.md).

For project prioritization or requests to determine the next task, read [.agents/skills/next-step/SKILL.md](.agents/skills/next-step/SKILL.md).

For requests to add or modify historical player, team, or opponent features, read [.agents/skills/add-historic-features/SKILL.md](.agents/skills/add-historic-features/SKILL.md).

## Checks

Run `PYTHONDONTWRITEBYTECODE=1 fantasy_gm_env/bin/python tests/test_features.py` from the repository root. The tests use standard-library unittest and pandas; pytest is not required.

For prediction evaluation changes, also run `PYTHONDONTWRITEBYTECODE=1 fantasy_gm_env/bin/python tests/test_baseline.py`. The validation benchmark command is documented in [README.md](README.md#first-prediction-benchmark); it reads SQLite without overwriting datasets and reserves the test season.

The dependency file is currently named `requirments.txt`. Use the existing environment when available. The full feature command, `fantasy_gm_env/bin/python src/features/build_features.py`, reads SQLite and overwrites the processed CSV; use it when a dataset rebuild is part of the task.
