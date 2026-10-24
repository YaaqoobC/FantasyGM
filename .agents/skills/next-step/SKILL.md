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

Invoking `next-step` requests assessment and a proposal; it does not itself approve implementation. End the proposal with a focused approval question and wait. Before asking, identify the exact approval requirement in this skill and link it so the user understands the pause.

Existing approval counts only when it clearly covers the specific proposal and scope being executed. Do not infer implementation approval from an earlier general "let's do this," approval to edit the workflow, or invocation of the skill. If approval clearly covers this proposal, continue without asking again; routine implementation details within that scope need no additional approval.

For unresolved decisions that materially change scope, priorities, architecture, data contracts, evaluation design, cost, or account access, explain the consequences and recommend an option. Get the user's decision before dependent work; continue useful independent work while waiting. Do not reopen settled decisions without new evidence.

## 5. Deliver the approved work

Use the applicable repository skill, such as `add-historic-features`, and complete the approved scope. Make focused, maintainable changes; preserve unrelated working behavior and user edits.

Add meaningful tests for the changed behavior and run the relevant checks. Resolve failures caused by the change. Update documentation and `.agents/context/project.md` when verified behavior, data contracts, milestones, or explicit decisions change. Keep planned and completed work separate.

If new evidence makes the approved approach unsuitable, explain the issue and propose a scoped adjustment. Seek a new decision only when it materially changes the agreement. Report external or environment blockers accurately; do not claim unrun checks passed.

## 6. Summarize the result

Lead with the outcome delivered. Explain what the system now does, how it works, and why it matters in plain language. Use a short concrete example when it helps the user understand a calculation or behavior. Name the important assumptions and design choices, especially what data is included or excluded and how leakage is prevented.

State how the change was verified, whether saved datasets were regenerated, and any remaining limitation or unfinished acceptance criterion. Test counts and feature counts support the explanation; they do not replace it. Keep the explanation concise but complete enough for this learning project. Do not claim completion while required work remains.
