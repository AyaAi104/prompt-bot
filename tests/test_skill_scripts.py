"""Exercise the public CLIs in isolated temporary workspaces."""

import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("goal", "constraints", "input", "output", "acceptance_criteria")
SECTIONS = {
    "Goal": "Provide a deterministic greeting CLI.",
    "Constraints": "Use Python 3.10+ and only the standard library.",
    "Input": "Accept one nonempty UTF-8 name argument; reject empty names.",
    "Output": "Print a greeting to stdout; invalid input exits 2 without files.",
    "Acceptance Criteria": "AC-1: Ada yields Hello Ada and exit 0. AC-2: An empty name exits 2.",
}


def contract():
    metadata = "\n".join(field + "_status: CLEAR" for field in FIELDS)
    body = "\n\n".join("## " + key + "\n" + value for key, value in SECTIONS.items())
    return "---\nrevision: 1\nlocked: true\n" + metadata + "\n---\n\n" + body + "\n"


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def run_script(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                              cwd=self.work, capture_output=True, text=True, timeout=15)

    def validate(self, text):
        path = self.work / "spec.md"
        path.write_text(text, encoding="utf-8")
        result = self.run_script("validate_spec.py", path)
        return result.returncode, json.loads(result.stdout)

    def emit(self, hook="ARCH_DECISION_HOOK", *args):
        return self.run_script("hitl_checkpoint.py", "--hook-type", hook,
                               "--summary", "Choose storage", "--options", "SQLite,JSON", *args)

    def state(self):
        return json.loads((self.work / "docs/spec-state.json").read_text(encoding="utf-8"))

    def test_complete_contract(self):
        code, result = self.validate(contract())
        self.assertEqual(code, 0)
        self.assertTrue(result["ready"])
        self.assertEqual(result["diagnostics"], [])

    def test_missing_and_empty_dimensions(self):
        for name, body in SECTIONS.items():
            for replacement in ("", "## " + name + "\n"):
                with self.subTest(name=name, replacement=replacement):
                    code, result = self.validate(contract().replace("## " + name + "\n" + body, replacement))
                    self.assertEqual(code, 2)
                    self.assertTrue(any(d["element"] == name for d in result["diagnostics"]))

    def test_placeholders_in_all_dimensions(self):
        for name, body in SECTIONS.items():
            for marker in ("TODO", "tbd", "???", "FIXME", "{{value}}", "<insert value>"):
                with self.subTest(name=name, marker=marker):
                    self.assertEqual(self.validate(contract().replace(body, body + " " + marker))[0], 2)

    def test_status_and_lock_gate(self):
        for status in ("MISSING", "AMBIGUOUS", "INFERRED_NEEDS_CONFIRMATION", "UNKNOWN"):
            self.assertEqual(self.validate(contract().replace("goal_status: CLEAR", "goal_status: " + status))[0], 2)
        self.assertEqual(self.validate(contract().replace("locked: true", "locked: false"))[0], 2)

    def test_invalid_metadata(self):
        for text in (contract().replace("revision: 1", "revision: 0"),
                     contract().replace("revision: 1", "revision: 1\nrevision: 2"),
                     contract().replace("---\n\n", "", 1),
                     contract().split("---", 2)[2]):
            self.assertEqual(self.validate(text)[0], 2)

    def test_fenced_or_commented_headings_do_not_satisfy_sections(self):
        for wrapper in ("```md\n{}\n```", "<!--\n{}\n-->"):
            text = contract().replace("## Input\n" + SECTIONS["Input"], wrapper.format("## Input\n" + SECTIONS["Input"]))
            self.assertEqual(self.validate(text)[0], 2)

    def test_comments_and_subheadings_are_not_content(self):
        for body in ("<!-- provided later -->", "### Schema", "- [ ]", "---"):
            self.assertEqual(self.validate(contract().replace(SECTIONS["Input"], body))[0], 2)

    def test_duplicate_section_and_unclosed_fence(self):
        self.assertEqual(self.validate(contract() + "\n## Goal\nAnother goal")[0], 2)
        self.assertEqual(self.validate(contract() + "\n```python\nprint(1)")[0], 2)

    def test_bom_crlf_and_code_payload(self):
        text = contract().replace(SECTIONS["Input"], '```json\n{"name": "Ada"}\n```')
        self.assertEqual(self.validate("\ufeff" + text.replace("\n", "\r\n"))[0], 0)

    def test_missing_file_and_bad_encoding(self):
        result = self.run_script("validate_spec.py", "absent.md")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["ready"])
        (self.work / "bad.md").write_bytes(b"\xff")
        result = self.run_script("validate_spec.py", "bad.md")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["ready"])

    def test_template_blocks_implementation(self):
        result = self.run_script("validate_spec.py", ROOT / "assets" / "spec-contract.template.md")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(set(json.loads(result.stdout)["elements"].values()), {"MISSING"})

    def test_all_hooks_emit_and_resolve_preserving_history(self):
        hooks = ("PRE_CODE_SPEC_LOCK", "ARCH_DECISION_HOOK", "HIGH_RISK_OP_HOOK",
                 "TEST_TRIAGE_HOOK", "SCOPE_DRIFT_HOOK", "FINAL_ACCEPTANCE_HOOK")
        for index, hook in enumerate(hooks, 1):
            result = self.emit(hook, "--evidence", "AC-1", "--recommendation", "SQLite")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PAUSED", result.stdout)
            state = self.state()
            self.assertEqual(len(state["checkpoints"]), index)
            identity = state["active_checkpoint_id"]
            self.assertEqual(state["checkpoints"][-1]["status"], "pending")
            result = self.run_script("hitl_checkpoint.py", "--resolve", identity, "--decision", "User selected SQLite")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsNone(self.state()["active_checkpoint_id"])
            self.assertEqual(self.state()["checkpoints"][-1]["resolution"]["decision"], "User selected SQLite")

    def test_pending_and_unknown_resolution_preserve_state(self):
        self.assertEqual(self.emit().returncode, 0)
        before = self.state()
        self.assertEqual(self.emit().returncode, 2)
        result = self.run_script("hitl_checkpoint.py", "--resolve", "unknown", "--decision", "Accept")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.state(), before)

    def test_invalid_emission_creates_no_state(self):
        for args in (("--options", "A"), ("--options", "A,A"), ("--options", "A,,B"),
                     ("--options", "A,B,C,D"), ("--summary", " "), ("--decision", "Accept")):
            self.assertEqual(self.emit("ARCH_DECISION_HOOK", *args).returncode, 2)
        self.assertEqual(self.emit("UNKNOWN").returncode, 2)
        self.assertFalse((self.work / "docs/spec-state.json").exists())

    def test_corrupt_state_not_overwritten(self):
        path = self.work / "docs/spec-state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        for contents in ("{", "[]", '{"schema_version":1,"checkpoints":[{}]}',
                         '{"schema_version":1,"checkpoints":[],"active_checkpoint_id":"ghost"}'):
            path.write_text(contents, encoding="utf-8")
            self.assertEqual(self.emit().returncode, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), contents)

    def test_concurrent_lock_is_preserved(self):
        lock = self.work / "docs/spec-state.json.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("another writer", encoding="utf-8")
        self.assertEqual(self.emit().returncode, 2)
        self.assertEqual(lock.read_text(encoding="utf-8"), "another writer")
        self.assertFalse((self.work / "docs/spec-state.json").exists())

    def test_custom_state_path(self):
        path = self.work / "nested" / "state.json"
        self.assertEqual(self.emit("SCOPE_DRIFT_HOOK", "--state-file", path).returncode, 0)
        self.assertTrue(path.exists())
        self.assertFalse(path.with_name("state.json.lock").exists())

    def test_default_state_uses_docs_without_touching_legacy_directory(self):
        # A file at the legacy directory path makes attempts to use it fail.
        legacy = self.work / ("." + "codex")
        legacy.write_text("Do not modify", encoding="utf-8")
        result = self.emit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.work / "docs" / "spec-state.json").is_file())
        self.assertEqual(legacy.read_text(encoding="utf-8"), "Do not modify")

    def test_v2_contract_all_sizes(self):
        for size in ("S", "M", "L"):
            text = contract().replace("revision: 1", "format_version: 2\nsize: " + size + "\nrevision: 1")
            text += "\n## Scope\nGreeting only; no network.\n## Interfaces\ncli.py accepts one name.\n## Verification\nRun python -m unittest; expect exit 0.\n"
            self.assertEqual(self.validate(text)[0], 0)

    def test_v2_requires_extended_sections_and_size(self):
        text = contract().replace("revision: 1", "format_version: 2\nrevision: 1")
        code, result = self.validate(text)
        self.assertEqual(code, 2)
        self.assertTrue({"Scope", "Interfaces", "Verification", "metadata"}.issubset(
            {item["element"] for item in result["diagnostics"]}))
        self.assertEqual(self.validate(text.replace("revision: 1", "size: XL\nrevision: 1"))[0], 2)

    def test_v2_rejects_unresolved_extended_content(self):
        text = contract().replace("revision: 1", "format_version: 2\nsize: M\nrevision: 1")
        text += "\n## Scope\nNo networking.\n## Interfaces\ncli.py\n## Verification\nRun unittest.\n"
        for original in ("No networking.", "cli.py", "Run unittest."):
            for replacement in ("", "TBD", "<!-- explanation later -->"):
                self.assertEqual(self.validate(text.replace(original, replacement))[0], 2)

    def test_format_version_compatibility(self):
        self.assertEqual(self.validate(contract().replace("revision: 1", "format_version: 1\nrevision: 1"))[0], 0)
        self.assertEqual(self.validate(contract().replace("revision: 1", "format_version: 99\nrevision: 1"))[0], 2)

    def test_handoff_requires_real_artifact(self):
        for hook in ("NEW_CHAT_REVIEW_HOOK", "CONTEXT_HANDOFF_HOOK"):
            self.assertEqual(self.emit(hook).returncode, 2)
            self.assertEqual(self.emit(hook, "--handoff-file", "missing.md").returncode, 2)
            for contents in (b" \n", b"\xff"):
                (self.work / "handoff.md").write_bytes(contents)
                self.assertEqual(self.emit(hook, "--handoff-file", "handoff.md").returncode, 2)
        self.assertFalse((self.work / "docs/spec-state.json").exists())

    def test_manual_review_waits_for_report_and_preserves_history(self):
        handoff = self.work / "handoff.md"
        handoff.write_text("Read the contract and actual diff; report findings.", encoding="utf-8")
        result = self.emit("NEW_CHAT_REVIEW_HOOK", "--handoff-file", handoff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Please open a new chat yourself", result.stdout)
        state = self.state()
        identity = state["active_checkpoint_id"]
        record = state["checkpoints"][-1]
        self.assertEqual(record["handoff"]["path"], str(handoff.resolve()))
        self.assertEqual(record["handoff"]["sha256"], hashlib.sha256(handoff.read_bytes()).hexdigest())
        base_args = ("--resolve", identity, "--decision", "User returned review")
        self.assertEqual(self.run_script("hitl_checkpoint.py", *base_args).returncode, 2)
        report = self.work / "report.md"
        for contents in (None, b" \n", b"\xff"):
            if contents is not None:
                report.write_bytes(contents)
            self.assertEqual(self.run_script("hitl_checkpoint.py", *base_args, "--review-report", report).returncode, 2)
            self.assertEqual(self.state(), state)
        report.write_text("Changes requested: cover the missing error case.", encoding="utf-8")
        result = self.run_script("hitl_checkpoint.py", *base_args, "--review-report", report)
        self.assertEqual(result.returncode, 0, result.stderr)
        resolved = self.state()
        self.assertIsNone(resolved["active_checkpoint_id"])
        self.assertEqual(resolved["checkpoints"][-1]["resolution"]["review_report"]["sha256"],
                         hashlib.sha256(report.read_bytes()).hexdigest())
        # History must remain usable after the local evidence is archived/moved.
        report.unlink()
        handoff.unlink()
        self.assertEqual(self.emit().returncode, 0)
        self.assertEqual(len(self.state()["checkpoints"]), 2)

    def test_continuation_can_resume_without_review_report(self):
        handoff = self.work / "handoff.md"
        handoff.write_text("Continue task T-2 after reading progress.", encoding="utf-8")
        self.assertEqual(self.emit("CONTEXT_HANDOFF_HOOK", "--handoff-file", handoff).returncode, 0)
        identity = self.state()["active_checkpoint_id"]
        result = self.run_script("hitl_checkpoint.py", "--resolve", identity,
                                 "--decision", "User opened this chat and requested continuation")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(self.state()["active_checkpoint_id"])

    def test_artifact_flags_are_rejected_for_unrelated_hooks(self):
        self.assertEqual(self.emit("ARCH_DECISION_HOOK", "--handoff-file", "handoff.md").returncode, 2)
        self.assertEqual(self.emit("ARCH_DECISION_HOOK", "--review-report", "report.md").returncode, 2)
        self.assertEqual(self.emit().returncode, 0)
        state = self.state()
        result = self.run_script("hitl_checkpoint.py", "--resolve", state["active_checkpoint_id"],
                                 "--decision", "Accepted", "--review-report", "report.md")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.state(), state)

    def test_corrupt_handoff_evidence_is_rejected(self):
        handoff = self.work / "handoff.md"
        handoff.write_text("Review the implementation.", encoding="utf-8")
        self.assertEqual(self.emit("NEW_CHAT_REVIEW_HOOK", "--handoff-file", handoff).returncode, 0)
        state = self.state()
        state["checkpoints"][0]["handoff"]["sha256"] = "invalid"
        path = self.work / "docs/spec-state.json"
        path.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self.emit().returncode, 2)
        self.assertEqual(self.state(), state)


if __name__ == "__main__":
    unittest.main()
