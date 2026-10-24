# Review artifact contract (version 1)

The coordinator writes UTF-8 JSON input for `scripts/tally_votes.py`. The helper performs validation and deterministic tallying; agents perform discovery, evidence checks, deduplication, and voting. The helper does not launch agents or verify source claims.

## Input

Required top-level fields (additional fields are rejected):

- `schema_version`: integer `1`.
- `review_id`: nonempty identifier for this review run.
- `snapshot`: object with nonempty `base_revision`, `head_revision`, `content_sha256` (64 lowercase hex characters), and `digest_method`. For a non-Git audit, use explicit identifiers such as `no-git` and document the content manifest.
- `scope`: nonempty list of repository-relative file paths actually reviewed. Paths use `/`, with no absolute paths, backslashes, `.` or `..` components. Do not include secrets or raw datasets as review artifacts.
- `board`: list of distinct reviewer IDs, odd length at least three. These identify independent agents, not repeated runs presented as independent agents.
- `candidates`: list of the objects below; IDs are unique within this review.
- `ballots`: list of objects with `reviewer_id` and `votes`. Each reviewer submits at most one ballot. Each vote contains exactly `candidate_id`, `decision` (`agree`, `disagree`, `abstain`), and a nonempty `reason`. Every candidate needs an explicit decision from every reviewer for a complete report. An empty candidate list still requires one empty ballot per reviewer to attest completion.

A candidate has exactly these fields:

```json
{
  "id": "R001",
  "category": "logic",
  "priority": "P1",
  "title": "Reject empty input before indexing the first row",
  "body": "An empty import reaches rows[0] and raises IndexError before the documented empty-input result can be returned.",
  "location": {"path": "src/importer.py", "side": "head", "start_line": 42, "end_line": 43},
  "evidence": "The CLI permits empty input; the changed function indexes rows before its existing guard.",
  "suggested_fix": "Move the empty-input guard before the first access.",
  "verification": "Add an empty-input fixture and assert the documented empty result."
}
```

Categories: `logic`, `formatting`, `documentation`, `best-practices`, `testing`, `security`, `performance`. Pick the primary category. Priorities: `P0` immediate blocker with demonstrated broad impact; `P1` high-impact failure; `P2` normal actionable issue; `P3` low-impact convention/readability issue. Do not inflate stylistic issues to behavioral failures.

`location.path` must be in `scope`; `side` is `head` for current code or `base` for removed code. Line numbers refer to that side, are positive integers, and end is at least start. Keep the range as short as needed. All prose/ID fields are nonempty strings. The coordinator verifies actual file existence and evidence at the indicated side of the snapshot; the helper only validates structure. The fixer must map base-side deletion comments to the current code rather than treating base lines as current edit offsets. Do not include discovery authors or current tallies in the material sent to voters.

Minimal complete input with no findings:

```json
{
  "schema_version": 1,
  "review_id": "review-001",
  "snapshot": {
    "base_revision": "BASE_COMMIT",
    "head_revision": "HEAD_COMMIT",
    "content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "digest_method": "SHA-256 of the saved length-prefixed diff and untracked source manifest; see manifest.json"
  },
  "scope": ["src/importer.py"],
  "board": ["reviewer-1", "reviewer-2", "reviewer-3"],
  "candidates": [],
  "ballots": [
    {"reviewer_id": "reviewer-1", "votes": []},
    {"reviewer_id": "reviewer-2", "votes": []},
    {"reviewer_id": "reviewer-3", "votes": []}
  ]
}
```

## Output and pipeline behavior

The output preserves the validated input and adds:

- `status`: `complete` or `incomplete`.
- `majority_threshold`: fixed from the full board size.
- `missing_votes`: objects containing `reviewer_id` and `candidate_id` (`null` represents a missing empty ballot).
- `candidate_results`: candidate ID, counts for `agree`, `disagree`, `abstain`, and `missing`, plus `accepted` (boolean). Acceptance requires complete board voting for the entire review.
- `comments`: accepted candidate objects, sorted by priority/path/line/ID and augmented with `votes` (the four counts).

Complete reviews may have zero comments because no candidates were found or none passed. Incomplete reviews always have zero comments, even if a partial ballot already reaches the threshold. Rejected/abstained candidates remain in the audit trail, not the fix queue. Malformed input produces no report, exits `2`, and explains the error on stderr; incomplete reviews produce JSON and exit `3`.

The pipeline must check process success, schema version, `status`, and snapshot identity before consuming comments. Do not interpret a missing/invalid report as success. Keep original reports immutable for audit; a fix or changed candidate list needs a new run. No automatic edit, GitHub comment, commit, or merge is implied by report generation.
