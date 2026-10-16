"""Emit or resolve a human checkpoint with atomic, serialized state updates."""

import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid


HOOKS = (
    "PRE_CODE_SPEC_LOCK", "ARCH_DECISION_HOOK", "HIGH_RISK_OP_HOOK",
    "TEST_TRIAGE_HOOK", "SCOPE_DRIFT_HOOK", "FINAL_ACCEPTANCE_HOOK",
    "NEW_CHAT_REVIEW_HOOK", "CONTEXT_HANDOFF_HOOK",
)
HANDOFF_HOOKS = ("NEW_CHAT_REVIEW_HOOK", "CONTEXT_HANDOFF_HOOK")


def artifact(path):
    """Record a readable, nonempty UTF-8 artifact without executing its contents."""
    path = path.resolve()
    data = path.read_bytes()
    if not data.decode("utf-8-sig").strip():
        raise ValueError("Artifact must contain nonempty UTF-8 text: " + str(path))
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}


def valid_artifact(value):
    # Historical evidence may have moved; validate the record, not live contents.
    return (isinstance(value, dict) and isinstance(value.get("path"), str)
            and bool(value["path"].strip()) and isinstance(value.get("sha256"), str)
            and len(value["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in value["sha256"]))


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def load_state(path):
    if not path.exists():
        return {"schema_version": 1, "active_checkpoint_id": None, "checkpoints": []}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") != 1 or not isinstance(state.get("checkpoints"), list):
        raise ValueError("Unsupported or malformed checkpoint state")
    seen = set()
    pending = []
    for record in state["checkpoints"]:
        if not isinstance(record, dict):
            raise ValueError("Malformed checkpoint record")
        identity = record.get("id")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("Invalid or duplicate checkpoint ID")
        seen.add(identity)
        if record.get("hook_type") not in HOOKS or record.get("status") not in ("pending", "resolved"):
            raise ValueError("Invalid checkpoint type or status")
        if record["hook_type"] in HANDOFF_HOOKS and not valid_artifact(record.get("handoff")):
            raise ValueError("Handoff checkpoint requires an artifact path and SHA-256")
        for key in ("summary", "evidence", "recommendation", "phase", "created_at"):
            if not isinstance(record.get(key), str):
                raise ValueError("Invalid checkpoint field: " + key)
        options = record.get("options")
        if not isinstance(options, list) or not 2 <= len(options) <= 3 or any(not isinstance(x, str) or not x.strip() for x in options):
            raise ValueError("Invalid checkpoint options")
        if record["status"] == "pending":
            if record.get("resolution") is not None:
                raise ValueError("Pending checkpoint contains resolution")
            pending.append(identity)
        else:
            resolution = record.get("resolution")
            if not isinstance(resolution, dict) or any(not isinstance(resolution.get(k), str) or not resolution[k].strip() for k in ("decision", "resolved_at")):
                raise ValueError("Invalid checkpoint resolution")
            if record["hook_type"] == "NEW_CHAT_REVIEW_HOOK" and not valid_artifact(resolution.get("review_report")):
                raise ValueError("Resolved review checkpoint requires report evidence")
    active = state.get("active_checkpoint_id")
    if "active_checkpoint_id" not in state or (pending != [active] if active is not None else bool(pending)):
        raise ValueError("Active checkpoint does not match pending history")
    return state


def save_state(path, state):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(state, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--hook-type", choices=HOOKS)
    action.add_argument("--resolve", metavar="CHECKPOINT_ID")
    parser.add_argument("--summary")
    parser.add_argument("--options")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--recommendation")
    parser.add_argument("--phase", default="BUILD_AND_VERIFY")
    parser.add_argument("--decision")
    parser.add_argument("--handoff-file", type=Path, help="Required for manual new-chat hooks")
    parser.add_argument("--review-report", type=Path, help="Required when resolving a new-chat review")
    parser.add_argument("--state-file", type=Path, default=Path("docs/spec-state.json"))
    args = parser.parse_args(argv)
    if args.hook_type:
        options = [item.strip() for item in (args.options or "").split(",")]
        if not args.summary or not args.summary.strip() or not 2 <= len(options) <= 3 or not all(options) or len(set(options)) != len(options):
            parser.error("Emission requires a nonempty summary and 2–3 distinct comma-separated options")
        if args.decision is not None:
            parser.error("Use --decision only with --resolve")
        if args.recommendation is not None and not args.recommendation.strip():
            parser.error("Recommendation cannot be empty")
        if args.review_report is not None:
            parser.error("Use --review-report only with --resolve")
        if args.hook_type in HANDOFF_HOOKS and args.handoff_file is None:
            parser.error("Manual new-chat hooks require --handoff-file")
        if args.hook_type not in HANDOFF_HOOKS and args.handoff_file is not None:
            parser.error("Use --handoff-file only with a manual new-chat hook")
    elif not args.decision or not args.decision.strip():
        parser.error("Resolution requires a nonempty --decision from the user's response")
    elif args.summary is not None or args.options is not None or args.recommendation is not None or args.handoff_file is not None:
        parser.error("Emission fields cannot be used with --resolve")

    path = args.state_file.absolute()
    lock = path.with_name(path.name + ".lock")
    acquired = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("x", encoding="utf-8") as handle:
            acquired = True
            handle.write(str(os.getpid()))
        state = load_state(path)
        if args.hook_type:
            if state["active_checkpoint_id"] is not None:
                raise ValueError("Resolve the active checkpoint before emitting another")
            record = {
                "id": str(uuid.uuid4()), "hook_type": args.hook_type,
                "summary": args.summary.strip(), "options": options,
                "evidence": args.evidence, "recommendation": args.recommendation or options[0],
                "phase": args.phase, "created_at": timestamp(),
                "status": "pending", "resolution": None,
            }
            if args.hook_type in HANDOFF_HOOKS:
                record["handoff"] = artifact(args.handoff_file)
            state["checkpoints"].append(record)
            state["active_checkpoint_id"] = record["id"]
            banner = [f"HUMAN INTERVENTION REQUIRED [{record['hook_type']}]", f"Checkpoint: {record['id']}",
                      f"Hook Trigger Reason: {record['summary']}",
                      f"Current State & Evidence: {record['phase']} | {record['evidence'] or 'See accompanying chat evidence'}",
                      "Concrete Options:"]
            banner.extend(f"  {chr(65 + i)}. {option}" for i, option in enumerate(options))
            banner.extend([f"Recommended Path: {record['recommendation']}", "PAUSED: wait for the user's decision."])
            if args.hook_type in HANDOFF_HOOKS:
                banner.extend([f"Handoff file: {record['handoff']['path']}",
                               "Please open a new chat yourself and paste the prompt in the handoff file.",
                               "Keep this chat intact. No chat was opened or cleared by this utility."])
                if args.hook_type == "NEW_CHAT_REVIEW_HOOK":
                    banner.append("Independent review remains pending until its report is returned.")
        else:
            if state["active_checkpoint_id"] != args.resolve:
                raise ValueError("Resolution ID is not the active checkpoint")
            record = next(item for item in state["checkpoints"] if item["id"] == args.resolve)
            report = None
            if record["hook_type"] == "NEW_CHAT_REVIEW_HOOK":
                if args.review_report is None:
                    raise ValueError("Independent review requires --review-report before resolution")
                report = artifact(args.review_report)
            elif args.review_report is not None:
                raise ValueError("--review-report applies only to NEW_CHAT_REVIEW_HOOK")
            record["status"] = "resolved"
            record["resolution"] = {"decision": args.decision.strip(), "resolved_at": timestamp()}
            if report is not None:
                record["resolution"]["review_report"] = report
            state["active_checkpoint_id"] = None
            banner = [f"Recorded resolution for {args.resolve}", f"Decision: {args.decision.strip()}"]
        save_state(path, state)
        print("\n".join(banner))
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc), "paused": True}), file=sys.stderr)
        return 2
    finally:
        if acquired:
            try:
                lock.unlink()
            except OSError as exc:
                print(f"Warning: could not remove checkpoint lock: {exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
