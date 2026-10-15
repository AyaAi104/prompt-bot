"""Validate a five-element Markdown contract using a strict flat YAML subset."""

import argparse
import json
import re
import sys
from pathlib import Path


ELEMENTS = {
    "Goal": "goal_status",
    "Constraints": "constraints_status",
    "Input": "input_status",
    "Output": "output_status",
    "Acceptance Criteria": "acceptance_criteria_status",
}
EXTENDED_SECTIONS = ("Scope", "Interfaces", "Verification")
PLACEHOLDER = re.compile(r"\b(?:TODO|TBD|FIXME)\b|\?\?\?|\{\{.*?\}\}|<insert\b", re.I)


def validate(text):
    """Return JSON-compatible diagnostics; never execute Markdown or YAML."""
    errors = []
    metadata = {}
    lines = text.lstrip("\ufeff").splitlines()
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:
            errors.append({"element": "metadata", "reason": "Unclosed frontmatter"})
            lines = []
        else:
            for line in lines[1:end]:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                match = re.fullmatch(r"([a-z_]+):\s*([A-Za-z0-9_-]+)\s*", line)
                if not match or match[1] in metadata:
                    errors.append({"element": "metadata", "reason": "Invalid or duplicate flat metadata field", "line": line})
                else:
                    metadata[match[1]] = match[2]
            lines = lines[end + 1:]
    else:
        errors.append({"element": "metadata", "reason": "Missing YAML frontmatter"})

    if metadata.get("locked") != "true":
        errors.append({"element": "metadata", "reason": "Contract must have locked: true"})
    if not re.fullmatch(r"[1-9][0-9]*", metadata.get("revision", "")):
        errors.append({"element": "metadata", "reason": "Revision must be a positive integer"})

    version = metadata.get("format_version", "1")
    if version not in ("1", "2"):
        errors.append({"element": "metadata", "reason": "Unsupported format_version; use 1 or 2"})
    required = list(ELEMENTS)
    if version == "2":
        required.extend(EXTENDED_SECTIONS)
        if metadata.get("size") not in ("S", "M", "L"):
            errors.append({"element": "metadata", "reason": "Version 2 requires size: S, M, or L"})

    sections = {}
    current = None
    fence = None
    in_comment = False
    for raw in lines:
        # Comments and fenced examples cannot introduce requirement headings.
        clean = ""
        rest = raw
        while rest:
            if in_comment:
                _, sep, rest = rest.partition("-->")
                if not sep:
                    break
                in_comment = False
            else:
                before, sep, rest = rest.partition("<!--")
                clean += before
                if not sep:
                    break
                in_comment = True
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", clean)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not clean[marker.end():].strip():
                fence = None
            elif current:
                sections[current].append(clean)
            continue
        if marker:
            fence = marker[1]
            continue
        heading = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", clean)
        if heading and len(heading[1]) <= 2:
            name = heading[2]
            current = name if len(heading[1]) == 2 and name in required else None
            if current:
                if current in sections:
                    errors.append({"element": current, "reason": "Duplicate section"})
                sections.setdefault(current, [])
        elif current:
            sections[current].append(clean)
    if fence or in_comment:
        errors.append({"element": "document", "reason": "Unclosed code fence or HTML comment"})

    statuses = {}
    for name in required:
        content = "\n".join(sections.get(name, [])).strip()
        if name in ELEMENTS:
            statuses[name] = metadata.get(ELEMENTS[name], "MISSING")
            if statuses[name] != "CLEAR":
                errors.append({"element": name, "reason": "Status must be CLEAR", "status": statuses[name]})
        if not re.search(r"\w", re.sub(r"(?m)^\s*#{1,6}.*$", "", content)):
            errors.append({"element": name, "reason": "Missing or empty section"})
        if PLACEHOLDER.search(content):
            errors.append({"element": name, "reason": "Unresolved placeholder"})
    criteria = "\n".join(sections.get("Acceptance Criteria", []))
    ids = re.findall(r"\bAC-([1-9][0-9]*)\b", criteria)
    if not ids:
        errors.append({"element": "Acceptance Criteria", "reason": "Include acceptance identifiers such as AC-1"})
    return {"ready": not errors, "elements": statuses, "diagnostics": errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec_file", type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate(args.spec_file.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError) as exc:
        result = {"ready": False, "elements": {}, "diagnostics": [{"element": "file", "reason": str(exc)}]}
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
