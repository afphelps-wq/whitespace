"""Startup Idea Checker: compare a pitch against ~1,500 YC companies by meaning."""
import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import llm
from config import (DUP_MAX, MIN_YEAR, OLLAMA_MODEL, RAW_PATH, REPORT_TOP, SELECTED_IDS_PATH,
                    SIMILAR_MAX)
from db import (add_pitch, company_filter, find_similar_pitches, get_companies, get_pitches,
                list_pitches, reset_pitches, search_companies)
from scoring import analyze, format_report

MENU = """
--- Whitespace ---
1. Check a new idea
2. Search my past pitches
3. Show all my saved pitches
4. Toggle pitch rewrite (currently {rewrite})
5. Stats
6. Quit"""

TEMPLATE = ("We are [company] and we build [x] for [y]. This solves [real problem]. "
            "[Relatable example of the problem]. Our unique insight is [non-obvious understanding "
            "of the market or technology].")
MAX_WORDS = 150
ECHO = not sys.stdin.isatty()  # scripted runs: echo answers so the transcript reads like a session


def ask(prompt):
    answer = input(prompt)
    if ECHO:
        print(answer)
    return answer.strip()


def ask_multiline():
    lines = []
    while True:
        line = ask("> " if not lines else "  ")
        if not line:
            return " ".join(lines)
        lines.append(line)


def ask_year():
    while True:
        raw = ask("Batch year from (blank = all): ")
        if not raw:
            return None
        if raw.isdigit() and len(raw) == 4:
            return int(raw)
        print("  Enter a 4-digit year like 2020, or leave blank.")


def print_top(results):
    """Top companies with distances only: used when there's no verdict."""
    for i, (m, d) in enumerate(zip(results["metadatas"][0][:REPORT_TOP], results["distances"][0]), 1):
        print(f"  {i}. {m['name']} ({m['batch']}, {m['status']})  distance {d:.3f}")
        print(f"     {m['one_liner']}")
        print(f"     {m['website'] or '(no website)'}  |  {m['yc_url']}")


def print_advice(text, top):
    print("\nAsking the local LLM for advice...")
    advice = llm.advise(text, top)
    if not advice:
        print("(No advice this time; the LLM is unavailable.)")
        return
    print(f"\nMarket summary: {advice['summary']}")
    print("Ways to stand out:")
    for a in advice["angles"]:
        print(f"  - {a}")


def save_with_duplicate_check(text, verdict, top_match):
    closest = find_similar_pitches(text, n=1)
    if closest:
        _, prev_text, created, dist = closest[0]
        dist = max(dist, 0.0)  # float rounding can give -0.000 for identical text
        if dist <= DUP_MAX:
            print(f"\nYou already saved a nearly identical pitch on {created[:10]} (distance {dist:.3f}):")
            print(f"  {prev_text}")
            if ask("Save anyway? (y/N): ").lower() != "y":
                print("Not saved.")
                return
        elif dist <= SIMILAR_MAX:
            print(f"\nNote: this is close to a pitch you saved on {created[:10]} (distance {dist:.3f}):")
            print(f"  {prev_text}")
    add_pitch(text, verdict=verdict, top_match=top_match)
    print(f"Saved to your pitches ({get_pitches().count()} total).")


def check_idea(state):
    print("\nDescribe your idea. A one-liner is fine, or use the template:")
    print(f"  {TEMPLATE}")
    print("Finish with an empty line.")
    text = ask_multiline()
    if not text:
        print("Nothing entered.")
        return
    words = len(text.split())
    if words > MAX_WORDS:
        print(f"Warning: {words} words. Text past about {MAX_WORDS} words is ignored by the embedding model.")

    active_only = ask("Only active companies? (y/N): ").lower() == "y"
    where = company_filter(active_only, ask_year())

    rewrite = None
    if state["rewrite"]:
        print("\nRewriting as a pitch...")
        rewrite = llm.rewrite_to_pitch(text)
        if rewrite is None:
            print("Rewrite failed, so this check uses your raw text with no verdict.")

    if rewrite:
        print(f"\nOriginal: {text}")
        print(f"Rewrite:  {rewrite}")
        results = search_companies(rewrite, where=where)
    else:
        results = search_companies(text, where=where)
    if not results["ids"][0]:
        print("No companies match those filters.")
        return

    print()
    if rewrite:
        a = analyze(results)
        print(format_report(a))
        print_advice(text, a["top"])
        verdict, top_match = a["verdict"], a["top"][0]["name"]
    else:
        print(f"Closest {REPORT_TOP} YC companies to your text:")
        print_top(results)
        print("\nNo verdict: verdict thresholds are calibrated for pitch-style text "
              "(\"An app that...\"). Turn rewrite on (option 4) or phrase it as a pitch for one.")
        verdict, top_match = "", results["metadatas"][0][0]["name"]
    save_with_duplicate_check(text, verdict, top_match)


def search_pitches():
    if get_pitches().count() == 0:
        print("\nNo saved pitches yet.")
        return
    query = ask("\nSearch your pitches for: ")
    if not query:
        return
    for i, (_, text, created, dist) in enumerate(find_similar_pitches(query), 1):
        print(f"  {i}. {created[:10]}  distance {max(dist, 0.0):.3f}")
        print(f"     {text}")


def show_pitches():
    rows = list_pitches()
    if not rows:
        print("\nNo saved pitches yet.")
        return
    print(f"\n{len(rows)} saved pitch(es):")
    for i, (_, text, m) in enumerate(rows, 1):
        verdict = m["verdict"] or "no verdict"
        top = f", top match {m['top_match']}" if m["top_match"] else ""
        print(f"  {i}. {m['created_at'][:16].replace('T', ' ')}  [{verdict}{top}]")
        print(f"     {text}")


def toggle_rewrite(state):
    if state["rewrite"]:
        state["rewrite"] = False
        print("\nRewrite is OFF: searches use your raw text and show no verdict.")
    elif llm.is_available():
        state["rewrite"] = True
        print("\nRewrite is ON.")
    else:
        print(f"\nCan't turn rewrite on: Ollama isn't reachable or {OLLAMA_MODEL} isn't pulled.")


def stats():
    companies = get_companies()
    metas = companies.get(include=["metadatas"])["metadatas"]
    years = [m["batch_year"] for m in metas]
    print(f"\nyc_companies: {companies.count()} companies, batches {min(years)}-{max(years)}")
    for status, n in Counter(m["status"] for m in metas).most_common():
        print(f"  {status:<9} {n:5d}  ({n / len(metas):.0%})")
    print(f"my_pitches:   {get_pitches().count()} saved")
    raw = Path(RAW_PATH)
    snapshot = datetime.fromtimestamp(raw.stat().st_mtime).strftime("%Y-%m-%d") if raw.exists() else "unknown"
    print(f"Data snapshot: yc-oss API downloaded {snapshot}; sample of {MIN_YEAR}+ companies "
          f"listed in {SELECTED_IDS_PATH}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset-pitches", action="store_true", help="delete all saved pitches before starting")
    args = ap.parse_args()
    if args.reset_pitches:
        reset_pitches()
        print("All saved pitches deleted.")

    state = {"rewrite": llm.is_available()}
    if not state["rewrite"]:
        print(f"Note: Ollama isn't reachable (or {OLLAMA_MODEL} isn't pulled), so rewrite and advice are "
              "off. Searches still work.")
    actions = {"1": lambda: check_idea(state), "2": search_pitches, "3": show_pitches,
               "4": lambda: toggle_rewrite(state), "5": stats}
    while True:
        print(MENU.format(rewrite="ON" if state["rewrite"] else "OFF"))
        try:
            choice = ask("Choose 1-6: ")
        except EOFError:
            print()
            break
        if choice == "6":
            break
        if choice in actions:
            try:
                actions[choice]()
            except EOFError:
                print()
                break
        else:
            print("Please enter a number from 1 to 6.")
    print("Bye.")


if __name__ == "__main__":
    main()
