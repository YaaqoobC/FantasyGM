---
name: code-review-board
description: Review code changes with independent agents, vote on each proposed issue, and return majority-approved comments plus a structured report for a downstream fixing pipeline. Use for board-based code review, consensus review, or multi-agent review requests.
---

# Code review board

Produce actionable review comments supported by a strict majority of independent reviewers. Review only; applying fixes, publishing comments, and merging changes are separate actions requiring their own authorization. Local review artifacts are part of this workflow.

## Establish the review

Read applicable repository instructions and inspect the requested changes, surrounding code, callers, and relevant tests. Respect the requested scope. For an unspecified local review, use staged and unstaged tracked changes plus relevant untracked source files; for a branch/PR review, use its merge-base diff. If no change exists, ask for a target rather than inventing one.

Record the scope, base/head revisions, and a SHA-256 digest of the exact reviewed diff and any included untracked file contents in a local manifest. Include file names and boundaries in the digest input. Record how the digest was computed so a fixing step can reproduce it. This identifies the working tree, which a commit hash alone cannot do. Capture the same snapshot for every reviewer and verify it again before finalizing. If it changes, restart the review against the new snapshot; do not reuse old ballots.

Read [references/report-contract.md](references/report-contract.md) before assembling artifacts. Store the manifest, raw reviewer outputs, canonical candidates, ballots, and final report in the caller's requested artifact location, or a temporary directory outside the reviewed tree. Do not add generated reports to commits by default.

## Convene independent reviewers

Use the available agent delegation tools to create a board of **three distinct reviewer agents** by default. The coordinating agent organizes findings and tallies votes; it has no vote. A caller may request a larger odd board (at least three). Every reviewer examines all review dimensions; these focus areas provide complementary emphasis:

- Reviewer 1: logic, edge cases, data contracts, errors, security, and domain correctness.
- Reviewer 2: formatting, naming, comments/docstrings, readability, and repository conventions.
- Reviewer 3: design, best practices, tests, performance, and maintainability.

Give each reviewer the same target/snapshot, repository instructions, and candidate/report contract, plus its emphasis. Start reviewers without inherited conversation history when supported; explicitly supply the required context so coordinator opinions and peer findings do not leak into their discovery. Ask each to inspect source and tests itself. Do not provide other reviewers' findings during discovery or disclose an expected conclusion. Do not create reviewers as aliases of the coordinator's own opinion. Do not let reviewers spawn additional reviewers. When slots are limited, run distinct agents in batches and retain their outputs, then resume each for voting. If independent delegation is unavailable, report the review as blocked/incomplete; do not simulate a board or call a single review a majority result.

Reviewers must look for logic, formatting, commenting/documentation, best-practice, testing, security, and performance issues. Require evidence: a concrete trigger and consequence for behavioral issues, or an applicable repository convention and precise violation for style issues. Flag misleading comments and unnecessary complexity when the effect and improvement are concrete. Personal formatting preferences are not findings without an established convention or clear readability impact. Distinguish optional suggestions from actionable issues; suggestions do not enter voting. Inspect pre-existing code for context but report issues introduced or materially worsened by the change, unless a broader audit was requested. Use repository-specific domain checks where relevant (for example, temporal leakage in ML code).

## Build the ballot

Collect independent discoveries before sharing any candidates. Merge only findings with the same root cause, affected behavior, and fix; retain distinct failures at the same line. Normalize wording without strengthening a claim. Assign stable IDs within this review (for example, `R001`), category, priority, minimal source location, evidence, suggested fix, and verification. Use changed lines for inline comments when possible; explain a necessary location outside the diff. Set location `side` to `head` for current code or `base` for removed code. Check that paths and line ranges exist on that side of the reviewed snapshot. A deletion comment tells a fixer what must be restored or replaced; its base line number is not a current edit offset.

Provide every reviewer the **same frozen candidate list**, with author identities and discovery counts removed. Each independently inspects every candidate against the code and returns `agree`, `disagree`, or `abstain` with a reason. Agreement endorses the stated claim, priority, and suggested fix. A reviewer may agree with its own discovery only after this verification; proposing a finding is not a vote. Abstain when evidence is unavailable. Votes must not be influenced by others' ballots; collect all ballots before revealing totals. One vote per reviewer per candidate.

Allow one correction round for concrete factual errors or genuinely new findings discovered during voting: freeze a revised list and collect fresh ballots from the entire board. Never carry votes across changed claims. Finish voting on that revised list, using disagreement or abstention for unresolved evidence; missing ballots mean incomplete. Disclose any subsequent new issues separately as unreviewed, without presenting them as accepted comments. Do not keep polling until a desired verdict appears.

## Tally and deliver

Use the deterministic helper rather than estimating consensus:

```bash
python3 <skill-directory>/scripts/tally_votes.py <review-input.json> > <report.json>
```

An issue passes only with `floor(board_size / 2) + 1` explicit agreements from the configured board. Disagreement, abstention, failures, and missing votes never reduce this denominator. A complete review requires every reviewer to submit a decision for every candidate, or an explicit empty ballot when there are no candidates. Retry a missing/malformed ballot once with the same frozen list. If still missing, produce an incomplete report; it contains no actionable comments. Do not substitute a new reviewer while retaining ballots from a different board.

The helper validates identities and payloads, rejects duplicate/unknown votes, and produces comments only for approved candidates after complete voting. Inspect its exit status: `0` complete, `2` invalid input, `3` incomplete. Keep stdout as JSON and diagnostics on stderr. Invalid input is a failed review, never a clean result.

Return only majority-approved findings as review comments, ordered by priority and location. Each comment states the problem, trigger/consequence or violated convention, and a focused correction; include the tally, source link/range, and verification. Link the JSON report and disclose the reviewed snapshot, scope, actual checks, and any unavailable evidence. Distinguish complete-with-no-findings from incomplete/blocked. Majority agreement is a filter, not proof that code is correct or that reviewers' errors are independent.

The downstream fixer consumes `comments` only when `status == "complete"` and the snapshot still matches. It should implement each approved issue with focused verification, then request a fresh review of the new snapshot. Finding IDs are local to one review and do not authorize edits outside its scope. This skill neither runs that fixing loop nor posts external comments unless separately requested.
