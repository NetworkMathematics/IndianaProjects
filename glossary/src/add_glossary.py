"""
1. copy 'combined' sheet verbatim to combined_new.xlsx
2. append 'glossary' column: 1 if normalized title matches an extracted term, else 0
3. export extracted terms with NO match in combined, extracted_only.csv
"""

import csv, re, unicodedata, shutil, openpyxl
from pathlib import Path

SRC_XLSX     = Path("combined.xlsx")
SRC_CSV      = Path("extracted.csv")
OUT_XLSX     = Path("combined_new.xlsx")
OUT_ONLY_CSV = Path("extracted_only.csv")

DASH_RE = re.compile(r'[-\u2010\u2011\u2012\u2013\u2014\u2015]')

def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = DASH_RE.sub(" ", s)
    return re.sub(r'\s+', ' ', s).lower().strip()

def stem(s: str) -> str:
    n = norm(s)
    return n[:-1] if n.endswith("s") else n

# load extracted terms 
with open(SRC_CSV, encoding="utf-8") as f:
    glossary_terms = [r["term"] for r in csv.DictReader(f)]

norm_to_term: dict[str, str] = {}
stem_to_terms: dict[str, list[str]] = {}
for t in glossary_terms:
    norm_to_term.setdefault(norm(t), t)
    stem_to_terms.setdefault(stem(t), []).append(t)

def find_match(title: str):
    n, s = norm(title), stem(title)
    if n in norm_to_term:
        return norm_to_term[n]
    for candidate in stem_to_terms.get(s, []):
        if norm(candidate) == n or stem(candidate) == s:
            return candidate
    return None

# build combined_new.xlsx 
shutil.copy(SRC_XLSX, OUT_XLSX)
wb = openpyxl.load_workbook(OUT_XLSX)
ws = wb["combined"]

glossary_col = ws.max_column + 1
ws.cell(1, glossary_col).value = "glossary"

matched_glossary_terms: set[str] = set()

for row in range(2, ws.max_row + 1):
    title = ws.cell(row, 1).value
    if title is None:
        continue
    match = find_match(str(title))
    ws.cell(row, glossary_col).value = 1 if match else 0
    if match:
        matched_glossary_terms.add(norm(match))

wb.save(OUT_XLSX)
print(f"combined_new.xlsx saved — glossary col {glossary_col}")
print(f"  Titles matched : {len(matched_glossary_terms)}")

# extracted_only.csv 
extracted_only = [
    t for t in glossary_terms
    if norm(t) not in matched_glossary_terms
    and stem(t) not in {stem(m) for m in matched_glossary_terms}
]

with open(OUT_ONLY_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["term"])
    for t in extracted_only:
        writer.writerow([t])

print(f"extracted_only.csv saved; {len(extracted_only)} terms")