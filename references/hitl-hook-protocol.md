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
