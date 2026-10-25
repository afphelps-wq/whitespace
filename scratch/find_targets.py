"""Keyword search for YC companies my two test queries should retrieve. No DB code."""
import json
import re

from inspect_data import PATH, batch_year, text

TOPICS = {
    "A: meeting times / calendars": [
        r"calendars?", r"schedul\w*", r"availability", r"booking", r"appointments?",
        r"meeting times?", r"time slots?",
    ],
    "B: meeting people / hobby communities": [
        r"communit\w*", r"social", r"hobb\w*", r"meetups?", r"local", r"connect\w*",
        r"friends?\w*", r"meet new people", r"like-minded", r"clubs?",
    ],
}
LIMIT = 15


def matches(patterns, s):
    s = s.lower()
    return [p for p in patterns if re.search(rf"\b{p}\b", s)]


def main():
    data = json.loads(PATH.read_text())
    pool = [r for r in data
            if (batch_year(r.get("batch")) or 0) >= 2015 and text(r, "long_description")]
    print(f"pool: {len(pool)} companies (2015+, non-empty long_description)")

    for topic, patterns in TOPICS.items():
        scored = []
        for r in pool:
            in_liner = matches(patterns, text(r, "one_liner"))
            in_desc = matches(patterns, text(r, "long_description"))
            hits = set(in_liner) | set(in_desc)
            if hits:
                # one_liner hits count double: it says what the company mainly does
                scored.append((2 * len(in_liner) + len(in_desc), r, hits))
        scored.sort(key=lambda t: -t[0])

        print(f"\n== Topic {topic} — {len(scored)} keyword matches, top {LIMIT} ==")
        for score, r, hits in scored[:LIMIT]:
            print(f"[{score}] {r['slug']} | {r['name']} | {r['batch']} | {r['status']}")
            print(f"     {text(r, 'one_liner')}")
            print(f"     matched: {', '.join(sorted(hits))}")


if __name__ == "__main__":
    main()
