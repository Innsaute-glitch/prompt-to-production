"""Clause-preserving summarizer for the UC-0B HR leave policy.

The implementation is deliberately extractive: the source policy is the sole
authority, so it does not add interpretations or outside HR information.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


CLAUSE_RE = re.compile(r"^(\d+\.\d+)\s+(.*\S)\s*$")
SECTION_HEADING_RE = re.compile(r"^\d+\.\s+\S")
SEPARATOR_RE = re.compile(r"^[^\w]*$")


def retrieve_policy(path: str) -> List[Tuple[str, str]]:
    """Load a UTF-8 text policy and return its numbered clauses in order.

    Every non-empty policy line must either begin a numbered clause, continue
    the currently open clause with indentation, or be a section/decorative
    line. An unexpected unindented line is rejected rather than silently
    attaching it to a neighboring clause.
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
    seen_clause = False

    def finish_clause() -> None:
        nonlocal current_number, current_parts
        if current_number is not None:
            clause_text = " ".join(current_parts).strip()
            if not clause_text:
                raise ValueError(f"Clause {current_number} has no text")
            clauses.append((current_number, clause_text))
            current_number = None
            current_parts = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        match = CLAUSE_RE.match(raw_line)
        if match:
            finish_clause()
            current_number = match.group(1)
            current_parts = [match.group(2)]
            seen_clause = True
            continue

        if SEPARATOR_RE.fullmatch(stripped):
            continue
        if SECTION_HEADING_RE.match(stripped):
            # A numbered section heading closes the preceding clause.
            finish_clause()
            continue

        if current_number is None:
            if not seen_clause:
                # Document title, reference, version, and other preamble
                # metadata are outside the numbered clause inventory.
                continue
            raise ValueError(f"Unexpected policy text on line {line_number}: {stripped}")
        if not raw_line[:1].isspace():
            raise ValueError(
                f"Ambiguous unindented text on line {line_number}; review the policy input"
            )
        current_parts.append(stripped)

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
        # One source-derived entry per clause preserves conditions, thresholds,
        # approvers, deadlines, exceptions, and consequences.
        lines.append(f"Clause {number}: {text}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a clause-preserving summary of an HR leave policy."
    )
    parser.add_argument("--input", required=True, help="Path to the UTF-8 .txt policy")
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
