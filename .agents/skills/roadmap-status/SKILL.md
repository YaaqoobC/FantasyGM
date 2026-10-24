---
name: roadmap-status
description: Give a high-level FantasyGM roadmap review covering completed outcomes, the current stage, and remaining milestones. Use for project progress or status questions; use next-step for choosing and approving implementation work.
---

# Roadmap status

Explain where FantasyGM stands against its overall goal in plain language. Keep the review at the level of capabilities and outcomes, rather than functions, feature lists, or implementation tasks.

## Assess the evidence

Read `AGENTS.md`, `.agents/context/project.md`, and relevant roadmap sections of `README.md`. Check the working tree and inspect enough relevant source and tests to substantiate milestone status. Use existing verification records with their dates; distinguish them from checks run during this review.

Derive the milestones from the documented goals and explicit decisions rather than maintaining a second roadmap here. Treat feature wish lists and possible experiments as optional ideas unless they were agreed as required work. Include uncommitted implementations in the assessment.

Separate implemented capabilities from demonstrated results. Passing calculation tests does not establish prediction quality; an experimental feature is not a validated modeling improvement. Note material gaps such as saved data lagging behind the implemented pipeline. If evidence conflicts or is missing, state the uncertainty instead of marking the milestone complete.

## Give the overview

Start with one sentence describing the current stage and the main capability still needed to reach the project goal.

Use a compact table with these columns:

| Milestone / outcome | Status | What is done or still missing |
| --- | --- | --- |

Group work into a handful of meaningful stages, such as reliable historical data, pregame inputs, trustworthy prediction evaluation, model comparisons, league integration, and roster recommendations. Adapt these groups to the actual roadmap. Use clear statuses: complete, partial, planned, or unknown. Mark a stage complete only when its stated outcome is supported by evidence.

Close with the main remaining dependency or unresolved decision, if any. Keep limitations that affect readiness visible, but omit low-level details and long task lists. Link to a few supporting repository sources without turning the overview into a file inventory. Avoid completion percentages or delivery estimates without an agreed basis.

## Keep assessment separate from execution

A status request authorizes a review, not new feature work, training, dataset rebuilds, or a change of priorities. Do not turn the review into an implementation proposal unless asked. If the user also requests the next task, follow [next-step](../next-step/SKILL.md) for the proposal and approval workflow. Ask a focused question only when a material ambiguity in the goals prevents a useful assessment; otherwise report the uncertainty and complete the overview.
