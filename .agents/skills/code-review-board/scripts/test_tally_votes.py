"""Synthetic checks for the review gate; no repository or service access needed."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tally_votes import tally


def fixture(decisions=("agree", "agree", "disagree")):
    return {
        "schema_version": 1,
        "review_id": "synthetic-review",
        "snapshot": {"base_revision": "base", "head_revision": "head",
                     "content_sha256": "a" * 64, "digest_method": "Synthetic fixture"},
        "scope": ["src/example.py"],
        "board": [f"r{i}" for i in range(len(decisions))],
        "candidates": [{"id": "R001", "category": "logic", "priority": "P2",
                        "title": "Guard empty input", "body": "Empty rows cause IndexError.",
                        "location": {"path": "src/example.py", "side": "head", "start_line": 2, "end_line": 2},
                        "evidence": "rows[0] is accessed before checking for empty input.",
                        "suggested_fix": "Guard empty input before indexing.",
                        "verification": "Test empty input."}],
        "ballots": [{"reviewer_id": f"r{i}", "votes": [{"candidate_id": "R001",
                    "decision": decision, "reason": f"Synthetic {decision} evidence."}]}
                    for i, decision in enumerate(decisions)],
    }


class TallyTests(unittest.TestCase):
    def test_majority_and_minority(self):
        for decisions, accepted in [(("agree", "agree", "disagree"), True),
                                    (("agree", "disagree", "disagree"), False),
                                    (("agree", "abstain", "abstain"), False)]:
            with self.subTest(decisions=decisions):
                report = tally(fixture(decisions))
                self.assertEqual(report["status"], "complete")
                self.assertEqual(bool(report["comments"]), accepted)
                self.assertEqual(report["majority_threshold"], 2)

    def test_five_member_threshold(self):
        report = tally(fixture(("agree", "agree", "abstain", "disagree", "abstain")))
        self.assertEqual(report["majority_threshold"], 3)
        self.assertEqual(report["comments"], [])

    def test_missing_board_member_does_not_shrink_denominator(self):
        review = fixture()
        review["ballots"].pop()
        report = tally(review)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["candidate_results"][0]["votes"]["agree"], 2)
        self.assertEqual(report["comments"], [])
        self.assertEqual(report["missing_votes"], [{"reviewer_id": "r2", "candidate_id": "R001"}])

    def test_one_missing_decision_blocks_entire_fix_queue(self):
        review = fixture()
        other = copy.deepcopy(review["candidates"][0])
        other["id"] = "R002"
        review["candidates"].append(other)
        for ballot in review["ballots"][:2]:
            ballot["votes"].append({"candidate_id": "R002", "decision": "agree", "reason": "Verified."})
        report = tally(review)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["comments"], [])

    def test_empty_candidates_need_explicit_completion(self):
        review = fixture()
        review["candidates"] = []
        for ballot in review["ballots"]:
            ballot["votes"] = []
        self.assertEqual(tally(review)["status"], "complete")
        review["ballots"].pop()
        self.assertEqual(tally(review)["missing_votes"], [{"reviewer_id": "r2", "candidate_id": None}])

    def test_duplicate_and_unknown_identities_are_rejected(self):
        for mutation in ("board", "candidate", "ballot", "vote", "unknown-reviewer", "unknown-candidate"):
            with self.subTest(mutation=mutation):
                review = fixture()
                if mutation == "board":
                    review["board"][1] = review["board"][0]
                elif mutation == "candidate":
                    review["candidates"].append(copy.deepcopy(review["candidates"][0]))
                elif mutation == "ballot":
                    review["ballots"].append(copy.deepcopy(review["ballots"][0]))
                elif mutation == "vote":
                    review["ballots"][0]["votes"] *= 2
                elif mutation == "unknown-reviewer":
                    review["ballots"][0]["reviewer_id"] = "stranger"
                else:
                    review["ballots"][0]["votes"][0]["candidate_id"] = "R999"
                with self.assertRaises(ValueError):
                    tally(review)

    def test_invalid_boundaries_and_payloads_are_rejected(self):
        mutations = [lambda r: r.update(schema_version=True),
                     lambda r: r.update(board=["r0", "r1"]),
                     lambda r: r.update(unexpected="field"),
                     lambda r: r["snapshot"].update(content_sha256="bad"),
                     lambda r: r["candidates"][0]["location"].update(start_line=True),
                     lambda r: r["candidates"][0]["location"].update(end_line=1),
                     lambda r: r["candidates"][0]["location"].update(path="outside.py"),
                     lambda r: r["candidates"][0]["location"].update(side="working"),
                     lambda r: r["ballots"][0]["votes"][0].update(decision="yes"),
                     lambda r: r["ballots"][0]["votes"][0].update(reason=" "),
                     lambda r: r["ballots"][0]["votes"][0].update(candidate_id=[])]
        for mutation in mutations:
            review = fixture()
            mutation(review)
            with self.assertRaises(ValueError):
                tally(review)

        for path in ("/abs.py", "../escape.py", "src/../escape.py", "src//a.py", "C:/a.py", "src\\a.py"):
            review = fixture()
            review["scope"] = [path]
            with self.assertRaises(ValueError):
                tally(review)

    def test_deleted_code_uses_base_side_location(self):
        review = fixture()
        review["candidates"][0]["location"]["side"] = "base"
        self.assertEqual(tally(review)["comments"][0]["location"]["side"], "base")

    def test_comments_sort_by_priority_and_keep_audit_trail(self):
        review = fixture()
        for identity, priority in [("R002", "P1"), ("R003", "P3")]:
            candidate = copy.deepcopy(review["candidates"][0])
            candidate.update(id=identity, priority=priority)
            review["candidates"].append(candidate)
            for ballot in review["ballots"]:
                ballot["votes"].append({"candidate_id": identity, "decision": "agree", "reason": "Verified."})
        report = tally(review)
        self.assertEqual([c["id"] for c in report["comments"]], ["R002", "R001", "R003"])
        self.assertEqual(report["ballots"], review["ballots"])
        self.assertNotIn("votes", review["candidates"][0])

    def test_cli_exit_codes_and_json_output(self):
        script = Path(__file__).with_name("tally_votes.py")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            for mode, expected in [("complete", 0), ("incomplete", 3), ("invalid", 2), ("duplicate-json", 2)]:
                review = fixture()
                if mode == "incomplete":
                    review["ballots"].pop()
                elif mode == "invalid":
                    review["board"] = []
                source.write_text('{"schema_version":1,"schema_version":1}' if mode == "duplicate-json"
                                  else json.dumps(review), encoding="utf-8")
                result = subprocess.run([sys.executable, str(script), str(source)], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                if expected == 2:
                    self.assertEqual(result.stdout, "")
                    self.assertIn("Invalid review input", result.stderr)
                else:
                    self.assertEqual(json.loads(result.stdout)["status"], mode)
                    self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
