"""
Convert the Healthy Nation survey workbook (one row per respondent, one column per question) into a long-format table read by classify.py.

Output (all files are in the data/ folder):
    healthy_nation.csv          → id,requirement (only these two columns are sent to the model)
    healthy_nation_expected.csv → id,expected_label,respondent,category (reference labels; not sent to the model)

ID format: three-digit respondent ID - two-digit question number, e.g. 001-01. Questions 01–11 come from the FR worksheet; 12–22 come from the NFR worksheet.
IDs do not contain FR/NFR, so they do not hint at the answer to the model.
Content with no letters or digits (for example, just ".") is treated as blank; the main script displays SKIPPED.

Usage:
    python prepare_data.py Healthy_Nation_...xlsx
"""

import re
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
SHEETS = [("Functional Requirements", "FR"), ("Non-Functional Requirements", "NFR")]
META_COLUMNS = ["Id", "Start time", "Completion time", "Email", "Name"]


def clean(text):
    text = str(text).strip()
    return text if re.search(r"[A-Za-z0-9]", text) else ""


def main(src):
    rows, expected = [], []
    q = 0
    sheets = {}
    for sheet, label in SHEETS:
        df = pd.read_excel(src, sheet_name=sheet, dtype=str, keep_default_na=False)
        if list(df.columns[:5]) != META_COLUMNS:
            raise SystemExit(f"{sheet}: the first five columns do not match {META_COLUMNS}")
        if not df["Id"].is_unique:
            raise SystemExit(f"{sheet} has duplicate IDs")
        cols = list(df.columns[5:])
        sheets[sheet] = (df.set_index("Id"), [(q + k + 1, c) for k, c in enumerate(cols)], label)
        q += len(cols)

    ids = list(sheets[SHEETS[0][0]][0].index)
    if set(ids) != set(sheets[SHEETS[1][0]][0].index):
        raise SystemExit("Respondent IDs do not match between the two worksheets")
    for rid in sorted(ids, key=int):
        for sheet, _ in SHEETS:
            df, cols, label = sheets[sheet]
            for qn, col in cols:
                record_id = f"{int(rid):03d}-{qn:02d}"
                rows.append({"id": record_id, "requirement": clean(df.at[rid, col])})
                expected.append({"id": record_id, "expected_label": label,
                                 "respondent": rid, "category": col})

    out = SCRIPT_DIR / "data"
    out.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "healthy_nation.csv", index=False, encoding="utf-8")
    pd.DataFrame(expected).to_csv(out / "healthy_nation_expected.csv", index=False, encoding="utf-8")
    empty = sum(1 for r in rows if not r["requirement"])
    print(f"Respondents: {len(ids)}; questions: {q}; total {len(rows)} rows (blank: {empty})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python prepare_data.py <xlsx_path>")
    main(sys.argv[1])
