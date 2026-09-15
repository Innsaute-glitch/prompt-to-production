"""UC-0A municipal complaint classifier.

The rules deliberately use only the complaint row and always emit values from
the fixed assignment taxonomy.
"""

import argparse
import csv
import re
from pathlib import Path


CATEGORIES = {
    "Pothole",
    "Flooding",
    "Streetlight",
    "Waste",
    "Noise",
    "Road Damage",
    "Heritage Damage",
    "Heat Hazard",
    "Drain Blockage",
    "Other",
}
PRIORITIES = {"Urgent", "Standard", "Low"}
SEVERITY_KEYWORDS = (
    "injury", "child", "school", "hospital", "ambulance", "fire",
    "hazard", "fell", "collapse",
)
REQUIRED_INPUT_FIELDS = {"complaint_id", "description"}


def _find_term(text: str, terms):
    """Return the exact source span matching a term, or None.

    A word boundary at the beginning avoids matching unrelated words, while
    the trailing word characters allow the assignment keyword ``child`` to
    match the source word ``children`` and ``injury`` to match ``injuries``.
    """
    for term in terms:
        pattern = r"(?<!\w)" + re.escape(term).replace(r"\ ", r"\s+") + r"\w*"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _evidence(description: str, terms) -> str:
    """Return exact words from the description for the reason field."""
    match = _find_term(description, terms)
    if match:
        return match
    return description.strip()


def _review_result(complaint_id: str, description: str, reason_prefix: str) -> dict:
    """Return a safe review result while still applying mandatory urgency."""
    matched_severity = _find_term(description, SEVERITY_KEYWORDS)
    priority = "Urgent" if matched_severity else "Standard"
    if description:
        reason = (
            f'{reason_prefix} The description says "{description}" but no safe '
            "allowed category can be assigned."
        )
    else:
        reason = f"{reason_prefix} The description is missing, so no safe allowed category can be assigned."
    return {
        "complaint_id": complaint_id,
        "category": "Other",
        "priority": priority,
        "reason": reason,
        "flag": "NEEDS_REVIEW",
    }


def classify_complaint(row: dict) -> dict:
    """Classify one row and return complaint_id, category, priority, reason, flag."""
    complaint_id = (row.get("complaint_id") or "").strip()
    description = (row.get("description") or "").strip()

    if not complaint_id or not description:
        return _review_result(complaint_id, description, "Required complaint fields are missing or malformed.")

    category_terms = (
        ("Pothole", ("pothole",)),
        ("Streetlight", ("streetlight", "street light", "lights out", "light out")),
        ("Drain Blockage", ("drain blocked", "blocked drain", "drainage blocked", "clogged drain")),
        ("Flooding", ("flood", "waterlogged")),
        ("Waste", ("garbage", "waste", "rubbish", "dumped", "dead animal", "bins")),
        ("Noise", ("noise", "music", "loud", "midnight")),
        ("Heritage Damage", ("heritage", "monument", "historic")),
        ("Heat Hazard", ("heatwave", "heat", "hot pavement")),
        ("Road Damage", (
            "road surface", "road cracked", "road damage", "sinking", "footpath",
            "manhole", "tiles broken", "upturned",
        )),
    )

    category = None
    evidence = None
    for candidate, terms in category_terms:
        evidence = _find_term(description, terms)
        if evidence:
            category = candidate
            break

    if category is None:
        return _review_result(complaint_id, description, "The complaint is genuinely ambiguous.")

    matched_severity = _find_term(description, SEVERITY_KEYWORDS)
    priority = "Urgent" if matched_severity else "Standard"
    reason = f'Classified as {category} because the description says "{evidence}"'
    if matched_severity:
        reason += f' and includes the severity word "{matched_severity}"'
    reason += "."

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": "",
    }


def batch_classify(input_path: str, output_path: str):
    """Classify all rows and write one result row for each readable CSV row."""
    source = Path(input_path)
    if not source.is_file():
        raise ValueError(f"Input CSV does not exist: {input_path}")

    with source.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = set(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("Input CSV has no header row")
        missing = sorted(REQUIRED_INPUT_FIELDS - fieldnames)
        if missing:
            raise ValueError("Input CSV is missing required columns: " + ", ".join(missing))

        results = []
        for row in reader:
            if None in row:
                # Keep the row, but do not trust a malformed column mapping.
                complaint_id = (row.get("complaint_id") or "").strip()
                description = (row.get("description") or "").strip()
                results.append(_review_result(
                    complaint_id,
                    description,
                    "The row has unexpected columns that do not match the header.",
                ))
            else:
                results.append(classify_complaint(row))

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = ["complaint_id", "category", "priority", "reason", "flag"]
    with destination.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input", required=True, help="Path to test_[city].csv")
    parser.add_argument("--output", required=True, help="Path to write results CSV")
    args = parser.parse_args()
    try:
        batch_classify(args.input, args.output)
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))
    print(f"Done. Results written to {args.output}")
