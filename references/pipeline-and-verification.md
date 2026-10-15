# Pipeline tailoring, context, and verification

## Initialize context

Read applicable project rules, configuration, and target modules. Start with scoped
file searches, then load relevant sections and canonical nearby examples. For M/L
existing-code tasks, map input through state changes to output, citing actual
file:line locations. List uncertainty instead of claiming unexplored dependencies
are understood. For greenfield work, state that explicitly.

If repeated project-specific mistakes warrant persistent rules, propose or update
the appropriate project rule file within authorized scope. Preserve existing rules;
do not create competing AGENTS.md/CLAUDE.md/.cursorrules files. Aim for a short
document (at most about 200 lines; no minimum-padding requirement), limited to
non-obvious commands, unusual conventions, and architectural boundaries. Apply
the deletion test: remove a rule if omitting it would not plausibly cause a mistake.
Avoid making transient task decisions permanent project-wide requirements.

Load references as needed. For long supplied logs/docs, extract relevant portions
or delimit documents above the task request in a prepared prompt. Separate evidence
from instructions. XML is an organizational aid, not a security boundary or a
promise of any measured accuracy improvement.

## Size and task decomposition

S: up to three files, reversible, no schema/auth/security boundary change. Keep
the five-element audit and a brief contract, but skip a separate interview when
the user already supplied all required information. Ask about genuine gaps.

M: multi-file features, endpoints, or data models. Use a locked contract,
tasks/progress artifacts, and independently testable vertical slices. Review in
a user-opened fresh chat when changing public interfaces, concurrency, or material
boundaries, or whenever the user requests it.

L: auth, payments, migrations, cross-service changes, or unfamiliar legacy systems.
Use all M artifacts and require independent fresh-chat review before acceptance.
Classify by consequence and reversibility, not file count alone.

Each slice should expose one complete observable behavior across relevant layers.
For a CLI: argument parsing -> transformation -> output; for a UI feature: storage
-> service -> API -> interaction. Do not invent layers the application does not
have. Record dependencies, touched paths, AC IDs, reference implementation,
completion evidence, and the next task.

## Verification selection

Read existing commands rather than guessing them. In the contract's Verification
section, list checks with working directory, command, expected signal, and evidence
location. Explicitly mark inapplicable checks with a reason.

| Change | Select relevant evidence |
| --- | --- |
| Business logic or CLI | Behavior tests, invalid-input tests, relevant regression suite |
| Public API, schema, state mutation | Contract/integration tests, compatibility and error cases |
| Typed or compiled project | Existing type checker and build command in addition to tests |
| Project with configured lint | Existing linter without gratuitous package installation |
| UI/layout | Live screenshot at relevant viewport sizes, comparison to target, discrepancy/fix list, interaction checks |
| Auth/payment/migration | Boundary/error tests and independent review of contract drift and security-sensitive changes |

If a design target or tool is missing, ask first; if the user does not know, follow
the research/reasoning guide. An unavailable visual check is not a pass. Record
commands and actual output, retaining relevant failures without dumping entire
logs. Do not fabricate build/type checks for projects that have none. The skill
supplies workflow gates, not host-level Stop hooks.

## Failure recovery and context hygiene

Track same-root-cause failures in progress. On the third consecutive failure,
pause with evidence and options; do not reset the counter by changing test commands.
Propose rollback only with a known safe revision/patch and preserve pre-existing
user changes. Obtain authorization for destructive recovery. Never use automatic
git reset, chat rewind, or history clearing.

Save progress after meaningful milestones: contract revision, decisions, changed
interfaces, tests, next action, and blockers. Do not treat a fixed 30%–40% context
threshold as a universal fact or invent utilization measurements. When available
context signals or loss of trackable state warrant a fresh chat, prepare a manual
handoff and pause. Large exploration may use a user-opened research chat with a
narrow prompt and concise findings; do not automatically create a chat or substitute
a reviewer subagent.
