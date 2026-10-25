"""Milestone 4: query the real collection and inspect raw results. No app logic.

`python3.14 explore_queries.py` runs sections 1-5; `python3.14 explore_queries.py 6` runs only the
query-variant and calibration section, and `... 7` only the README-query check.
"""
import sys
from pprint import pprint

import chromadb

from check_targets import content_words
from config import CHROMA_PATH, COLLECTION

QUERY_A = "I waste half my week emailing back and forth to find a time that works for everyone"
QUERY_B = "We just moved in and have no idea who on our street could watch the kids in a pinch"
TARGETS = {
    QUERY_A: ["meetingbird", "hera", "cron"],
    QUERY_B: ["allo", "poppy"],
}
REALISTIC = [
    "AI that drafts insurance claims for small clinics",
    "help restaurants stop throwing away food at the end of the night",
    "make it easy for landlords to screen tenants",
]
NONSENSE = [
    "purple elephant tax law banana",
    "asdf qwerty zxcv",
    "the weather was nice yesterday",
]
ALL_QUERIES = [QUERY_A, QUERY_B] + REALISTIC + NONSENSE
TOP = 5
KEYWORD_TOP = 15

# Section 6: paraphrases of the two test queries, plus pitches expected to be crowded vs. open
VARIANT_GROUPS = [
    ("A", ["hera", "meetingbird"], [
        "I waste half my week emailing back and forth to find a time that works for everyone",
        "I hate trying to figure out what times to meet with people, everyone's so busy",
        "I hate wasting time scheduling meetings",
    ]),
    ("B", ["allo", "poppy"], [
        "We just moved in and have no idea who on our street could watch the kids in a pinch",
        "I need to be able to find someone to watch my kids quickly!",
        "How do I know who to contact for child care when I just moved to a new neighborhood?",
    ]),
    ("crowded", [], [
        "Corporate cards for startups that automatically categorize every expense",
        "An AI bot that reviews pull requests and leaves comments like a senior engineer",
        "Software that automates medical billing and appeals denied insurance claims for hospitals",
        "Payroll and compliance for companies hiring contractors in other countries",
        "Open-source tracing and evaluation tools for LLM applications",
    ]),
    ("niche", [], [
        "A subscription service that rents out trained goats to clear invasive weeds",
        "Matching amateur choirs with retirement homes for weekly concerts",
        "A marketplace for renting idle church kitchens to food startups",
        "A smart collar that turns cat sounds into mood alerts for owners",
        "Booking professional mourners for funerals",
    ]),
]

# Section 7: README query candidates; None = not written yet, skipped
README_B = [
    ("B3", "How do I know who to contact for child care when I just moved to a new neighborhood?"),
    ("B3b", "How do I know who to contact for child care when I just moved somewhere new?"),
    ("B3c", None),
]
README_A = [("A1", QUERY_A)]
PREFIX_MIN = 4  # shorter stem must be at least this long to prefix-match ("new" won't hit "network")


def shared_words(query, doc):
    q, d = content_words(query), content_words(doc)
    return [q[k][0] for k in q if k in d]


def shared_words_prefix(query, doc):
    """Like shared_words, but stems also match when one is a prefix of the other
    ("neighborhood" ~ "neighbors"). Returns [(query word, [doc words])]."""
    q, d = content_words(query), content_words(doc)
    out = []
    for qk, qforms in q.items():
        hits = sorted({w for dk, dforms in d.items() for w in dforms
                       if qk == dk or (min(len(qk), len(dk)) >= PREFIX_MIN
                                       and (qk.startswith(dk) or dk.startswith(qk)))})
        if hits:
            out.append((qforms[0], hits))
    return out


def keyword_baseline(q, targets, doc_words):
    """Section 4's exact-stem keyword search over every document."""
    n = len(doc_words)
    qw = content_words(q)
    print(f"\n{q!r}")
    print(f"  query content words: {[v[0] for v in qw.values()]}")
    hits = {}
    for k, forms in qw.items():
        matched = [s for s, dw in doc_words.items() if k in dw]
        print(f"    {forms[0]!r}: {len(matched)} documents")
        for s in matched:
            hits.setdefault(s, []).append(forms[0])
    ranked = sorted(hits.items(), key=lambda kv: -len(kv[1]))
    print(f"  documents matching any word: {len(hits)}/{n}")
    print(f"  top {KEYWORD_TOP} by number of distinct query words matched:")
    for s, words in ranked[:KEYWORD_TOP]:
        print(f"    {len(words)}  {s}: {words}")
    kw_rank = {s: i for i, (s, _) in enumerate(ranked, 1)}
    for t in targets:
        if t in hits:
            print(f"  target {t}: matched {hits[t]}, keyword rank {kw_rank[t]}/{len(hits)} "
                  f"({sum(len(w) == len(hits[t]) for _, w in ranked)} docs tied at that word count)")
        else:
            print(f"  target {t}: NOT FOUND by keyword search")


def variants(collection):
    n = collection.count()
    queries = [q for _, _, qs in VARIANT_GROUPS for q in qs]
    res = collection.query(query_texts=queries, n_results=n, include=["metadatas", "distances"])
    full = {q: list(zip(res["ids"][i], res["metadatas"][i], res["distances"][i]))
            for i, q in enumerate(queries)}
    docs = dict(zip(*[collection.get(include=["documents"])[k] for k in ("ids", "documents")]))

    print(f"\n== 6. Query variants and calibration pitches ==")
    flags, summary = [], []
    for group, targets, qs in VARIANT_GROUPS:
        for q in qs:
            print(f"\n[{group}] {q!r}")
            for rank, (slug, m, dist) in enumerate(full[q][:TOP], 1):
                print(f"  {rank}. {dist:.4f}  {slug} | {m['name']} | {m['status']}")
            ranks = {slug: (rank, dist) for rank, (slug, _, dist) in enumerate(full[q], 1)}
            for t in targets:
                rank, dist = ranks[t]
                shared = shared_words(q, docs[t])
                flag = "   <-- FLAG: shares words" if shared else ""
                print(f"  target {t}: rank {rank}/{n}, distance {dist:.4f}, "
                      f"SHARED: {'[' + ', '.join(shared) + ']' if shared else 'none'}{flag}")
                if shared:
                    flags.append((q, t, shared))
            summary.append((q, group, full[q][0][2], full[q][TOP - 1][2]))

    print(f"\nFLAGGED variant/target pairs with shared words: {len(flags)}")
    for q, t, shared in flags:
        print(f"  {t} <- {q!r}: {shared}")

    print(f"\n{'query':<92} {'group':<8} {'best':>7} {'5th':>7}")
    for q, group, best, fifth in summary:
        print(f"{q[:92]:<92} {group:<8} {best:7.4f} {fifth:7.4f}")


def readme_check(collection):
    n = collection.count()
    docs = dict(zip(*[collection.get(include=["documents"])[k] for k in ("ids", "documents")]))
    print(f"\n== 7. README query check (prefix-based SHARED, shorter stem >= {PREFIX_MIN} chars) ==")

    def check(label, q, targets):
        res = collection.query(query_texts=[q], n_results=n, include=["distances"])
        ranks = {slug: (rank, dist)
                 for rank, (slug, dist) in enumerate(zip(res["ids"][0], res["distances"][0]), 1)}
        print(f"\n[{label}] {q!r}")
        out = {}
        for t in targets:
            rank, dist = ranks[t]
            shared = shared_words_prefix(q, docs[t])
            shown = ", ".join(f"{w}~{'/'.join(ds)}" for w, ds in shared) if shared else "none"
            print(f"  {t}: rank {rank}/{n}, distance {dist:.4f}, SHARED: {shown}")
            out[t] = (rank, shared)
        return out

    clean_b = []
    for label, q in README_B:
        if q is None:
            print(f"\n[{label}] skipped: no query text yet")
            continue
        r = check(label, q, ["allo", "poppy"])
        if r["allo"][0] <= TOP and not r["allo"][1]:
            clean_b.append((label, q))
    for label, q in README_A:
        check(label, q, ["hera"])

    print(f"\n-- keyword baseline for B variants with allo in top {TOP} and SHARED none --")
    if not clean_b:
        print("  none qualify")
    doc_words = {slug: content_words(d) for slug, d in docs.items()}
    for label, q in clean_b:
        print(f"\n[{label}]", end="")
        keyword_baseline(q, ["allo"], doc_words)


def main():
    collection = chromadb.PersistentClient(path=CHROMA_PATH).get_collection(COLLECTION)
    n = collection.count()
    print(f"collection {COLLECTION!r}: {n} items, space={collection.configuration['hnsw']['space']}")

    if sys.argv[1:] == ["6"]:
        variants(collection)
        return
    if sys.argv[1:] == ["7"]:
        readme_check(collection)
        return

    print(f"\n== 1. Raw result, Query A, n_results={TOP} ==")
    pprint(collection.query(query_texts=[QUERY_A], n_results=TOP), width=120)

    # rank every document for every query, so targets outside the top 5 still get a rank
    res = collection.query(query_texts=ALL_QUERIES, n_results=n, include=["metadatas", "distances"])
    full = {q: list(zip(res["ids"][i], res["metadatas"][i], res["distances"][i]))
            for i, q in enumerate(ALL_QUERIES)}

    print(f"\n== 2. Top {TOP} per query ==")
    for q in ALL_QUERIES:
        print(f"\n{q!r}")
        for rank, (slug, m, dist) in enumerate(full[q][:TOP], 1):
            print(f"  {rank}. {dist:.4f}  {slug} | {m['name']} | {m['status']} | {m['batch']}")

    docs = dict(zip(*[collection.get(include=["documents"])[k] for k in ("ids", "documents")]))

    print(f"\n== 3. Target ranks and word overlap with the full embedded document ==")
    for q, targets in TARGETS.items():
        print(f"\n{q!r}")
        ranks = {slug: (rank, dist) for rank, (slug, _, dist) in enumerate(full[q], 1)}
        for t in targets:
            rank, dist = ranks[t]
            shared = shared_words(q, docs[t])
            print(f"  {t}: rank {rank}/{n}, distance {dist:.4f}, "
                  f"SHARED: {'[' + ', '.join(shared) + ']' if shared else 'none'}")

    print(f"\n== 4. Keyword baseline over all {n} documents ==")
    doc_words = {slug: content_words(d) for slug, d in docs.items()}
    for q, targets in TARGETS.items():
        keyword_baseline(q, targets, doc_words)

    print(f"\n== 5. Distance summary ==")
    print(f"  {'query':<85} {'best':>7} {'5th':>7} {'gap':>7}")
    for q in ALL_QUERIES:
        best, fifth = full[q][0][2], full[q][TOP - 1][2]
        print(f"  {q[:85]:<85} {best:7.4f} {fifth:7.4f} {fifth - best:7.4f}")


if __name__ == "__main__":
    main()
