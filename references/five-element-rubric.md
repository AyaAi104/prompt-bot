# Five-element evaluation rubric

## Status rules

Use CLEAR for explicit, consistent, actionable requirements supported by the
user's request or confirmed workspace context. Use MISSING when there is no
usable information. Use INFERRED_NEEDS_CONFIRMATION for an assumption or proposed
default. Use AMBIGUOUS for contradictions or multiple materially different
interpretations. Only CLEAR passes the gate. A statement such as "no additional
performance constraints" is valid if explicitly confirmed; an empty section is
not. Do not invent arbitrary security or performance requirements.

## Goal

Pass when the intended user, core behavior, and useful outcome are identifiable.
Fail when the request supplies only a technology or broad aspiration. "Build an
API" lacks behavior; "Expose inventory lookup by SKU to warehouse operators"
provides an actionable goal. Separate essential behavior from optional features.

Ask: "Should the first version support lookup only (recommended), or lookup and
editing?" Do not silently expand a lookup feature into an inventory platform.

## Constraints

Pass when the relevant runtime, architectural boundaries, dependency policy, and
applicable operational limits are known. Read existing project configuration for
evidence. Ask only about limits that affect the implementation. Record explicit
absence of additional constraints if the user confirms it.

Fail on mutually incompatible limits, such as offline execution and a required
remote-only API. "Fast" is not a measurable latency budget when latency matters.

Ask: "Use the existing Python standard-library stack (recommended), or may this
feature add an external package?" Surface trade-offs before adding dependencies.

## Input

Pass when entry points, data shape/types, required fields, preconditions, and
relevant invalid/empty inputs have defined handling. An interactive feature can
specify user events rather than a file schema. A no-input operation must explicitly
say so and describe any environmental prerequisites.

Fail when sample data leaves types or required fields unclear, or when a schema
conflicts with examples. Include encoding and size limits only when material.

Ask: "For invalid records, reject the whole file (recommended for atomic imports),
or skip invalid rows and report them?"

## Output

Pass when returned values, artifacts or paths, error behavior, and relevant state
mutations are specified. Distinguish stdout from stderr for CLI contracts and
explicitly settle overwrite behavior for generated files.

Fail when "save the result" leaves the destination or overwrite semantics open.
Avoid hidden mutations not mentioned in the user's request.

Ask: "Write a new JSON file beside the input (recommended), or print JSON to stdout?"

## Acceptance Criteria

Pass when each criterion has a stable AC-number and an observable pass/fail
condition. Include representative normal behavior and relevant failure cases.
Tie performance criteria to a workload and measurement method. Manual checks
are acceptable when automation cannot substantiate the required property;
identify them explicitly and do not fabricate passing evidence.

Fail on "works well", "production-ready", or tests that merely assert the chosen
implementation's internal structure. Prefer "an unknown SKU returns HTTP 404
without modifying storage" over "use a lookup helper".

Ask: "Is success defined by lookup, unknown-SKU errors, and unchanged storage
(recommended), or are throughput measurements also required?"

## Cross-element audit

Check that inputs can produce the promised outputs within constraints. Ensure
every core goal has an acceptance criterion, and each criterion has a feasible
verification method. Record material decisions and user confirmation in Contract
Notes. A syntactically complete document still fails the semantic gate if its
requirements contradict one another. Resolve contradictions in one grouped
clarification turn rather than choosing whichever statement is easier to implement.

## Machine-readable contract format

Use the bundled template's exact level-two headings and metadata keys. The
validator intentionally accepts a small YAML subset: one unquoted scalar per
line, blank lines, and full-line comments. It does not implement general YAML
(nested mappings, quoted values, inline comments, or block scalars). Keep prose
in the Markdown body. `revision` must be a positive integer, `locked` must be
`true`, and each of the five status fields must be `CLEAR` for a passing gate.

Empty sections, comment-only sections, duplicate required sections, unfinished
markers such as `TODO`, `TBD`, and `???`, and unclosed fences/comments fail the
gate. Acceptance Criteria must include at least one AC-number. Requirement
headings inside examples or HTML comments do not satisfy missing sections.
Literal marker strings in payload examples also trigger the conservative
placeholder check; describe those payloads in words in the contract instead.
The script does not prove that prose is meaningful, criteria cover every behavior,
or the lock represents genuine user confirmation. Perform the semantic audit too.
