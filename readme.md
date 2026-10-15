# spec-driven-coder

[中文说明](readme_cn.md)

`prompt-bot` is a reusable Codex skill for specification-driven software development with human-in-the-loop (HITL) decisions. 
It guides a coding agent to clarify requirements before implementation, build against a confirmed specification, verify the results, 
and request human input when a material decision is needed. 
The rule is from runoob.

The package contains agent instructions, reference documents, a specification template, and two Python command-line utilities. The utilities validate contracts and record checkpoints; the agent carries out the coding workflow. They do not automatically intercept tool calls or enforce filesystem permissions.

## Requirements

- Python 3.10 or later.
- Only the Python standard library is needed; no `pip install` step is required.
- Commands below run from this project directory using `python`. Use `python3` instead if that is your Python 3 executable.

## Project files

```text
.
├── SKILL.md
├── readme.md
├── readme_cn.md
├── references/
│   ├── five-element-rubric.md
│   └── hitl-hook-protocol.md
├── assets/
│   └── spec-contract.template.md
├── scripts/
│   ├── validate_spec.py
│   └── hitl_checkpoint.py
└── tests/
    └── test_skill_scripts.py
```

| File | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Skill entry point: trigger description, five-phase state machine, clarification gate, implementation and testing loop, checkpoint rules, and acceptance hand-off. |
| [references/five-element-rubric.md](references/five-element-rubric.md) | Evaluation rules for the five requirement dimensions, examples of unclear requirements, suggested questions, and the supported contract format. |
| [references/hitl-hook-protocol.md](references/hitl-hook-protocol.md) | Hook triggers, interrupt cards, checkpoint JSON structure, pause/resume rules, and logging failure handling. |
| [assets/spec-contract.template.md](assets/spec-contract.template.md) | Starting template for a task's specification, including revision, lock state, requirement statuses, and section headings. It intentionally fails validation until completed. |
| [scripts/validate_spec.py](scripts/validate_spec.py) | Checks specification structure, required content, statuses, and unresolved placeholders; prints JSON diagnostics. |
| [scripts/hitl_checkpoint.py](scripts/hitl_checkpoint.py) | Emits human-intervention banners, saves checkpoint history, and records decisions that resolve active checkpoints. |
| [tests/test_skill_scripts.py](tests/test_skill_scripts.py) | Runs CLI tests in temporary directories, covering valid and invalid contracts, checkpoint lifecycles, corrupt state, and concurrent-access locks. |
| [readme.md](readme.md) / [readme_cn.md](readme_cn.md) | English and Chinese project documentation. |

The existing `main.py` and `.idea/` directory belong to the surrounding workspace and are not required by this skill package. Neither Python utility uses `main.py` as an entry point.

## Workflow

The specification has five mandatory dimensions:

| Dimension | What it defines |
| --- | --- |
| Goal | What to build, who it serves, and its primary behavior. |
| Constraints | Runtime, dependency rules, architecture, and relevant operational limits. |
| Input | Data shapes, arguments, events, preconditions, and invalid-input handling. |
| Output | Return values, generated artifacts, errors, and state changes. |
| Acceptance Criteria | Observable pass/fail conditions, identified as `AC-1`, `AC-2`, etc. |

The agent follows five phases:

1. **PARSE_SPEC:** Extract the five dimensions from the request and workspace evidence.
2. **CLARIFY_GATE:** Clarify unresolved requirements, write `.codex/active-spec.md`, and validate the locked contract. Group questions into one turn with at most five high-impact questions.
3. **BUILD_AND_VERIFY:** Implement atomic tasks and run tests mapped to acceptance criteria. Run the project's configured linter when available.
4. **HITL_INTERRUPT_HOOK:** Pause affected work when a material decision or failure requires human input. This phase occurs when triggered, rather than on every implementation step.
5. **ACCEPTANCE_SIGN_OFF:** Present criterion-by-criterion evidence and request final acceptance or refinements.

Only `CLEAR` requirement statuses pass the gate. `MISSING`, `AMBIGUOUS`, and `INFERRED_NEEDS_CONFIRMATION` block application implementation. Previously confirmed requirements and authorized actions do not require duplicate approval. Material contract changes require a new revision, clarification, and validation.

## Use the workflow

Ask your coding agent to read this project's `SKILL.md` and apply it to a concrete task. For example:

> Read SKILL.md in this project and use its prompt-bot workflow to build a Python CLI that converts CSV inventory records into JSON. Clarify missing requirements before implementing it.

Read-only investigation and specification drafting can happen before the gate passes. Production implementation begins after the requirements are confirmed, the contract is locked, and validation succeeds.

The commands below assume the skill scripts and target workspace are in the same directory. When using this skill for another project, run commands from that target workspace and use absolute paths to the bundled scripts. Runtime artifacts then belong to the target project.

## Validate a specification

Copy `assets/spec-contract.template.md` to `.codex/active-spec.md`, creating the `.codex` directory if needed. Fill all five sections with confirmed requirements. Keep the exact English level-two headings and metadata keys from the template; the prose may be written in Chinese or another language.

Before validation, set each status to `CLEAR`, set `locked: true`, and use a positive integer `revision`. Include acceptance identifiers such as `AC-1`.

```sh
python scripts/validate_spec.py .codex/active-spec.md
```

| Exit code | Meaning |
| --- | --- |
| `0` | The structural gate passed; JSON contains `"ready": true`. |
| `2` | Clarification or correction is required, or the input file could not be read. For file/content checks, JSON diagnostics identify the problem. Invalid CLI usage prints argparse usage instead. |

The validator rejects empty or duplicate required sections, non-`CLEAR` statuses, unlocked contracts, unresolved markers such as `TODO`, `TBD`, and `???`, and unclosed fences or HTML comments. Headings inside fenced examples or comments do not satisfy required sections.

Frontmatter supports a deliberately restricted YAML subset: unquoted scalar fields, blank lines, and full-line comments. Quoted values, inline comments, nested YAML, and block scalars are unsupported. A passing result establishes structural completeness; the agent must still check consistency, meaningful requirements, and test coverage.

## Human checkpoints

| Hook | When to use it |
| --- | --- |
| `PRE_CODE_SPEC_LOCK` | The proposed specification still needs human confirmation. |
| `ARCH_DECISION_HOOK` | A material architecture choice or unapproved schema change needs a decision. |
| `HIGH_RISK_OP_HOOK` | An operation needs authorization, such as deleting existing files, changing production configuration, installing an external package, or running a migration. |
| `TEST_TRIAGE_HOOK` | Verification fails three consecutive times for the same root cause, or a specification contradiction is discovered. |
| `SCOPE_DRIFT_HOOK` | Required behavior extends beyond the locked constraints or input contract. |
| `FINAL_ACCEPTANCE_HOOK` | Verification evidence is ready for the user's acceptance review. |

Emit a checkpoint:

```sh
python scripts/hitl_checkpoint.py --hook-type ARCH_DECISION_HOOK --summary "Choose persistent storage" --options "SQLite,JSON file" --evidence "Concurrent writes are required by AC-3" --recommendation "SQLite" --phase BUILD_AND_VERIFY
```

`--options` requires two or three distinct nonempty choices separated by commas; individual choices cannot contain commas. The recommendation defaults to the first choice. The command prints a checkpoint ID and a structured interrupt banner. The agent must present the decision in chat and wait for a real response.

After the user responds, replace `CHECKPOINT_ID` with the emitted ID and record their actual decision:

```sh
python scripts/hitl_checkpoint.py --resolve CHECKPOINT_ID --decision "User selected SQLite and approved the contract revision"
```

Checkpoint commands return `0` when the event is saved and `2` on invalid arguments, state errors, lock conflicts, or filesystem failures. Successfully emitting a checkpoint means work is paused; it does not mean approval was granted. Recording a resolution does not itself restart an agent or validate a revised specification.

## Runtime artifacts

| Path | Purpose |
| --- | --- |
| `.codex/active-spec.md` | Task-specific specification created by the agent from the template. |
| `.codex-spec-state.json` | Checkpoint history, active checkpoint ID, evidence, timestamps, and recorded decisions. |
| `.codex-spec-state.json.lock` | Temporary exclusive lock used while updating checkpoint state. |

These files are created during use, not shipped as a completed task state. Use `--state-file PATH` to change the checkpoint log location. Each state file permits only one pending checkpoint; resolve it before emitting another. Atomic replacement protects updates, and malformed state is rejected without resetting history. If a crash leaves a lock file, verify that no writer is running before manually removing it.

## Verification

Run the script test suite:

```sh
python -m unittest discover -s tests -v
```

The initial project verification passed all 17 tests. The tests use isolated temporary workspaces and exercise complete/incomplete contracts, placeholder detection, malformed metadata, Markdown parsing, missing or unreadable files, all six hooks, resolution history, invalid requests, corrupt state, lock conflicts, and custom state paths.

These tests verify the helper utilities. They do not prove that an agent will follow the instructions or that a future application's acceptance criteria have been met; each task needs its own implementation tests and acceptance evidence.
