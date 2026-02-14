import re
import os

prd_path = r"c:\Users\Karim Keshavjee\Documents\Antigravity\PRODUCT_REQUIREMENTS.md"
with open(prd_path, "r", encoding="utf-8") as f:
    content = f.read()

# Find all [cite: 1, 2, 3] patterns
matches = re.findall(r"\[cite:\s*(.*?)\]", content)

# Flatten and extract unique IDs
unique_ids = set()
for match in matches:
    ids = [i.strip() for i in match.split(",")]
    unique_ids.update(ids)

sorted_ids = sorted(list(unique_ids), key=lambda x: int(x) if x.isdigit() else x)

print("Unique Citation IDs found:")
for cid in sorted_ids:
    print(cid)
