# Structured Coding Prompt

Replace the instructions below with task-specific facts when assembling a prompt.
Do not invent requirements. Put necessary long source documents before the task
and label them as evidence. Link specific files instead of pasting repositories.

```xml
<context>
Describe the confirmed goal, current behavior, contract revision, and relevant files.
</context>
<reference_pattern>
Identify an actual repository example and the conventions to reuse.
</reference_pattern>
<constraints>
List confirmed boundaries, exclusions, and engineering reasons.
</constraints>
<task>
Specify one end-to-end behavior, AC IDs, and verification commands.
Ask about missing required information before implementing. If I do not know,
research or analyze alternatives and recommend within my authorization.
If a new chat is required, prepare file paths and a copyable prompt, remind me
kindly to open it myself, and pause; do not clear or create chats automatically.
</task>
```
