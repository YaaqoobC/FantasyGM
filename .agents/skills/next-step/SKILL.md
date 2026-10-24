---
name: next-step
description: Assess FantasyGM, propose the next outcome and a concise approach, obtain approval, then implement, test, document, and summarize the approved work. Use when the user asks what to work on next, requests prioritization, or invokes next-step.
---

# Next step

Follow the project from assessment through delivery. Ground decisions in repository evidence and the user's priorities. Keep proposals and updates concise.

## 1. Determine what is needed

Read `AGENTS.md`, `.agents/context/project.md`, and relevant README sections. Inspect working-tree changes and the source/tests for the likely milestone. Distinguish implemented, verified, planned, and unknown behavior; do not mistake uncommitted work for missing work.

Compare the current state with the goals: reliable NBA data, pregame predictions, fair model comparisons, league scoring, and useful roster recommendations. Resolve correctness and leakage problems before dependent work. Prefer a bounded increment that unlocks a useful result or measurable comparison. Preserve the learning goal and GRU + MLP experiments while establishing chronological evaluation and baselines first.

Run focused, inexpensive checks when they affect the recommendation. Recheck relevant old blockers rather than assuming they persist. Assessment alone does not authorize imports, dataset overwrites, model training, or account connections.

## 2. Propose the outcome

State one recommended goal in terms of the capability or result it enables. Explain briefly why it matters now, citing the relevant implementation and verification evidence.

For example: "Give predictions pregame context about the opponent's recent scoring defense." A function name or a list of files to edit is an implementation detail, not the goal. Do not promise better prediction accuracy until evaluation demonstrates it.

Define observable acceptance criteria and a clear scope boundary. Mention alternatives only when they involve a meaningful tradeoff. Avoid speculative infrastructure or endless feature expansion.

## 3. Propose the approach

Explain how to achieve the outcome in a few bullets: the main change, dependencies or important assumptions, tests, and documentation updates. Include material tradeoffs without turning the proposal into an implementation walkthrough.

## 4. Obtain approval

Present a concrete, reviewable proposal before requesting approval to implement it. Ask one focused question about the proposed outcome and approach, then wait for the user's response before dependent implementation. Silence is not approval.

Approval already given in the conversation counts: when the user accepts a proposal or explicitly requests its implementation, continue without asking again. This skill does not add approval gates to routine details within the agreed scope.

For unresolved decisions that materially change scope, priorities, architecture, data contracts, evaluation design, cost, or account access, explain the consequences and recommend an option. Get the user's decision before dependent work; continue useful independent work while waiting. Do not reopen settled decisions without new evidence.

## 5. Deliver the approved work

Use the applicable repository skill, such as `add-historic-features`, and complete the approved scope. Make focused, maintainable changes; preserve unrelated working behavior and user edits.

Add meaningful tests for the changed behavior and run the relevant checks. Resolve failures caused by the change. Update documentation and `.agents/context/project.md` when verified behavior, data contracts, milestones, or explicit decisions change. Keep planned and completed work separate.

If new evidence makes the approved approach unsuitable, explain the issue and propose a scoped adjustment. Seek a new decision only when it materially changes the agreement. Report external or environment blockers accurately; do not claim unrun checks passed.

## 6. Summarize the result

Lead with the outcome delivered. Briefly state what changed, how it was verified, and any remaining limitation or unfinished acceptance criterion. Explain important ML reasoning when useful, without narrating every edit. Do not claim completion while required work remains.
