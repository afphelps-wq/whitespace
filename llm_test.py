"""Milestone 6b check: LLM rewrite + advice on the README queries and on holdout pitches."""
import time

from db import search_companies
from explore_queries import QUERY_A, QUERY_B
from llm import advise, rewrite_to_pitch
from scoring import analyze, format_report

README = [("A1", QUERY_A, "hera"), ("B1", QUERY_B, "allo")]
# thresholds in config.py were NOT fit on these
HOLDOUT = [
    "Uber for dog walking",
    "Software that helps small farms sell directly to restaurants",
    "An app that reminds people to call their grandparents",
    "AI that writes first drafts of grant proposals for nonprofits",
    "Rent-a-telescope service for backyard astronomers",
]

timings = []


def timed(label, fn, *args):
    start = time.perf_counter()
    out = fn(*args)
    timings.append((label, time.perf_counter() - start, out is not None))
    return out


def rewrite_and_score(label, text):
    rewrite = timed(f"rewrite {label}", rewrite_to_pitch, text)
    query = rewrite or text
    print(f"original: {text!r}")
    print(f"rewrite:  {rewrite!r}" + (f"  ({len(rewrite.split())} words)" if rewrite
                                      else "  (LLM unavailable, searching the original)"))
    return query, analyze(search_companies(query))


def main():
    for label, text, target in README:
        print("=" * 100)
        print(f"[{label}]")
        query, a = rewrite_and_score(label, text)
        print(format_report(a))
        top_names = [m["name"].lower() for m in a["top"]]
        print(f"\n{target} in top 5: {target in top_names}   graveyard warning fired: {a['graveyard']}")
        advice = timed(f"advise {label}", advise, text, a["top"])
        if advice:
            print(f"\nMarket summary: {advice['summary']}")
            names = [m["name"] for m in a["top"]]
            for i, angle in enumerate(advice["angles"], 1):
                named = [n for n in names if n.lower() in angle.lower()]
                print(f"  Angle {i}: {angle}")
                print(f"           names a listed company: {named or 'NO'}")
        else:
            print("\n(no advice: LLM unavailable)")

    print("=" * 100)
    print("HOLDOUT PITCHES")
    for i, text in enumerate(HOLDOUT, 1):
        print()
        _, a = rewrite_and_score(f"holdout {i}", text)
        top = a["top"][0]
        print(f"verdict:  {a['verdict']}  (best {a['best_distance']:.3f}: {top['name']}, "
              f"{a['relevant_count']} relevant, graveyard {a['graveyard']})")

    print("=" * 100)
    print("LLM call timing")
    for label, secs, ok in timings:
        print(f"  {label:<20} {secs:6.2f}s  {'ok' if ok else 'None'}")


if __name__ == "__main__":
    main()
