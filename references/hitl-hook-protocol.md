# Human checkpoint protocol

## Hook types and transitions

| Hook | Trigger | Resume condition |
| --- | --- | --- |
| PRE_CODE_SPEC_LOCK | Proposed requirements need explicit user confirmation | Confirm affected requirements, lock contract, validate successfully |
| ARCH_DECISION_HOOK | Material architecture alternatives or unapproved schema change | User selects a path; re-lock changed contract |
| HIGH_RISK_OP_HOOK | Unapproved existing-file deletion, production config change, external package installation, or migration | Explicit authorization for the concrete operation |
| TEST_TRIAGE_HOOK | Three consecutive failing attempts for one root cause, or an immediate spec contradiction | User selects a remediation; revise contract if needed |
| SCOPE_DRIFT_HOOK | Necessary behavior falls outside locked constraints/input | User accepts a contract revision or selects an in-scope alternative |
| FINAL_ACCEPTANCE_HOOK | Verification evidence is ready for review | User explicitly accepts or requests refinement |
| NEW_CHAT_REVIEW_HOOK | Independent fresh-chat review required | User manually opens review chat and returns its report; reconcile it before acceptance |
| CONTEXT_HANDOFF_HOOK | Fresh context required for continuation/research | User manually opens a chat with the handoff and authorizes continuation |

Preserve existing authorization; do not re-ask for the same approved action.
Approval applies only to the recorded scope. If circumstances or the contract
change materially, pause for a new decision. Never interpret tool success, a
timeout, a suggested default, or an agent-written resolution as user approval.

## Emit a checkpoint

Run from the target workspace, with an absolute script path if installed elsewhere:

```sh
python3 scripts/hitl_checkpoint.py --hook-type ARCH_DECISION_HOOK --summary "Storage must support concurrent writers" --options "SQLite,Existing service,Defer concurrency" --evidence "AC-3 requires concurrent writes; current storage is a JSON file" --recommendation "SQLite" --phase BUILD_AND_VERIFY
```

`--options` is a comma-separated list of two or three distinct nonempty choices;
do not include commas inside a choice. `--evidence`, `--recommendation`, and
`--phase` are optional CLI fields; the agent must provide decision-relevant
evidence in the emitted record or accompanying chat. Recommendation defaults
to the first option. The banner is a local output, not a message to the user:
repeat the card in chat and wait there.

The JSON file defaults to `.codex-spec-state.json` in the current directory.
Use `--state-file PATH` to isolate a different workspace or test run. Schema:

```json
{
  "schema_version": 1,
  "active_checkpoint_id": "generated UUID or null",
  "checkpoints": [
    {
      "id": "generated UUID",
      "hook_type": "ARCH_DECISION_HOOK",
      "summary": "Storage must support concurrent writers",
      "options": ["SQLite", "Existing service"],
      "evidence": "AC-3 requires concurrent writes",
      "recommendation": "SQLite",
      "phase": "BUILD_AND_VERIFY",
      "created_at": "UTC ISO-8601 timestamp",
      "status": "pending",
      "resolution": null
    }
  ]
}
```

Only one checkpoint may be pending per state file. A second emission fails
without overwriting it. History is retained. Existing malformed state is rejected,
not reset. Writes use atomic replacement and an exclusive lock file to reject
concurrent writers. If a process crashes leaving a `.lock` file, verify no writer
is running before manually removing that lock; never auto-delete a possibly live lock.

## Interrupt card

Show the checkpoint ID and hook type, followed by:

- Hook Trigger Reason: the specific blocked decision or operation.
- Current State & Evidence: phase, affected criteria, commands/errors or diff.
- Concrete Options: A/B/C choices, with meaningful consequences.
- Recommended Path: the preferred option and a short reason.

Do not continue dependent implementation or operations while pending. Read-only
investigation supporting the decision may continue within the existing scope.

## Resume payload

After an actual user response, record its substance:

```sh
python3 scripts/hitl_checkpoint.py --resolve CHECKPOINT_ID --decision "User selected SQLite and approved the contract revision"
```

Resolution changes status to `resolved`, adds a `resolution` object containing
`decision` and `resolved_at`, and clears `active_checkpoint_id`. Preserve the
original phase to determine where to resume. Resolution text may capture a
custom user choice; it need not equal an offered option. The utility cannot
authenticate who approved: the agent is responsible for recording real consent.
Resolve only the active ID. Duplicate or unknown resolution requests fail.

Both commands exit 0 on a successfully recorded event and 2 on invalid arguments,
state corruption, concurrent access, or filesystem errors. A successful emission
means **paused**, not permission granted. On a failed write, remain paused and
report the error. Logs can contain sensitive evidence; include only what the
decision needs and follow the project's existing handling rules.

## Manual new-chat hooks

Read [the handoff guide](manual-chat-handoff.md) and populate the handoff file before
emitting either new hook. They require `--handoff-file` pointing to a readable,
nonempty UTF-8 text file. The checkpoint stores `handoff: {path, sha256}` with an
absolute path and a SHA-256 hash of its bytes. Do not update a handed-off file
silently after recording its identity; make revisions explicit to the user.

```sh
python3 scripts/hitl_checkpoint.py --hook-type NEW_CHAT_REVIEW_HOOK --summary "Independent review is ready" --options "Open review chat,Discuss blockers first" --handoff-file .codex/handoff.md --phase WAIT_FOR_USER_NEW_CHAT
```

Present a kind reminder, required file paths, and the complete copyable prompt.
Pause task execution and let the user open a new chat. Never clear/reset the
current chat, open a chat automatically, or spawn a reviewer as a substitute.
CONTEXT_HANDOFF_HOOK uses the same arguments and can be resolved with the user's
continuation instruction. Independent review requires an actual report:

```sh
python3 scripts/hitl_checkpoint.py --resolve CHECKPOINT_ID --decision "User returned review; findings require repair" --review-report .codex/review-report.md
```

For NEW_CHAT_REVIEW_HOOK, missing, empty, unreadable, or invalid UTF-8 reports
block resolution and leave the state unchanged. Resolution records
`review_report: {path, sha256}` alongside decision and timestamp. It means review
evidence was received, not that review passed. A reviewer does not resolve the
author's checkpoint. The author reconciles the report on the user's return and
requests renewed review when material changes invalidate the reviewed snapshot.

The original six hook formats remain compatible with schema version 1. Historical
artifact records are validated structurally without requiring their files to still
exist. Hashes record identity, not authenticity. The utility cannot judge whether
a report is independent, complete, current, or favorable, and is not a Stop hook.
Never pass arbitrary text as a fabricated report to bypass the review requirement.
