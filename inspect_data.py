"""Download the YC company corpus and print a profile of it. No DB code."""
import json
import re
import statistics
import urllib.request
from collections import Counter
from pathlib import Path

URL = "https://yc-oss.github.io/api/companies/all.json"
PATH = Path("data/raw/yc_all.json")


def download():
    if PATH.exists():
        print(f"{PATH} exists, skipping download")
        return
    PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL}")
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        PATH.write_bytes(r.read())


def text(rec, key):
    v = rec.get(key)
    return v.strip() if isinstance(v, str) else ""


def batch_year(batch):
    """Year from batch strings like 'Winter 2023', 'W23', 'Summer 2015'; None if unparseable."""
    if not isinstance(batch, str):
        return None
    m = re.search(r"(20\d\d)", batch)
    if m:
        return int(m.group(1))
    m = re.search(r"[A-Za-z](\d\d)$", batch.strip())
    return 2000 + int(m.group(1)) if m else None


def length_stats(records, key):
    lens = sorted(len(text(r, key)) for r in records if text(r, key))
    if not lens:
        return "no non-empty values"
    p90 = lens[int(0.9 * (len(lens) - 1))]
    return f"median={statistics.median(lens):.0f}  p90={p90}  (n={len(lens)} non-empty)"


def main():
    download()
    data = json.loads(PATH.read_text())
    print(f"\n== Size ==\ntotal records: {len(data)}")
    keys = sorted({k for r in data for k in r})
    print(f"keys on first record: {list(data[0].keys())}")
    print(f"union of keys across all records ({len(keys)}): {keys}")

    print("\n== Empty / missing text fields ==")
    for k in ("one_liner", "long_description"):
        print(f"{k}: {sum(1 for r in data if not text(r, k))} empty/missing")
        print(f"  length chars: {length_stats(data, k)}")

    print("\n== Batch format ==")
    batches = Counter(r.get("batch") for r in data)
    print(f"distinct batch values: {len(batches)}")
    print("sample:", sorted(map(str, batches))[:12])
    shapes = Counter(re.sub(r"\d", "9", re.sub(r"[A-Za-z]+", "A", str(b))) for b in batches.elements())
    print("shape patterns (A=letters, 9=digit):", dict(shapes))
    years = Counter(batch_year(r.get("batch")) for r in data)
    print("companies per batch year:")
    for y in sorted(years, key=lambda y: (y is None, y)):
        print(f"  {y}: {years[y]}")

    print("\n== Status ==")
    print("overall:", dict(Counter(r.get("status") for r in data)))
    print("by batch year (2015+):")
    by_year = {}
    for r in data:
        y = batch_year(r.get("batch"))
        if y and y >= 2015:
            by_year.setdefault(y, Counter())[r.get("status")] += 1
    for y in sorted(by_year):
        print(f"  {y}: {dict(by_year[y])}")

    def has_desc(r):
        return bool(text(r, "one_liner") or text(r, "long_description"))

    recent = [r for r in data if (batch_year(r.get("batch")) or 0) >= 2015]
    print("\n== 2015+ with a description ==")
    print(f"2015+ companies: {len(recent)}")
    print(f"with non-empty one_liner or long_description: {sum(map(has_desc, recent))}")
    print(f"with non-empty long_description: {sum(1 for r in recent if text(r, 'long_description'))}")
    print(f"with non-empty one_liner: {sum(1 for r in recent if text(r, 'one_liner'))}")

    print("\n== 3 example records ==")
    for r in data[:3]:
        print(json.dumps(r, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
