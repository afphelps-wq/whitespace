"""Optional local LLM helpers via Ollama's HTTP API. Every function returns None if Ollama is unavailable."""
import json

import requests

from config import LLM_SEED, LLM_TIMEOUT, OLLAMA_MODEL, OLLAMA_URL

REWRITE_SYSTEM = """You turn a startup idea into a one-sentence product description.
Rules:
- Start with "Software that", "An app that", or "A service that".
- At most 20 words. One sentence: what the product does and who it is for.
- Keep the user's core nouns (the people, objects, and places they named).
- Do not use the words "helps", "streamline", "streamlining", "saving time", or "This AI tool".
- No marketing adjectives (seamless, effortless, innovative, powerful, easy, user-friendly, trusted, etc.).
- No company or brand names.
- If the input already describes a product, keep it close to the original wording.
- Output only the sentence, with no quotes or preamble."""

ADVISE_SYSTEM = """You advise a student on a startup idea using ONLY the companies listed in the message.
Do not mention, invent, or rely on any company that is not in that list.
Do not state or guess whether any company is active, acquired, or shut down; the app shows that separately.
Reply as JSON with exactly these keys:
  "summary": 2-3 sentences on what the listed companies already cover and what they leave out,
  "angles": a list of 2-3 strings. Each is one full sentence that names one listed company
            and says concretely how the idea would differ from it."""


def is_available():
    """True if Ollama answers and has OLLAMA_MODEL pulled. Quick check, no printing."""
    try:
        r = requests.get(OLLAMA_URL.rsplit("/api/", 1)[0] + "/api/tags", timeout=3)
        r.raise_for_status()
        return any(m.get("name") == OLLAMA_MODEL for m in r.json().get("models", []))
    except (requests.RequestException, ValueError):
        return False


def _chat(system, user, json_mode=False):
    """Message content from Ollama, or None (with one printed line) on any failure.
    Temperature 0 and a fixed seed, so repeated runs give the same output."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0, "seed": LLM_SEED},
    }
    if json_mode:
        payload["format"] = "json"
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=LLM_TIMEOUT)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"[LLM unavailable: {type(e).__name__}; continuing without it]")
        return None


def rewrite_to_pitch(user_text):
    """The one-line pitch, or None if Ollama is unavailable or the reply has no usable line.
    A preamble line like "Here is a product description:" is skipped."""
    out = _chat(REWRITE_SYSTEM, user_text)
    if not out:
        return None
    lines = [ln.strip().strip('"').strip() for ln in out.splitlines()]
    lines = [ln for ln in lines if ln and not ln.endswith(":")]
    return lines[0] if lines else None


def advise(user_text, top5):
    """{"summary": str, "angles": [str]} from the given companies only, or None.
    Status is left out of the prompt so the model can't misstate it."""
    companies = "\n".join(f"- {m['name']} ({m['batch']}): {m['one_liner']}" for m in top5)
    user = f"Idea: {user_text}\n\nCompanies (the only ones you may use):\n{companies}"
    out = _chat(ADVISE_SYSTEM, user, json_mode=True)
    if out is None:
        return None
    try:
        data = json.loads(out)
        summary, angles = data["summary"], data["angles"]
    except (ValueError, KeyError, TypeError):
        print("[LLM unavailable: reply was not the expected JSON; continuing without it]")
        return None
    if isinstance(angles, str):
        angles = [angles]
    if not isinstance(angles, list):
        angles = []
    # a model sometimes returns {"company": ..., "angle": ...} objects instead of sentences
    angles = [": ".join(str(v).strip() for v in a.values()) if isinstance(a, dict) else str(a).strip()
              for a in angles]
    angles = [a for a in angles if a]
    if not isinstance(summary, str) or not summary.strip() or not angles:
        print("[LLM unavailable: reply had no summary or angles; continuing without it]")
        return None
    return {"summary": summary.strip(), "angles": angles[:3]}
