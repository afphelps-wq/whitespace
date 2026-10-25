"""Clean, sample, and embed YC companies into the Chroma collection."""
import argparse
import json
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import chromadb

from config import (BATCH_SIZE, CHROMA_PATH, COLLECTION, FORCE_INCLUDE, MAX_DOC_CHARS, MIN_YEAR,
                    RAW_PATH, SEED, SELECTED_IDS_PATH, TARGET_N)
from inspect_data import batch_year, download, text

HIRING = re.compile(
    r"\b(we['’]?re hiring|(is|are) hiring|join (us|our team)|check out our open roles|we['’]?re looking for)\b",
    re.IGNORECASE,
)


def load_pool():
    """2015+ companies with a non-empty long_description ('Unspecified' batch has no year, so it drops).
    Downloads the raw file first if it's missing."""
    download()  # inspect_data writes to the same path as RAW_PATH
    data = json.loads(Path(RAW_PATH).read_text())
    return {r["slug"]: r for r in data
            if (batch_year(r.get("batch")) or 0) >= MIN_YEAR and text(r, "long_description")}


def clean_description(s):
    """Returns (cleaned text, list of removed hiring sentences).

    Sentence boundaries are . ! ? plus original line breaks and " - " list markers (the dash stays
    with the item), so an unpunctuated "We are hiring" line can't take the whole description with it.
    """
    lines = [ln for ln in re.split(r"\r\n|\r|\n", s) if not ln.strip().startswith("*")]
    sentences = []
    for ln in lines:
        ln = re.sub(r"\s+", " ", ln).strip()
        sentences += [x for x in re.split(r"(?<=[.!?])\s+|\s+(?=-\s)", ln) if x]
    kept = [x for x in sentences if not HIRING.search(x)]
    return " ".join(kept), [x for x in sentences if HIRING.search(x)]


def clean_one_liner(s):
    return re.sub(r"\s+", " ", s).strip()


def make_document(name, one_liner, desc):
    """A one_liner cut off upstream ("…") is left out when there's a description to stand in for it."""
    if one_liner.endswith("…") and desc:
        one_liner = ""
    head = f"{name}: {one_liner.rstrip('.')}. " if one_liner else f"{name}: "
    doc = head + desc
    if len(doc) > MAX_DOC_CHARS:
        doc = doc[:MAX_DOC_CHARS].rsplit(" ", 1)[0]
    return doc


def make_metadata(r, one_liner):
    return {
        "name": text(r, "name"),
        "one_liner": one_liner,
        "batch": text(r, "batch"),
        "batch_year": batch_year(r["batch"]),
        "status": text(r, "status"),
        "industries": ", ".join(r.get("industries") or []),
        "website": text(r, "website"),
        "yc_url": text(r, "url"),
    }


def sample_slugs(pool):
    """FORCE_INCLUDE first, then fill to TARGET_N, sampling each batch year in proportion to its pool share."""
    forced = [s for s in FORCE_INCLUDE if s in pool]
    for s in FORCE_INCLUDE:
        if s not in pool:
            print(f"WARNING: force-include {s!r} is not in the pool, skipping")

    by_year = defaultdict(list)
    for slug in sorted(pool):
        if slug not in forced:
            by_year[batch_year(pool[slug]["batch"])].append(slug)
    remaining = TARGET_N - len(forced)
    total = sum(len(v) for v in by_year.values())

    # largest-remainder rounding so per-year quotas sum exactly to `remaining`
    exact = {y: remaining * len(v) / total for y, v in by_year.items()}
    quota = {y: int(e) for y, e in exact.items()}
    for y in sorted(exact, key=lambda y: exact[y] - quota[y], reverse=True)[:remaining - sum(quota.values())]:
        quota[y] += 1

    rng = random.Random(SEED)
    sampled = []
    for y in sorted(by_year):
        sampled += rng.sample(by_year[y], quota[y])
    return forced + sampled


def select_slugs(pool):
    path = Path(SELECTED_IDS_PATH)
    if path.exists():
        slugs = [s for s in path.read_text().split() if s]
        missing = [s for s in slugs if s not in pool]
        if missing:
            print(f"WARNING: {len(missing)} selected slugs missing upstream, skipping: {missing}")
        print(f"using {len(slugs) - len(missing)} slugs from {path}")
        return [s for s in slugs if s in pool]
    slugs = sample_slugs(pool)
    path.write_text("\n".join(slugs) + "\n")
    print(f"sampled {len(slugs)} slugs (seed={SEED}), wrote {path}")
    return slugs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true", help="delete and recreate the collection")
    ap.add_argument("--limit", type=int, help="only embed the first N selected companies")
    args = ap.parse_args()

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    if args.rebuild:
        if COLLECTION in [c.name for c in client.list_collections()]:
            client.delete_collection(COLLECTION)
            print(f"deleted collection {COLLECTION!r}")
    collection = client.get_or_create_collection(
        name=COLLECTION,
        configuration={"hnsw": {"space": "cosine"}},
    )
    if collection.count() > 0:
        print(f"{COLLECTION!r} already has {collection.count()} items; pass --rebuild to re-ingest")
        return

    pool = load_pool()
    print(f"pool: {len(pool)} companies ({MIN_YEAR}+, non-empty long_description)")
    slugs = select_slugs(pool)

    ids, docs, metas, hiring_removed, cut_liners = [], [], [], [], 0
    for slug in slugs:
        r = pool[slug]
        desc, removed = clean_description(text(r, "long_description"))
        hiring_removed += [(slug, x) for x in removed]
        one_liner = clean_one_liner(text(r, "one_liner"))
        cut_liners += one_liner.endswith("…") and bool(desc)
        ids.append(slug)
        docs.append(make_document(text(r, "name"), one_liner, desc))
        metas.append(make_metadata(r, one_liner))
    print(f"hiring sentences removed across {len(slugs)} selected companies: {len(hiring_removed)}")
    for slug, x in hiring_removed:
        print(f"  [{slug}] {x}")
    print(f"documents that left out a cut-off one_liner: {cut_liners}")
    print("status:", dict(Counter(m["status"] for m in metas).most_common()))

    if args.limit:
        ids, docs, metas = ids[:args.limit], docs[:args.limit], metas[:args.limit]
        print(f"--limit {args.limit}: embedding first {len(ids)} only")

    start = time.perf_counter()
    for i in range(0, len(ids), BATCH_SIZE):
        j = i + BATCH_SIZE
        collection.add(ids=ids[i:j], documents=docs[i:j], metadatas=metas[i:j])
        print(f"  added {min(j, len(ids))}/{len(ids)}  ({time.perf_counter() - start:.1f}s)")
    elapsed = time.perf_counter() - start
    print(f"done: {collection.count()} items in {COLLECTION!r}, embed+add took {elapsed:.1f}s "
          f"({elapsed / len(ids):.3f}s/company)")


if __name__ == "__main__":
    main()
