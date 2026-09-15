```python
"""
UC-0A — Complaint Classifier
Rule-based implementation guided by agents.md and skills.md.
"""

import argparse
import csv
import re


ALLOWED_CATEGORIES = [
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
]

ALLOWED_PRIORITIES = ["Urgent", "Standard", "Low"]

SEVERITY_KEYWORDS = [
    "injury",
    "child",
    "school",
    "hospital",
    "ambulance",
    "fire",
    "hazard",
    "fell",
    "collapse",
]


def _contains_keyword(text: str, keyword: str) -> bool:
    """Case-insensitive whole-word keyword check."""
    return re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE) is not None


def _find_severity_keyword(text: str):
    """Return the first matching severity keyword, if any."""
    for keyword in SEVERITY_KEYWORDS:
        if _contains_keyword(text, keyword):
            return keyword
    return None


def _classify_category(description: str):
    """
    Determine the best-supported category from the complaint description.

    Returns:
        (category, ambiguous)
    """
    text = description.lower()

    matches = []

    category_terms = {
        "Pothole": ["pothole"],
        "Flooding": ["flood", "flooded", "flooding", "waterlogged", "water logging"],
        "Streetlight": ["streetlight", "street light", "lights out", "light out"],
        "Waste": [
            "garbage",
            "waste",
            "dumped",
            "dumping",
            "dead animal",
            "overflowing bins",
            "waste bins",
        ],
        "Noise": [
            "noise",
            "music",
            "loud",
            "sound",
            "playing music",
        ],
        "Road Damage": [
            "road surface",
            "road damage",
            "cracked road",
            "cracked",
            "sinking",
            "broken road",
            "tiles broken",
            "footpath",
            "manhole",
        ],
        "Heritage Damage": [
            "heritage",
            "historic",
            "historical",
            "old city",
        ],
        "Heat Hazard": [
            "heat",
            "extreme heat",
            "heatwave",
            "hot weather",
        ],
        "Drain Blockage": [
            "drain blocked",
            "blocked drain",
            "drain blockage",
            "drain",
        ],
    }

    for category, terms in category_terms.items():
        if any(term in text for term in terms):
            matches.append(category)

    # Remove obvious overlaps where a more specific issue is present.
    if "Drain Blockage" in matches and "Flooding" in matches:
        # Flooding is the primary category when the complaint explicitly
        # describes flooding and separately mentions a blocked drain.
        matches.remove("Drain Blockage")

    if "Heritage Damage" in matches and "Streetlight" in matches:
        # A heritage-area streetlight complaint is still a Streetlight issue
        # unless the heritage structure itself is damaged.
        matches.remove("Heritage Damage")

    if not matches:
        return "Other", False

    if len(matches) == 1:
        return matches[0], False

    return matches[0], True


def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row.

    Returns:
        complaint_id, category, priority, reason, flag
    """
    complaint_id = (row.get("complaint_id") or "").strip()
    description = (row.get("description") or "").strip()

    if not description:
        return {
            "complaint_id": complaint_id,
            "category": "Other",
            "priority": "Standard",
            "reason": "No complaint description was provided.",
            "flag": "NEEDS_REVIEW",
        }

    category, ambiguous = _classify_category(description)

    severity_keyword = _find_severity_keyword(description)

    if severity_keyword:
        priority = "Urgent"
        reason = (
            f'The complaint describes "{category.lower()}" and contains '
            f'the severity keyword "{severity_keyword}", requiring urgent priority.'
        )
    else:
        priority = "Standard"
        reason = (
            f'The description specifically mentions "{description[:80].rstrip(".")}" '
            f'and supports the "{category}" category.'
        )

    # Keep reason to exactly one sentence.
    reason = reason.strip()

    flag = "NEEDS_REVIEW" if ambiguous else ""

    # Final schema enforcement.
    if category not in ALLOWED_CATEGORIES:
        category = "Other"
        flag = "NEEDS_REVIEW"

    if priority not in ALLOWED_PRIORITIES:
        priority = "Standard"

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag,
    }


def batch_classify(input_path: str, output_path: str):
    """
    Read input CSV, classify every row, and write results CSV.

    Bad rows are not allowed to stop the entire batch.
    """
    results = []

    with open(input_path, "r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)

        if not reader.fieldnames:
            raise ValueError("Input CSV has no header row.")

        for row in reader:
            try:
                result = classify_complaint(row)
            except Exception as exc:
                result = {
                    "complaint_id": (row.get("complaint_id") or "").strip(),
                    "category": "Other",
                    "priority": "Standard",
                    "reason": f"Classification failed for this row: {str(exc)}.",
                    "flag": "NEEDS_REVIEW",
                }

            results.append(result)

    fieldnames = [
        "complaint_id",
        "category",
        "priority",
        "reason",
        "flag",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input", required=True, help="Path to test_[city].csv")
    parser.add_argument("--output", required=True, help="Path to write results CSV")
    args = parser.parse_args()

    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
```
