"""UC-0A municipal complaint classifier.

The rules deliberately use only the complaint description and always emit values
from the fixed assignment taxonomy.
"""

import argparse
import csv
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


def _evidence(description: str, terms) -> str:
    """Return a complete exact word or phrase from the description."""
    lowered = description.lower()
    for term in terms:
        if term in lowered:
            start = lowered.find(term)
            return description[start : start + len(term)]
    return description.strip()[:80].strip(" ,.;:")


def classify_complaint(row: dict) -> dict:
    """Classify one row and return complaint_id, category, priority, reason, flag."""
    complaint_id = (row.get("complaint_id") or "").strip()
    description = (row.get("description") or "").strip()

    if not complaint_id or not description:
        return {
            "complaint_id": complaint_id,
            "category": "Other",
            "priority": "Standard",
            "reason": "Required complaint fields are missing or malformed.",
            "flag": "NEEDS_REVIEW",
        }
    lowered = description.lower()

    # Specific infrastructure terms take precedence over broader symptoms.
    if any(term in lowered for term in ("pothole", "potholes")):
        category, terms = "Pothole", ("pothole",)
    elif any(term in lowered for term in ("streetlight", "street light", "lights out", "light out")):
        category, terms = "Streetlight", ("streetlight", "street light", "lights out", "light")
    elif any(term in lowered for term in ("drain blocked", "blocked drain", "drainage blocked", "clogged drain")):
        category, terms = "Drain Blockage", ("drain blocked", "blocked drain", "drainage blocked", "clogged drain")
    elif any(term in lowered for term in ("flood", "flooded", "flooding", "waterlogged")):
        category, terms = "Flooding", ("flood", "flooded", "flooding", "waterlogged")
    elif any(term in lowered for term in ("garbage", "waste", "rubbish", "dumped", "dead animal", "bins")):
        category, terms = "Waste", ("garbage", "waste", "rubbish", "dumped", "dead animal", "bins")
    elif any(term in lowered for term in ("noise", "music", "loud", "midnight")):
        category, terms = "Noise", ("noise", "music", "loud", "midnight")
    elif any(term in lowered for term in ("heritage", "monument", "historic")):
        category, terms = "Heritage Damage", ("heritage", "monument", "historic")
    elif any(term in lowered for term in ("heat", "hot pavement", "heatwave")):
        category, terms = "Heat Hazard", ("heat", "hot pavement", "heatwave")
    elif any(term in lowered for term in (
        "road surface", "road cracked", "road damage", "sinking", "footpath",
        "manhole", "tiles broken", "upturned",
    )):
        category, terms = "Road Damage", (
            "road surface", "road cracked", "road damage", "sinking", "footpath",
            "manhole", "tiles broken", "upturned",
        )
    else:
        return {
            "complaint_id": complaint_id,
            "category": "Other",
            "priority": "Urgent" if any(word in lowered for word in SEVERITY_KEYWORDS) else "Standard",
            "reason": f"The description says '{_evidence(description, ())}', but it does not identify one allowed category.",
            "flag": "NEEDS_REVIEW",
        }

    severity_word = next((word for word in SEVERITY_KEYWORDS if word in lowered), None)
    priority = "Urgent" if severity_word else "Standard"
    reason = f"Classified as {category} because the description says '{_evidence(description, terms)}'"
    if severity_word:
        reason += f" and includes the severity word '{severity_word}'"
    reason += "."

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": "",
    }


def batch_classify(input_path: str, output_path: str):
    """Classify all readable CSV rows and write one result row for each."""
    source = Path(input_path)
    if not source.is_file():
        raise ValueError(f"Input CSV does not exist: {input_path}")

    with source.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        if not reader.fieldnames:
            raise ValueError("Input CSV has no header row")
        results = []
        for row in reader:
            if None in row:
                # The row has more columns than the header declares, so its
                # fields cannot be reliably mapped to the schema.
                results.append({
                    "complaint_id": (row.get("complaint_id") or "").strip(),
                    "category": "Other",
                    "priority": "Standard",
                    "reason": "Row has unexpected columns that do not match the header.",
                    "flag": "NEEDS_REVIEW",
                })
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
