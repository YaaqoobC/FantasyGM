---
name: next-step
description: Determine the next concrete task in FantasyGM by comparing project goals with repository implementation, tests, and outstanding decisions. Use when the user asks what to work on next, requests project prioritization, or invokes next-step.
---

# Determine the next project step

Recommend a small, verifiable task that advances FantasyGM's goals. Use current evidence rather than repeating the last documented milestone. Invoking this skill alone requests assessment and a recommendation; implement the recommendation when the user also authorizes that work.

## Establish the current state

Read `AGENTS.md`, `.agents/context/project.md`, and the relevant README sections. Incorporate the user's latest priorities and decisions; do not reopen settled decisions without new evidence.

Inspect the repository structure, working-tree changes, and source/tests relevant to the likely next milestone. Treat documentation as a guide and code as the source of implementation truth. Distinguish implemented behavior, tested behavior, planned work, and unknowns. Do not mistake uncommitted work for missing work or mark a component complete just because its file exists.

Run focused, inexpensive checks when they resolve an uncertainty that affects the recommendation. Do not launch data imports, overwrite processed datasets, train models, or connect accounts merely to assess status. Report unavailable checks and their practical impact. Reassess documented blockers when relevant rather than assuming an old environment failure still applies.

## Choose the next increment

Compare the current state with the end-to-end goal: reliable historical data, pregame features, reproducible prediction experiments, league scoring, current NBA/Yahoo context, and usable roster recommendations.

Use these decision criteria:

- Resolve correctness or data-leakage problems that invalidate the next milestone before adding dependent functionality.
- Check prerequisites and prefer tasks that unlock a meaningful result or measurable comparison.
- Favor a bounded change with clear acceptance criteria, suitable tests, and data already available.
- Balance the functional product and learning goals. Preserve the GRU + MLP experimentation goal while establishing chronological evaluation and a baseline before judging complex models.
- Avoid endless feature expansion, speculative infrastructure, or architecture complexity without a concrete need. A documented roadmap is a starting point, not a reason to ignore evidence or changed priorities.

Select one recommended task. Mention alternatives only when they represent a meaningful tradeoff. If a blocker matters, propose the smallest diagnostic or repair that makes progress; identify work that can proceed independently.

## Involve the user in consequential decisions

Ask for input when an unresolved choice materially changes product scope, milestone priorities, architecture, data contracts, evaluation design, paid services, or account access. Examples include prioritizing Yahoo integration over model evaluation, changing season-boundary history, or selecting a different prediction target.

First provide the evidence, your recommendation, and concrete options with their consequences. Ask one focused question, using the available user-input tool when appropriate. State what depends on the answer and continue useful independent assessment while waiting. Do not treat silence as a decision.

Routine implementation details, naming, and straightforward prerequisites do not require a new decision. Respect existing authorization; do not add an approval gate to work the user already requested. For a decision outside that authorization, wait for the answer before dependent implementation. Explain the actual tradeoff behind any question rather than requesting generic confirmation.

## Deliver a useful recommendation

Keep the result concise and grounded in inspected files:

- State the next task and why it matters now.
- Summarize the evidence for what is already done and any relevant verification limits.
- Define the bounded deliverable, key dependencies, and observable acceptance criteria, including appropriate tests.
- Surface a human decision only if one remains unresolved; otherwise give an actionable recommendation without a ceremonial approval question.

When implementation is also authorized, follow the applicable repository skill, such as `add-historic-features`, and complete the scoped work. Update `.agents/context/project.md` when verified implementation or an explicit user decision changes the project state. Do not record a recommendation as completed work or an unchosen option as an agreed plan.
