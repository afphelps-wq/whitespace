"""Turn a company search result into a verdict and a CLI report. No LLM."""
from collections import Counter
from datetime import datetime

from config import CROWDED_MIN_COUNT, GRAVEYARD_MIN, RELEVANT_MAX, REPORT_TOP, TAKEN_MAX

STATUS_GROUP = {"Active": "Active", "Acquired": "Acquired/Public", "Public": "Acquired/Public",
                "Inactive": "Inactive"}
GROUPS = ["Active", "Acquired/Public", "Inactive"]

VERDICT_TEXT = {
    "Taken": f"A YC company is already doing almost exactly this (best match <= {TAKEN_MAX}).",
    "Crowded": f"At least {CROWDED_MIN_COUNT} YC companies are close to this idea (<= {RELEVANT_MAX}).",
    "Some neighbors": "A few YC companies are nearby, but none is a direct match.",
    "Open": f"No YC company is close (best match > {RELEVANT_MAX}).",
}


def analyze(results):
    """`results` is a raw Chroma query result for a single query text, closest first."""
    matches = [{**m, "id": i, "distance": d}
               for i, m, d in zip(results["ids"][0], results["metadatas"][0], results["distances"][0])]
    best = matches[0]["distance"] if matches else 1.0
    relevant = [m for m in matches if m["distance"] <= RELEVANT_MAX]

    if best <= TAKEN_MAX:
        verdict = "Taken"
    elif len(relevant) >= CROWDED_MIN_COUNT:
        verdict = "Crowded"
    elif not relevant:
        verdict = "Open"
    else:
        verdict = "Some neighbors"

    counts = Counter(STATUS_GROUP.get(m["status"], m["status"]) for m in relevant)
    status = {g: counts.get(g, 0) for g in GROUPS}
    # graveyard looks at the top results regardless of distance: a dead space can sit just past RELEVANT_MAX
    top_inactive = sum(m["status"] == "Inactive" for m in matches[:REPORT_TOP])
    graveyard = top_inactive >= GRAVEYARD_MIN

    recent_year = datetime.now().year - 1
    recent = sum(m["batch_year"] >= recent_year for m in relevant)
    recency = bool(relevant) and recent > len(relevant) / 2

    return {
        "verdict": verdict,
        "best_distance": best,
        "relevant_count": len(relevant),
        "status": status,
        "graveyard": graveyard,
        "top_inactive": top_inactive,
        "recency": recency,
        "recent_count": recent,
        "recent_year": recent_year,
        "top": [{k: m[k] for k in ("name", "batch", "status", "distance", "one_liner", "website", "yc_url")}
                for m in matches[:REPORT_TOP]],
    }


def format_report(a):
    lines = [
        f"Verdict: {a['verdict'].upper()}",
        f"  {VERDICT_TEXT[a['verdict']]}",
        f"  Best match distance {a['best_distance']:.3f}; "
        f"{a['relevant_count']} relevant match(es) within {RELEVANT_MAX}.",
    ]
    if a["relevant_count"]:
        s = a["status"]
        lines.append(f"  Relevant matches: {s['Active']} active, {s['Acquired/Public']} acquired/public, "
                     f"{s['Inactive']} inactive.")
    if a["graveyard"]:
        lines.append(f"  ! Graveyard warning: {a['top_inactive']} of the {len(a['top'])} closest companies are "
                     "inactive. Find out why they died before building this.")
    if a["recency"]:
        lines.append(f"  ! Recency note: {a['recent_count']} of {a['relevant_count']} close matches are from "
                     f"{a['recent_year']} or later. This space is getting funded right now.")
    lines.append("")
    lines.append(f"  Closest {len(a['top'])} YC companies:")
    for i, m in enumerate(a["top"], 1):
        lines.append(f"  {i}. {m['name']} ({m['batch']}, {m['status']})  distance {m['distance']:.3f}")
        lines.append(f"     {m['one_liner']}")
        lines.append(f"     {m['website'] or '(no website)'}  |  {m['yc_url']}")
    return "\n".join(lines)
