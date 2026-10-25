"""Milestone 6 check: run the calibration pitches through search + analyze and compare verdicts."""
from db import search_companies
from explore_queries import VARIANT_GROUPS
from scoring import analyze, format_report

EXPECTED = {
    "Corporate cards for startups that automatically categorize every expense": "Taken",
    "An AI bot that reviews pull requests and leaves comments like a senior engineer": "Crowded",
    "Software that automates medical billing and appeals denied insurance claims for hospitals": "Taken",
    "Payroll and compliance for companies hiring contractors in other countries": "Some neighbors",
    "Open-source tracing and evaluation tools for LLM applications": "Taken",
    "A subscription service that rents out trained goats to clear invasive weeds": "Open",
    "Matching amateur choirs with retirement homes for weekly concerts": "Open",
    "A marketplace for renting idle church kitchens to food startups": "Some neighbors",
    "A smart collar that turns cat sounds into mood alerts for owners": "Open",
    "Booking professional mourners for funerals": "Open",
}


def main():
    pitches = [q for group, _, qs in VARIANT_GROUPS if group in ("crowded", "niche") for q in qs]
    summary = []
    for p in pitches:
        a = analyze(search_companies(p))
        print("=" * 100)
        print(f"PITCH: {p}")
        print(format_report(a))
        summary.append((p, EXPECTED[p], a))

    print("=" * 100)
    print(f"\n{'pitch':<70} {'expected':<15} {'got':<15} {'best':>6} {'rel':>4}")
    for p, exp, a in summary:
        mark = "" if a["verdict"] == exp else "  <-- MISMATCH"
        print(f"{p[:70]:<70} {exp:<15} {a['verdict']:<15} {a['best_distance']:6.3f} "
              f"{a['relevant_count']:4d}{mark}")
    print(f"\nmismatches: {sum(a['verdict'] != exp for _, exp, a in summary)}/{len(summary)}")


if __name__ == "__main__":
    main()
