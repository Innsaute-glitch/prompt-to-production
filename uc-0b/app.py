"""Clause-preserving summarizer for the UC-0B HR leave policy.

The implementation is deliberately extractive: the source policy is the sole
authority, so it does not add interpretations or outside HR information.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


CLAUSE_RE = re.compile(r"^\s*(\d+\.\d+)\s+(.*\S)\s*$")
SECTION_HEADING_RE = re.compile(r"^\d+\.\s+\S")


def retrieve_policy(path: str) -> List[Tuple[str, str]]:
    """Load a text policy and return its numbered clauses in source order.

    Wrapped source lines are joined into the clause they belong to. Section
    headings such as ``2. ANNUAL LEAVE`` are intentionally not treated as
    clauses because they do not have a second numeric component.
    """
    policy_path = Path(path)
    if not policy_path.is_file():
        raise ValueError(f"Input policy file does not exist: {path}")

    try:
        text = policy_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Could not read UTF-8 policy file: {path}") from exc

    if not text.strip():
        raise ValueError("The input policy is empty")

    clauses: List[Tuple[str, str]] = []
    current_number = None
    current_parts: List[str] = []

    def finish_clause() -> None:
        if current_number is not None:
            clause_text = " ".join(current_parts).strip()
            if clause_text:
                clauses.append((current_number, clause_text))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = CLAUSE_RE.match(line)
        if match:
            finish_clause()
            current_number = match.group(1)
            current_parts = [match.group(2)]
        elif current_number is not None and line:
            is_separator = not any(character.isalnum() for character in line)
            if is_separator:
                # Decorative separator lines are not policy content.
                continue
            if raw_line[:1].isspace():
                # Indented lines continue the current clause.
                current_parts.append(line)
            elif SECTION_HEADING_RE.match(line):
                # Section headings such as "2. ANNUAL LEAVE" are structure,
                # not clause content.
                continue
            else:
                # A non-indented, non-heading line inside a clause may be an
                # unindented continuation. Preserve it rather than dropping it.
                current_parts.append(line)

    finish_clause()

    if not clauses:
        raise ValueError("No numbered policy clauses were found in the input")

    numbers = [number for number, _ in clauses]
    duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicates:
        raise ValueError("Duplicate clause numbers found: " + ", ".join(duplicates))

    return clauses


def summarize_policy(clauses: List[Tuple[str, str]]) -> str:
    """Create a clause-referenced summary without changing source meaning."""
    if not clauses:
        raise ValueError("Cannot summarize an empty clause list")

    lines = [
        "HR EMPLOYEE LEAVE POLICY - CLAUSE-PRESERVING SUMMARY",
        "Source: supplied HR leave policy",
        "",
    ]
    for number, text in clauses:
        # Keeping each clause as one source-derived sentence avoids silently
        # losing conditions, thresholds, approvers, deadlines, or exceptions.
        lines.append(f"Clause {number}: {text}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a clause-preserving summary of an HR leave policy."
    )
    parser.add_argument("--input", required=True, help="Path to the .txt policy")
    parser.add_argument("--output", required=True, help="Path for the summary .txt file")
    args = parser.parse_args(argv)

    try:
        clauses = retrieve_policy(args.input)
        summary = summarize_policy(clauses)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(clauses)} clause summaries to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
