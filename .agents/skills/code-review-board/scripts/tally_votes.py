#!/usr/bin/env python3
"""Validate a frozen review ballot and emit majority-approved comments as JSON."""

import argparse
import json
import re
import sys
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, names, label):
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == set(names.split()), f"{label} fields must be: {names}")


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be a nonempty string")


def array(value, label):
    require(isinstance(value, list), f"{label} must be an array")


def unique_strings(values, label):
    array(values, label)
    for value in values:
        nonempty(value, label)
    require(len(values) == len(set(values)), f"{label} must not contain duplicates")


def relative_path(value):
    nonempty(value, "path")
    require(not value.startswith("/") and "\\" not in value
            and not re.match(r"^[A-Za-z]:", value)
            and all(part not in ("", ".", "..") for part in value.split("/")),
            f"invalid repository-relative path: {value!r}")


def tally(review):
    """Return a complete or incomplete report; reject malformed inputs explicitly."""
    fields(review, "schema_version review_id snapshot scope board candidates ballots", "review")
    require(type(review["schema_version"]) is int and review["schema_version"] == 1,
            "schema_version must be integer 1")
    nonempty(review["review_id"], "review_id")
    snapshot = review["snapshot"]
    fields(snapshot, "base_revision head_revision content_sha256 digest_method", "snapshot")
    for key, value in snapshot.items():
        nonempty(value, f"snapshot.{key}")
    require(re.fullmatch(r"[0-9a-f]{64}", snapshot["content_sha256"]) is not None,
            "snapshot.content_sha256 must be 64 lowercase hex characters")
    unique_strings(review["scope"], "scope")
    require(bool(review["scope"]), "scope must not be empty")
    for path in review["scope"]:
        relative_path(path)
    board = review["board"]
    unique_strings(board, "board")
    require(len(board) >= 3 and len(board) % 2 == 1, "board size must be odd and at least three")
    array(review["candidates"], "candidates")
    candidates = {}
    for candidate in review["candidates"]:
        fields(candidate, "id category priority title body location evidence suggested_fix verification", "candidate")
        for key, value in candidate.items():
            if key != "location":
                nonempty(value, f"candidate.{key}")
        identity = candidate["id"]
        require(identity not in candidates, f"duplicate candidate: {identity}")
        require(candidate["category"] in {"logic", "formatting", "documentation", "best-practices",
                                           "testing", "security", "performance"}, "unknown candidate category")
        require(candidate["priority"] in {"P0", "P1", "P2", "P3"}, "unknown candidate priority")
        location = candidate["location"]
        fields(location, "path side start_line end_line", "location")
        relative_path(location["path"])
        require(location["path"] in review["scope"], "candidate path is outside review scope")
        nonempty(location["side"], "location.side")
        require(location["side"] in {"base", "head"}, "location.side must be base or head")
        require(type(location["start_line"]) is int and type(location["end_line"]) is int
                and 1 <= location["start_line"] <= location["end_line"], "invalid source line range")
        candidates[identity] = candidate
    array(review["ballots"], "ballots")
    ballots = {}
    for ballot in review["ballots"]:
        fields(ballot, "reviewer_id votes", "ballot")
        reviewer = ballot["reviewer_id"]
        nonempty(reviewer, "reviewer_id")
        require(reviewer in board, f"unknown reviewer: {reviewer}")
        require(reviewer not in ballots, f"duplicate ballot for: {reviewer}")
        array(ballot["votes"], "votes")
        votes = {}
        for vote in ballot["votes"]:
            fields(vote, "candidate_id decision reason", "vote")
            for key, value in vote.items():
                nonempty(value, f"vote.{key}")
            identity = vote["candidate_id"]
            require(identity in candidates, f"unknown candidate: {identity}")
            require(identity not in votes, f"duplicate vote: {reviewer}/{identity}")
            require(vote["decision"] in {"agree", "disagree", "abstain"}, "invalid vote decision")
            votes[identity] = vote["decision"]
        ballots[reviewer] = votes

    missing = []
    for reviewer in board:
        if not candidates and reviewer not in ballots:
            missing.append({"reviewer_id": reviewer, "candidate_id": None})
        for identity in candidates:
            if identity not in ballots.get(reviewer, {}):
                missing.append({"reviewer_id": reviewer, "candidate_id": identity})
    complete = not missing
    threshold = len(board) // 2 + 1
    results = []
    comments = []
    for identity, candidate in candidates.items():
        counts = dict.fromkeys(("agree", "disagree", "abstain", "missing"), 0)
        for reviewer in board:
            counts[ballots.get(reviewer, {}).get(identity, "missing")] += 1
        accepted = complete and counts["agree"] >= threshold
        results.append({"candidate_id": identity, "votes": counts, "accepted": accepted})
        if accepted:
            comments.append({**candidate, "votes": counts})
    comments.sort(key=lambda item: (item["priority"], item["location"]["path"],
                                    item["location"]["start_line"], item["id"]))
    return {**review, "status": "complete" if complete else "incomplete",
            "majority_threshold": threshold, "missing_votes": missing,
            "candidate_results": results, "comments": comments}


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Frozen review input JSON")
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as source:
            review = json.load(source, object_pairs_hook=reject_duplicate_keys)
        report = tally(review)
    except (OSError, ValueError) as error:
        print(f"Invalid review input: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "complete" else 3


if __name__ == "__main__":
    sys.exit(main())
