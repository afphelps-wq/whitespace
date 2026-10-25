"""Milestone 5 check: saved pitches persist, are searchable right away, and duplicates are caught."""
import argparse

from config import DUP_MAX
from db import add_pitch, check_duplicate, find_similar_pitches, get_pitches, reset_pitches

PITCHES = [
    "An app that lets college students split grocery bills and track who owes what in shared apartments",
    "AI tutor that turns lecture recordings into practice quizzes for engineering courses",
    "Marketplace for renting camera gear from local photographers",
]
REWORDED_SEARCH = "a tool that automatically writes quiz questions from recorded class lectures"

DUP_CASES = [
    ("exact", PITCHES[0]),
    ("light rewording",
     "An app letting college students split grocery costs and track who owes what in shared apartments"),
    ("heavy rewording",
     "Roommates never know who paid for groceries, so this keeps a running tab and everyone settles up fairly"),
    ("unrelated", "Drone delivery of medical supplies to rural clinics"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset", action="store_true", help="delete and recreate my_pitches first")
    args = ap.parse_args()

    if args.reset:
        reset_pitches()
        print("reset my_pitches")

    pitches = get_pitches()
    print(f"my_pitches count at start: {pitches.count()}")
    if pitches.count() == 0:
        for p in PITCHES:
            print(f"  added {add_pitch(p)}  {p!r}")
    else:
        print("  already populated, not adding")
    print(f"my_pitches count now: {pitches.count()}")

    print(f"\n== search with different wording: {REWORDED_SEARCH!r} ==")
    for rank, (pid, text, created, dist) in enumerate(find_similar_pitches(REWORDED_SEARCH), 1):
        print(f"  {rank}. {dist:.4f}  {created}  {text!r}")

    print(f"\n== check_duplicate (DUP_MAX = {DUP_MAX}) against {PITCHES[0]!r} ==")
    for label, text in DUP_CASES:
        closest = find_similar_pitches(text, n=1)[0]
        dup = check_duplicate(text)
        print(f"  {label:<16} distance {closest[3]:.4f}  -> "
              f"{'DUPLICATE of ' + repr(dup[1][:40] + '...') if dup else 'None'}")
        print(f"  {'':<16} {text!r}")


if __name__ == "__main__":
    main()
