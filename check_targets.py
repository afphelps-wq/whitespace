"""Targeted Topic B search, then word-overlap between candidate targets and the test queries. No DB code."""
import json
import re
import sys

from inspect_data import PATH, batch_year, text

PHRASES_B = [
    "new city", "move", "moved", "relocat", "meet people", "meet new", "neighbor",
    "activity partner", "sports", "outdoor", "climbing", "hobby", "hobbies", "lonely", "loneliness",
]
LIMIT = 15

QUERY_A = "I waste half my week emailing back and forth to find a time that works for everyone"
QUERY_B = "I moved to a new city and don't know anyone who's into climbing"
FIXED_A = ["meetingbird", "cron", "hera"]

QUERY_B2 = "We just moved in and have no idea who on our street could watch the kids in a pinch"
PHRASES_NEIGHBOR = [
    "neighbor", "neighbour", "babysit", "childcare", "nanny", "parents", "families",
    "local community", "nextdoor",
]
LIMIT_NEIGHBOR = 10

# NLTK's English stopword list, with apostrophes removed to match tokenize()
STOPWORDS = set("""
i me my myself we our ours ourselves you youre youve youll youd your yours yourself yourselves
he him his himself she shes her hers herself it its itself they them their theirs themselves
what which who whom this that thatll these those am is are was were be been being have has had
having do does did doing a an the and but if or because as until while of at by for with about
against between into through during before after above below to from up down in out on off over
under again further then once here there when where why how all any both each few more most
other some such no nor not only own same so than too very s t can will just don dont should
shouldve now d ll m o re ve y ain aren arent couldn couldnt didn didnt doesn doesnt hadn hadnt
hasn hasnt haven havent isn isnt ma mightn mightnt mustn mustnt needn neednt shan shant shouldn
shouldnt wasn wasnt weren werent won wont wouldn wouldnt whos
""".split())


def load_pool():
    data = json.loads(PATH.read_text())
    return [r for r in data
            if (batch_year(r.get("batch")) or 0) >= 2015 and text(r, "long_description")]


def phrase_hits(phrases, s):
    s = s.lower()
    return [p for p in phrases if re.search(rf"\b{re.escape(p)}", s)]


def rank(pool, phrases):
    """[(score, record, hits)] best first; score = distinct phrases, one_liner hits count double."""
    scored = []
    for r in pool:
        in_liner = phrase_hits(phrases, text(r, "one_liner"))
        in_desc = phrase_hits(phrases, text(r, "long_description"))
        hits = set(in_liner) | set(in_desc)
        if hits:
            scored.append((2 * len(in_liner) + len(in_desc), r, hits))
    scored.sort(key=lambda t: -t[0])
    return scored


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def stem(w):
    """Light suffix stripping so email/emails/emailing and move/moved collapse together."""
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and not w.endswith("ss") and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "lsz":
        w = w[:-1]
    if len(w) > 3 and w.endswith("e"):
        w = w[:-1]
    return w


def content_words(s):
    """{stem: [surface forms]} for non-stopword tokens. Hyphens and punctuation split words."""
    s = re.sub(r"['’]", "", s.lower())
    out = {}
    for w in re.findall(r"[a-z0-9]+", s):
        if w not in STOPWORDS:
            out.setdefault(stem(w), []).append(w)
    return out


def print_shared(r, query, indent=""):
    desc = clean(text(r, "long_description"))
    q, d = content_words(query), content_words(desc)
    shared = [k for k in q if k in d]  # query order
    if shared:
        print(f"{indent}SHARED: [{', '.join(q[k][0] for k in shared)}]")
        print(f"{indent}  as written in description:",
              "; ".join(f"{q[k][0]} -> {'/'.join(sorted(set(d[k])))}" for k in shared))
    else:
        print(f"{indent}SHARED: none")


def overlap(r, query):
    print(f"\n--- {r['slug']} | {r['name']} | {r['batch']} | {r['status']} ---")
    print(clean(text(r, "long_description")))
    print_shared(r, query)


def print_ranked(scored, phrases, limit):
    for score, r, hits in scored[:limit]:
        print(f"[{score}] {r['slug']} | {r['name']} | {r['batch']} | {r['status']}")
        print(f"     {text(r, 'one_liner')}")
        print(f"     matched: {', '.join(p for p in phrases if p in hits)}")


def steps_1_2(pool, by_slug):
    scored = rank(pool, PHRASES_B)
    print(f"\n== Step 1: Topic B targeted search — {len(scored)} matches, top {LIMIT} ==")
    print_ranked(scored, PHRASES_B, LIMIT)

    print(f"\n== Step 2: word overlap ==")
    print(f"Query A: {QUERY_A!r}")
    for slug in FIXED_A:
        overlap(by_slug[slug], QUERY_A)
    print(f"\nQuery B: {QUERY_B!r}")
    for _, r, _ in scored[:3]:
        overlap(r, QUERY_B)


def step_3(pool, by_slug):
    print(f"\n== Step 3a: allo vs Query B ==")
    print(f"Query B: {QUERY_B2!r}")
    overlap(by_slug["allo"], QUERY_B2)

    scored = rank(pool, PHRASES_NEIGHBOR)
    print(f"\n== Step 3b: Allo's space — {len(scored)} matches, top {LIMIT_NEIGHBOR} ==")
    for score, r, hits in scored[:LIMIT_NEIGHBOR]:
        print_ranked([(score, r, hits)], PHRASES_NEIGHBOR, 1)
        print_shared(r, QUERY_B2, indent="     ")


def main():
    """Run all steps, or only the ones named on the command line (e.g. `check_targets.py 3`)."""
    pool = load_pool()
    by_slug = {r["slug"]: r for r in pool}
    print(f"pool: {len(pool)} companies (2015+, non-empty long_description)")

    steps = set(sys.argv[1:]) or {"1", "2", "3"}
    if steps & {"1", "2"}:
        steps_1_2(pool, by_slug)
    if "3" in steps:
        step_3(pool, by_slug)


if __name__ == "__main__":
    main()
