# Manual Chat Handoff

Populate with actual values before use. Keep unanswered questions unresolved.
Do not present instructional template text as completed work or review evidence.

## Purpose and pause reason

State continuation, research, or independent review; explain why another chat is
needed and name the current phase and pending checkpoint, if one exists.

## Exact workspace and snapshot

Record absolute path, branch/HEAD and base revision if Git, contract revision,
modified/untracked paths, and hashes or other identity for relevant uncommitted
files. Separate the author's changes from pre-existing user changes.

## Files to read or attach

List absolute paths to project rules, active-spec.md, tasks.md, progress.md,
source/tests, diff/added files, and raw evidence. Include UI design screenshots
when relevant. Explain what to upload if no shared workspace exists.

## Verification commands

Provide exact working directories, safe commands, expected outcomes, and environment
limitations. Author test output does not substitute for independent verification.

## Ready-to-paste prompt

Write the complete prompt in the user's language. For review, ask the new chat to
inspect the contract and actual diff, verify snapshot identity, run safe checks,
and report drift, defects, and missing coverage with file:line evidence. Forbid
implementation edits and further review handoffs. Specify the absolute output
path for review-report.md and ask the reviewer to return it to the user. For
continuation, explicitly name the next task.

## Return and resume

Explain which report/result to bring back and how findings block acceptance. State
that this chat stays paused until the user returns; the handoff is not approval.
