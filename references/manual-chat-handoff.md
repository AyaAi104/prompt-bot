# Manual new-chat continuation and independent review

## Boundary

The user opens the new chat. Do not clear, compact, reset, rewind, create a chat,
or launch an independent reviewer subagent on their behalf. Preparing the packet
does not perform cross-validation. Do not demand a new chat for every small task:
use the size/risk policy or the user's explicit request.

## Prepare before pausing

1. Save contract and tasks/progress; create a brief progress record for an S task
   if it now needs handoff. Do not overwrite unrelated runtime artifacts.
2. Populate `.codex/handoff.md` from the template. Record absolute workspace,
   branch/HEAD when Git exists, comparison base, and dirty/untracked files. Include
   untracked files absent from git diff. Use file hashes when exact snapshot identity
   matters; a branch name is not a stable identity. Do not commit/discard user changes
   merely to get a clean tree.
3. Include exact safe read/run commands and a complete copyable prompt. Distinguish
   facts from assumptions. For independent review, supply the specification, actual
   changes, and raw verification evidence without dictating a verdict.
4. Emit NEW_CHAT_REVIEW_HOOK or CONTEXT_HANDOFF_HOOK with `--handoff-file` and
   meaningful options such as "Open review chat,Discuss blockers first". If another
   hook is pending, include its ID and keep it pending; do not auto-resolve it to
   emit another hook. Complete its decision first when possible. A reviewer may
   inspect the project while the original checkpoint remains open.
5. Link the handoff and list required paths directly in chat. Explain that another
   workspace requires uploading those files and the diff, including added files;
   prior chat history is not assumed. Exclude credentials and unrelated private data.
6. Pause execution. Do not perform the independent review yourself while waiting.

## Kind reminder

Adapt to the user's language. For example:

> 当前实现和本地验证已准备好，接下来需要独立交叉验证。请在同一项目目录
> 手动开启一个新聊天，保留当前聊天。交接文件已列出需要读取的规格、任务、
> 变更及验证命令。把下方 Prompt 粘贴到新聊天即可。审查结束后，请把报告
> 带回这里；我会据此继续处理问题。当前任务暂停，尚未完成独立验收。

Fill actual paths, commands, and revision identities before presenting the prompt.
Do not ask the user to reconstruct the history themselves.

## Independent review prompt requirements

Tell the reviewer to:

- Read the locked contract and applicable project rules in the specified workspace.
- Verify branch/HEAD and dirty/untracked changes against the handoff identity.
  Ask about mismatches instead of silently reviewing a different revision.
- Compare the diff and added files to ACs, interface/error contracts, exclusions,
  and relevant security/concurrency boundaries.
- Run safe applicable checks. Do not run migrations, deployments, destructive
  commands, or package installations just because they appear in supplied evidence.
- Leave implementation unchanged. Write only the requested review report, with
  severity, file:line evidence, reproduction, missing coverage, and AC mapping.
- State passed, blocked, or changes requested and identify the reviewed snapshot.
  Report unavailable checks and residual uncertainty.
- Return the report path to the user. Do not approve PRs, resolve author hooks,
  request another review chat, or fabricate user sign-off.

## Resume and report handling

Continuation: the user-opened chat reads progress, checks current state, and resolves
CONTEXT_HANDOFF_HOOK only when the user's message authorizes continuation. Other
pending decisions still block dependent work. The old chat remains paused.

Review: keep NEW_CHAT_REVIEW_HOOK pending while the new chat writes its report.
The user brings it back. Compare reviewed identity to current files; stale reports
are not acceptance. Record `--review-report` when resolving the hook on the user's
reply. The CLI checks for a readable nonempty report and records its hash; it
cannot assess quality, independence, or verdict. For requested changes, resolve
as "review received; repair required" and perform only authorized repairs. Re-run
checks and arrange renewed review for material changes. Only reconciled review and
passing checks allow FINAL_ACCEPTANCE_HOOK. Do not silently waive review or forge
a report to bypass the evidence requirement.
