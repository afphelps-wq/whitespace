# Spec: Startup Idea Checker (working name TBD)

**Course:** 15-113, vector database homework
**Owner:** Anabella Phelps
**Due:** Monday, Oct 26, 2026
**Expected effort:** ~4.5 hours (per assignment)
**Status:** Design mostly decided. ChromaDB 1.5.9 installed on Python 3.14 (10/22). Milestones 1 (inspect) and 2 (smoke test: persistence and cosine verified) done. Target lookup done (both queries have zero-overlap targets). Milestone 3 test run (50 companies) done: 1.3 s to embed, about 40 s estimated for 1,500. `selected_ids.txt` written (1,500 slugs, force-includes first; committed). **Full ingest done (10/23):** 1,500 companies in 34 s. Status: Active 1,146 · Inactive 196 (13%) · Acquired 155 · Public 3. 110 documents left out a cut-off one-liner, and 14 hiring or "join us" sentences were removed. Langfuse fix applied and verified. Milestone 4 (queries, keyword baseline, calibration) done 10/23. README queries checked under strict matching (A1 → Hera, B1 → Allo). Milestone 5 (`my_pitches`: add, search immediately, persistence, duplicate check) done 10/23. Milestone 6 (scoring) done 10/23: all 10 calibration pitches got the expected verdict. That's circular, since the thresholds were fitted to them, and several pitches sit within 0.02 of a cutoff (PR bot crowded by 0.004). Graveyard warning never fired. Pain-style A1 and B1 come out "Open" on the raw path, as predicted in 7.6. Milestone 6b code done 10/24 (`llm.py`: rewrite at temp 0.1, advice in JSON mode at temp 0.3, settings in config). The fallback is verified: with Ollama off, calls fail in about 0.01 s, search runs on the raw text, and nothing crashes. Ollama 0.40.10 is installed as a brew service, with llama3.2:3b (2.0 GB).

**llm_test.py results (10/24):**
- The rewrite pulls targets much closer: Hera 0.671 → 0.486 (#2), Allo 0.752 → 0.555 (#1).
- Timing: rewrite ~0.6–1.3 s (3.4 s on the first call), advice ~4.6–5 s.
- Problems:
  1. Rewrite filler ("This AI tool helps… streamlining") made the grant-proposal holdout falsely Crowded (20+ "relevant").
  2. B1's rewrite changed the meaning ("neighborhood watch program").
  3. The graveyard warning missed B1's mostly-dead top 5, which all sit just above 0.53.
  4. The advice stated a wrong status fact (it said only Waypoint was active), and its angles are bare titles.

**Fixes [DECIDED 10/25]:**
- **Rewrite prompt:** must start with "Software / An app / A service that…", stay ≤ 20 words, and keep the user's core nouns. Ban "helps", "streamline", "saving time", "This AI tool", and marketing adjectives.
- **Graveyard:** fires if at least 3 of the **top 5** (regardless of distance) are Inactive.
- **Advice:** the model doesn't comment on company status, since statuses are shown separately by the app. Each angle is one full sentence naming which listed company it differs from and how.
- Hallucination by a 3B model can't be fully prevented. Note it as a limitation in the README.

**Milestone 7 (menu) done 10/25.** End-to-end test passed: A1 with rewrite gives "Taken" (Meetingbird / Cron / Hera at #1–3), raw mode shows no verdict, the duplicate check blocks an exact copy, filters work, pitches persist across relaunch, and with Ollama down the rewrite turns off automatically.

Known issues found:
- The rewrite isn't deterministic.
- B1's rewrite drifted to "background-checked caregivers" and got a misleading "Crowded" (elder care).
- Raw "Uber for X" input matches poorly.

**Final code changes [DECIDED]:** temperature 0 with a fixed seed, and an app `--reset-pitches` flag. **Then code freeze.** B1 drift and "Uber for X" are documented as README limitations, not tuned further.

**CODE FROZEN 10/25 ~4 pm.** Temperature 0 with `LLM_SEED = 113`; results are identical across runs.
- A1 with rewrite: TAKEN (Meetingbird 0.399, Cron, Hera, Aerotime, Waypoint).
- B1 with rewrite: SOME NEIGHBORS plus the **graveyard warning** (ReverCare, Alltruists, Brave Care inactive). Allo is not in the top 5 with rewrite on, so the README demo runs raw.
- requirements.txt: chromadb==1.5.9, requests==2.34.2. `.gitignore` verified.
- **The project folder `ideate/` sits inside a git repo rooted at the home folder.** Run `git init` inside `ideate/` before committing.

**Video plan:**
1. A1 with rewrite on → Taken.
2. B1 with rewrite on → graveyard warning.
3. Toggle rewrite off, then A1 raw → Hera #3 with zero shared words (the required query demo).
4. Search past pitches.
5. Relaunch to show persistence.

Legend: **[DECIDED]** fixed · **[DEFAULT]** use unless data says otherwise · **[OPEN]** needs my decision before the step that depends on it

---

## 0. How to use this spec with Claude Code (read first)

The assignment explicitly penalizes building the app in a single prompt and handing the AI the assignment document up front. So:

- **Do not paste this whole spec into the agent and say "build it."** Work through Section 10 one milestone at a time, with one or a few prompts per milestone, and test before moving on.
- Each prompt should be written by me, in my words, scoped to that milestone. It can reference the relevant spec section ("implement Section 6.2").
- **Never give the agent the assignment PDF or text.**
- Log every important prompt **verbatim** in `prompt_log.md` as I go (Section 12). Don't reconstruct it at the end.
- After the agent writes retrieval code, ask it to explain each argument and the result shape, then print real results and check whether the explanation was true.

---

## 1. Concept [DECIDED]

A CLI for **students validating startup ideas**. You type a pitch, anywhere from a one-line idea to a full YC-style pitch. The app searches ~1,500 Y Combinator companies **by meaning**, then tells you:

1. **Crowdedness and failures:** how many existing companies are close, and how many of those are dead
2. **Differentiation advice** (local LLM): a short market summary and specific angles to stand out
3. **Who to look at:** each close company's website and YC profile link

It also **keeps a history of your pitches**, warns you when a new pitch nearly duplicates one you already saved, and lets you search your own past pitches.

## 2. Assignment requirements and how this project meets each one

| Requirement | How it's met |
|---|---|
| Vector DB, and data persists between runs | ChromaDB `PersistentClient(path="./chroma_store")` |
| Real corpus | ~1,500 real YC company descriptions (public YC directory via yc-oss/api) |
| User adds new items at runtime and can search them immediately | Every checked pitch is saved to a `my_pitches` collection. "Search my past pitches" finds it right away. |
| Searches by meaning and does something useful with results | Crowdedness verdict, dead-company warning, contact links, "space looks open" when nothing is close, and LLM differentiation as an extra |
| Vector DB earns its place | Students describe the *problem* in their own words. Company descriptions use industry jargon. See the two required queries in Section 8. |

**Rubric risk to guard against:** the assignment lists "items are short, highly structured, and all look basically alike" as a sign of a bad choice. YC one-liners fit that description, which is why the long description is embedded too (Section 5). Also see the mitigation in Section 8.

## 3. Stack [DECIDED unless marked]

- **Python 3.14** (python.org framework install on macOS), installed globally rather than in a venv.
- **`chromadb` 1.5.9 [DECIDED]**. Pin `chromadb==1.5.9` in `requirements.txt`. All Chroma code must match the 1.x API. Check the current docs, not AI memory.
  - Cosine distance is set with `configuration={"hnsw": {"space": "cosine"}}` (verified in Milestone 2; `collection.configuration` reports `'space': 'cosine'`).
  - Works on Python 3.14. Run everything with **`python3.14`**, because plain `python3` is 3.13 and doesn't have chromadb. The README must say this.
  - On the first run, the embedding model (all-MiniLM-L6-v2, 79 MB) downloads once to `~/.cache/chroma`.
- Embeddings: Chroma's default (`all-MiniLM-L6-v2`), local, with no key. It downloads once on the first add.
  - **Hard limit:** about 256 word pieces. Anything longer is silently dropped, and this applies to both stored documents and queries.
- Distance **[DEFAULT]:** cosine, via `get_or_create_collection(..., metadata={"hnsw:space": "cosine"})`. Lower distance means more similar, and similarity = 1 − distance.
- `requests` for the download. `pandas` only for inspecting the data.
- LLM: **part of the build [DECIDED]**, used for the market summary and differentiation advice.
  - Provider **[DEFAULT: Ollama]**, since I don't have an API key. Install Ollama and pull a small model (for example, a ~3B Llama or Qwen) that fits my laptop. **[OPEN: final model, or switch to a hosted API if I get a key; keys go in `.env`, never committed]**
  - All LLM code lives in `llm.py`. **The app must still run if Ollama isn't installed or running.** It prints "LLM unavailable, skipping advice" and shows everything else, because graders need to run it from clear instructions.
- **Watch for outdated Chroma code from the agent.** `chromadb.Client(Settings(...))` and `collection.persist()` are from old versions. Check `pip show chromadb` against the current docs.

## 4. Data

### 4.1 Source
- `https://yc-oss.github.io/api/companies/all.json` is an unofficial open-source mirror of YC's public directory, with ~5.7k–6.2k companies, updated daily.
- Backup: the Kaggle "Complete YCombinator Dataset From 2005–2024."
- Raw file goes to `data/raw/yc_all.json` (gitignored).

### 4.2 Data facts (Milestone 1 output, 10/22)
- 6,322 records, 29 keys, all present on every record. Fields used: `name`, `slug`, `one_liner`, `long_description`, `batch`, `status`, `industries`, `tags`, `website` (company site), `url` (YC profile).
- `batch` format: "Season YYYY" (Winter/Spring/Summer/Fall). Parse the year from the last token. Drop the one "Unspecified" record (YC's own entry).
- `status` values: Active 4,360 · Inactive 1,100 · Acquired 839 · Public 23. **"Failed" = Inactive.**
- Recent companies are almost all Active because they're young (2025: 13/620 Inactive; 2026: 6/782). An Active 2025–26 match is weak evidence that a space is healthy.
- Missing: 160 one-liners, 426 long descriptions.
- Length (chars): one_liner median 47 / p90 67; long_description median 387 / p90 984.
- Quality issues: 589 one-liners are cut off with "…"; descriptions contain `\r\n` breaks and filler such as hiring pitches and "*Acquired by X in 2018" lines.
- 2015 onward: 5,611 companies; 5,577 with any text; 5,238 with a long_description.
- Per year, 2015 onward: 214, 224, 241, 277, 368, 438, 726, 631, 494, 590, 620, 782 (2015–2026), plus 6 in 2027.

### 4.3 Which companies [DECIDED: 2015 onward]
Target size: **~1,500 [DECIDED]**. Batch years: **2015 onward [DECIDED]**. This range keeps enough dead companies for the failures output.
- Eligible pool **[DECIDED]:** 2015 onward (including 2027) **and a non-empty long_description**, giving 5,238 companies. One-liner-only records are dropped because short, alike items are a named rubric risk.
- Sampling **[DECIDED]:** 1,500 drawn **proportionally by batch year** with a fixed seed (`SEED = 113`). Alternative: equal per year (~125 each), which gives more old and dead companies but less coverage of current ideas. Ingest prints the resulting status breakdown.
- **Force-include list [DECIDED approach]:** a 1,500 sample covers only about 29% of the pool, so the companies my two queries should retrieve will probably be missing. Before sampling, look up target companies in the raw JSON, add their slugs to `FORCE_INCLUDE` in `config.py`, and note this in the README.
- The chosen IDs are saved to `selected_ids.txt` (Section 4.4).

### 4.4 Reproducibility [DECIDED]
The source changes daily, so graders' downloads won't match mine.
- `ingest.py` selects companies by a **fixed batch range plus a saved ID list**.
- First run: apply the filter and write `data/selected_ids.txt`. **This file is committed**, since it's small.
- Later runs and graders: load only the IDs in `selected_ids.txt`, and print a warning listing any that no longer exist upstream.
- The README explains this.

## 5. What one item is [DECIDED]

One company equals one document, with this text:
```
{name}: {one_liner}. {long_description}
```
- **Cleaning before embedding [DECIDED]:**
  - Replace `\r\n` and other whitespace runs with a single space.
  - Drop lines starting with `*` (for example, "*Acquired by…").
  - Drop recruiting-pitch sentences using a **tight** regex only: `\b(we['’]?re hiring|(is|are) hiring|join (us|our team)|check out our open roles|we['’]?re looking for)\b`. A bare `hiring` match (first attempt) removed about 20 legitimate product sentences from HR-tech companies such as HigherMe, Contrario, and TalentDrop, which would have hurt HR-tech pitches. Print every removed sentence and spot-check.
  - Cut-off one-liners (ending in "…", 589 in the source data): **leave them out of the embedded document** when a long description exists, because a fragment like "help each." adds noise. Keep the one-liner with its "…" in metadata for display.
- **Truncation [DECIDED]:** after cleaning, cap the document at ~1,000 chars. The description p90 is 984 chars, so this trims only the tail, and ~1,000 chars is about the model's ~256 word-piece limit.
- Skip companies with no description at all.
- The document must contain the real content. Don't hide the description in metadata, because only the document text is embedded.

## 6. Collections

### 6.1 `yc_companies` (loaded by ingest; read-only at runtime)
- `id`: `slug`, unique
- `document`: from Section 5
- `metadata` (values must be str, int, float, or bool, with **no lists and no None**):
  - `name`, `one_liner`, `batch` (str)
  - `batch_year` (int, parsed from batch, used for filtering)
  - `status` (str, used for filtering)
  - `industries` (str, comma-joined)
  - `website` (str, "" if missing), `yc_url` (str)

### 6.2 `my_pitches` (added at runtime)
- `id`: UUID. Never reuse one, because `add()` silently ignores duplicate ids.
- `document`: the pitch text exactly as typed
- `metadata`: `created_at` (ISO str), `verdict` (str), `top_match` (str)
- Pitches are **never** mixed into YC results [DEFAULT].

## 7. App behavior

### 7.1 Menu [DECIDED: numbered]
```
--- Startup Idea Checker ---
1. Check a new idea
2. Search my past pitches
3. Show all my saved pitches
4. Stats
5. Quit
```

### 7.2 Option 1: Check a new idea
1. Prompt for the pitch. Accept a one-line idea or the full template (Section 7.4). Multi-line input ends on an empty line.
2. Ask about optional filters [DECIDED: status and year only]: "Only active companies? (y/N)" and "Founded/batch year from (blank = all)". These map to a Chroma `where=` filter, for example `{"$and": [{"status": "Active"}, {"batch_year": {"$gte": 2023}}]}`.
3. Query `yc_companies` with `n_results=5` [DECIDED].
4. **Nothing-close check [DECIDED]:** if the best similarity is below `OPEN_THRESHOLD`, print "Nothing close. This space looks open." and show the nearest match for context only.
5. Otherwise, print the top 5: rank, name, batch, status, similarity, one-liner, website, and YC profile URL [DECIDED: contacts = links].
6. **Crowdedness verdict [DEFAULT logic, thresholds calibrated in Milestone 4]:**
   - best similarity ≥ `TAKEN` → "Taken: a near-identical company exists."
   - at least 3 results ≥ `RELEVANT` → "Crowded space."
   - otherwise → "Some neighbors, room to differentiate."
7. **Failures:** "Of N close companies: X active, Y acquired/public, Z inactive." If at least 3 of the top 5 are Inactive (regardless of distance), add: "Graveyard warning: several attempts at this have died. Find out why before building." **[DEFAULT]** If most close matches are from the last 2 batch years, add: "Most competitors are very new, so it's too early to tell if this space works."
8. **Save the pitch with a near-duplicate warning [DECIDED]:** before saving, query `my_pitches`. If the best match is ≥ `DUP_THRESHOLD`, show it (date and text) and ask "Save anyway? (y/N)." Save the pitch with its verdict and top match.
9. **LLM advice [DECIDED]:** if the LLM is available, send the pitch and the top 5 (name, one-liner, status) and ask for (a) a 2–3 sentence market summary and (b) 2–3 specific differentiation angles [DECIDED: both]. Use a timeout, and if it fails, print a note and continue.

### 7.3 Options 2–4
- **2:** semantic search over `my_pitches`, showing the top 5 with date and similarity. This is the "add, then search immediately" demo.
- **3:** list all saved pitches with date and verdict.
- **4:** counts per collection, status breakdown of `yc_companies`, and the data snapshot date.

### 7.4 Pitch template (shown as a hint in option 1)
> We are [company] and we build [x] for [y]. This solves [real problem]. [Relatable example of the problem]. Our unique insight is [non-obvious understanding of the market or technology].

Keep pitches under about 150 words, since anything past the embedding limit is ignored. Print a warning if the input is longer.

### 7.5 Thresholds (in cosine **distance**, lower = closer, matching Chroma output)
**[DEFAULT, set 10/23 from 10 calibration pitches; small sample, so revisit if the demo looks wrong]** These apply to pitch-style text, meaning the LLM-rewritten query.
- `TAKEN_MAX = 0.40`: best ≤ 0.40 → "Taken: a near-identical company exists." (Langfuse 0.30, Brex 0.39, medical billing 0.39)
- `RELEVANT_MAX = 0.53`: results ≤ 0.53 count as real competitors for the crowdedness count and the failure breakdown.
- `CROWDED_MIN_COUNT = 3`: at least 3 relevant → "Crowded space." (The PR-review bot has 3 ≤ 0.53. Church kitchens has only 2, its food-delivery neighbors at 0.505 and 0.511, so it correctly stays out.)
- **Open = zero relevant matches** (best > `RELEVANT_MAX`) → "Nothing close. This space looks open." [DECIDED 10/24: replaces `OPEN_MIN = 0.55`] The old 0.53–0.55 band produced "Some neighbors" with 0 relevant matches (grant-proposal holdout, 0.543), which contradicts itself. All 10 calibration verdicts are unchanged.
- Otherwise (1–2 relevant matches) → "Some neighbors, room to differentiate." (Payroll for contractors 0.45, church kitchens 0.505)
- Near-duplicate pitches **[DEFAULT, set 10/23 from pitch_test.py]**, two tiers:
  - `DUP_MAX = 0.15` → "You've saved almost this exact pitch before. Save anyway? (y/N)" (exact match 0.00, light rewording 0.08)
  - `SIMILAR_MAX = 0.45` → informational only: "Similar to your pitch from {date}: …" (heavy rewording of the same idea 0.415; unrelated 0.73; a different student-app pitch 0.74)
  - Only one data point per tier. Revisit if it fires on different ideas.
- Reset `my_pitches` (`pitch_test.py --reset`) before recording the video, so test pitches don't show up.
- With the rewrite off (raw path, pain-style input), these cutoffs mislabel spaces as "open." Raw-path results should show the list without a verdict, or with a note saying so.

Original placeholders (superseded): 0.35 / 0.45 / 0.70 / 0.85 (cosine similarity). They are guesses. Set the real values in Milestone 4 by looking at the actual distributions, including from nonsense queries.

**Milestone 2 baseline (12 toy docs; cosine distance, lower = closer):**

| Query | Best (correct) | 2nd best |
|---|---|---|
| "emailing back and forth to find a time…" | 0.576 (calendar assistant) | 0.815 |
| "moved to a new city… into climbing" | 0.622 (hobby groups app) | 0.859 |
| "purple elephant tax law banana" (nonsense) | 0.771 | 0.848 |

- Unrelated text sits around 0.8–0.9 distance, real matches around 0.58–0.62, and nonsense at a surprisingly close 0.77.
- Caveat: the toy docs were written by the agent knowing the queries, so they're easier than real data.
- ~~Gap idea~~: **dropped.** On real data, the real queries had *smaller* gaps (0.03–0.05) than nonsense (0.07–0.12), the opposite of the toy data.

**Milestone 4 baseline (1,500 real docs; cosine distance):**

| Query | Best | 5th | Gap |
|---|---|---|---|
| A (pain-style) | 0.643 | 0.678 | 0.034 |
| B (pain-style) | 0.714 | 0.752 | 0.037 |
| AI drafts insurance claims for small clinics | 0.401 | 0.433 | 0.032 |
| restaurants throwing away food | 0.621 | 0.667 | 0.046 |
| landlords screen tenants | 0.555 | 0.703 | 0.147 |
| nonsense ×3 | 0.673–0.735 | 0.744–0.854 | 0.07–0.12 |

- **No single absolute cutoff separates real queries from nonsense:** nonsense scores 0.67–0.74, the same range as Queries A and B.
- Nonsense isn't a realistic input for this app anyway. Calibrate on **realistic pitches** instead: some in crowded spaces, some in open spaces.
- **Pain-style inputs score much farther away than pitch-style inputs** (0.64–0.71 vs. 0.40–0.62). Thresholds tuned on pitches would label Queries A and B "open" even though real competitors exist. **[OPEN]** How to handle: see Section 7.6.
- Preliminary bands from the 3 pitches: close competitor ≤ ~0.45, loosely related ~0.55–0.65, nothing close > ~0.65. Not final.

**Calibration pitch set (drafted by Claude at my request, 10/23; note this in the prompt log):**
- Expected crowded: (1) corporate cards that auto-categorize every startup expense; (2) AI bot that reviews pull requests and leaves comments; (3) automating medical billing and insurance-denial appeals for hospitals; (4) payroll and compliance for companies hiring contractors in other countries; (5) open-source tracing and evals for LLM apps.
- Expected open or niche: (6) renting out trained goats to clear invasive weeds; (7) matching amateur choirs with retirement homes for weekly concerts; (8) renting idle church kitchens to food startups; (9) a smart collar that turns cat sounds into mood alerts; (10) booking professional mourners for funerals.

### 7.6 Pain-style vs. pitch-style input [DECIDED: (b) LLM query rewrite]
- The LLM's two jobs are (1) rewriting the input into a one-line product pitch before search and (2) giving market and differentiation advice after search.
- The app shows the user both the original input and the rewrite.
- **The README's "no shared words" demo uses the raw path (rewrite off),** so any category words the LLM adds don't affect the evidence. Include a toggle (menu setting or flag) for this.
- If Ollama is unavailable, search the raw input and print a note.
- Thresholds are calibrated on **pitch-style** text, since that's what gets searched once the rewrite is on.

Options considered:
Problem found in Milestone 4: users describing a *problem* ("I waste half my week…") land 0.2–0.3 farther from relevant companies than users describing a *product*. Options:
- (a) **Prompt for pitch-style input** (a hint plus the template) and word the verdict carefully: "No close match; nearest is X." Cheapest.
- (b) **LLM query rewrite:** Ollama turns the input into a one-line product pitch before searching, and the app shows both. This improves the verdict and makes good prompt-log material. Caveat: the LLM may add category words like "scheduling," so the README's "no shared words" demo must use the raw path, with rewriting off.
- (c) **Search both** the raw input and the rewrite, and merge the results.

## 8. The two "earns its place" queries [OPEN: MUST WRITE BEFORE CODE]

The assignment requires two queries that share **no important words** with the item they correctly retrieve. Both go in the README, and at least one goes in the video.

- My earlier examples fail this test. The ERP/OCR pitch shares "ERP," "OCR," "accounting," and "manufacturing" with the companies it should find, and "make accounting less manual" shares "accounting."
- To pass, describe the **pain**, not the category. Example from Claude: "I'm sick of chasing coworkers for receipts every month" should find a spend or expense-management company without saying "expense," "card," or "spend."
- Query 1 draft (mine): "I'm sick of spending so much time on trying to schedule meetings with coworkers" → expected: an AI scheduling or calendar-assistant company
  - Concern: "schedule" and "meetings" probably appear in those companies' descriptions, so a keyword search would also find them. Possible pain-only rewrite: "I waste half my week emailing back and forth to find a time that works for everyone."
- Query 2 draft (mine): "I'm sick of trying to find friends and groups with similar interests to mine, where do I look?" → expected: a social-discovery or community app
  - Concern: "friends," "groups," and "interests" are likely words in social-app descriptions. Possible rewrite: "I moved to a new city and don't know anyone who's into climbing."
- **Target lookup results (10/22, check_targets.py):**
  - Query A rewrite vs. Meetingbird (Summer 2017, Acquired): SHARED none. Vs. Hera (Summer 2021, Inactive): SHARED none. Vs. Cron (Winter 2020, Acquired): SHARED [time, works], with a different sense of "works." Candidate force-includes: `meetingbird`, `hera`, `cron`.
  - Query B rewrite: **no fitting target found.** A keyword search ranks Lugg (a moving and delivery service) first because of "moved" and "new." That's useful README evidence of keyword search misreading meaning.
  - **Query B re-aimed at Allo [DECIDED]** (Winter 2019, Inactive; "helps neighboring families meet and help each other"). Wording: "We just moved in and have no idea who on our street could watch the kids in a pinch." **Overlap check vs. Allo's long_description: SHARED none** (street ↔ neighbors, kids ↔ children, watch the kids ↔ asking for a favor).
  - Allo's space: Poppy (Winter 2016, Inactive; childcare for parents) is the only close competitor. Milo (Winter 2020, Inactive; AI copilot for parents) is loosely related. The rest of the top 10 is elder care, funerals, and pediatric health, which is noise.
- **FORCE_INCLUDE [DECIDED]:** `meetingbird`, `hera`, `cron`, `allo`, `poppy`, `milo`. These count toward the 1,500.
- Note: SHARED was computed against long_description only. The embedded document also includes the name and one-liner, so re-run the overlap check against the **full embedded document** in Milestone 4 before putting it in the README.
- **Milestone 4 results (10/23, explore_queries.py; cosine distance):**
  - Query A: Aerotime 0.643, Mailwarm 0.667, **Hera 0.671 (#3, SHARED none)**, Mailmodo 0.676, Cron 0.678 (#5). Meetingbird is #17 (0.722; its description is short and vague). "Emailing" pulls in email-marketing tools (Mailwarm, Mailmodo).
  - Query B: Here 0.714, Alltruists, AvairSense, MagicBus, **Allo 0.752 (#5, SHARED none)**. Poppy is #12. Allo's distance sits in the nonsense range, so this is a weak demo.
  - Keyword baseline: Query A matches 676 of 1,500 docs. Hera and Meetingbird are not found; Cron is at keyword rank 172 with 154 ties. Query B matches 112 docs; Allo and Poppy are not found.
  - **Current README pairs:** A → Hera, B → Allo. Pending a wording iteration to strengthen both.
- **Variant test (10/23):**
  - A1 (original) → Hera #3, SHARED none. A2 ("…figure out what times to meet…") ranks higher but shares "meet." A3 ("…scheduling meetings") ranks Meetingbird #1 at 0.50 but shares "scheduling, meetings." That's a useful README contrast: shared words make the distance smaller, but the target is still found without them.
  - B1 → Allo #5. B2 shares "need, find." **B3 ("How do I know who to contact for child care when I just moved to a new neighborhood?") → Allo #4, SHARED none, with Poppy #3 right above it.** The top 5 is more on-topic than B1's.
- **Strict re-check (10/23, prefix stem matching, min 4 letters):** B3 fails (child~children, neighborhood~neighbors) and B3b fails (child~children; Allo drops to #7). A1 → Hera and B1 → Allo still pass.
- **README pairs [DEFAULT, lock unless B3c beats B1]:**
  - **Query A = A1** "I waste half my week emailing back and forth to find a time that works for everyone" → **Hera (#3, 0.671)**. SHARED none (strict). Keyword search: Hera not found among 676 matching docs.
  - **Query B = B1** "We just moved in and have no idea who on our street could watch the kids in a pinch" → **Allo (#5, 0.752)**. SHARED none (strict). Keyword search: Allo not found among 112 matching docs.
  - The video demos **A1** (the stronger result). B1 is weaker: the four results above Allo are off-topic, which the README should acknowledge honestly.
  - Words to avoid in any B rewrite (all in Allo's doc): child, kid, care, neighbor, famil, parent, communit, ask, favor, help.
- Both: confirm in Milestone 4 that (1) a matching company exists in the selected subset, and (2) a plain keyword search over the documents misses it.
- Verify both against the real data in Milestone 4. If they fail, adjust the stored text or the queries, not just the wording of the README.

## 9. Repo layout

```
<repo-name TBD>/          # standalone repo [DECIDED]
├── README.md
├── prompt_log.md
├── spec.md
├── requirements.txt
├── .gitignore            # data/raw/, chroma_store/, .venv/, __pycache__/, .env
├── data/
│   └── selected_ids.txt  # committed (small)
├── config.py             # paths, constants, thresholds, batch range
├── inspect_data.py       # Milestone 1
├── ingest.py             # Milestone 3
├── db.py                 # client, collections, add/search helpers
├── scoring.py            # verdict, failure breakdown
├── llm.py                # extra; app works without it
└── app.py                # menu loop
```

## 10. Milestones (match the assignment's steps; ~4.5 hrs total)

| # | Milestone | Assignment step | Time | Done when |
|---|---|---|---|---|
| 1 | Inspect the data: download it, then print row count, keys, empty-description %, length percentiles, status counts by year, 3 examples | Step 1 | 20 min | I can decide Sections 4.3 and 5 and write my two queries |
| 2 | Install Chroma, then create a persistent client and collection, add 10–15 hand-typed companies, restart, confirm the count persists | Steps 2–3 | 35 min | Count survives a restart |
| 3 | `ingest.py`: filter, write `selected_ids.txt`, batch-add (about 200 per call). **Time 50 items first, then extrapolate** | Step 4 | 35 min | ~1,500 loaded, time recorded |
| 4 | Raw queries: print the full result object (lists of lists), try my two queries plus nonsense queries, record distances, set thresholds | Step 5 | 25 min | Thresholds in `config.py`, both queries verified |
| 5 | `my_pitches`: save, near-duplicate warning, search past pitches | Step 6 | 20 min | Add, then search immediately, works |
| 6 | `scoring.py`: verdict, failures, nothing-close, contact links | Step 7 | 40 min | Output is more than a printed list |
| 6b | `llm.py`: install Ollama, pull a model, build the prompt from the pitch plus top 5, add a timeout and fallback; test that it fails gracefully with Ollama off | Step 7 | 60–90 min | Advice prints; app still works with Ollama off |
| 7 | `app.py` numbered menu and filters; full flow, then quit and relaunch | Step 8 | 15 min | End-to-end test passes |
| 8 | Re-run both queries in the finished app and capture the output | Step 9 | 15 min | Output pasted into README draft |
| 9 | README and prompt log | Step 10 | 30 min | Section 11 checklist complete |
| 10 | Video, push, portfolio, Google form | Step 11 | 35 min | Link tested in incognito |
**Total with the LLM: ~5.5–6 hrs** (assignment baseline 4.5 + LLM 1–1.5).

**Schedule [OPEN: hours available?]:** Thu night: Milestone 1, start the Chroma install. Fri: 2–4, and start the Ollama model download. Sat: 5–7. Sun: 8–10. Mon: buffer.

## 11. README checklist (`README.md`, repo root)

The first four items must be **written by me, in my own words.**
- [ ] What the app does and why I chose it (1–2 sentences)
- [ ] What's stored: source, what one item is, chunking choice, ~count, metadata fields
- [ ] How a user adds items and how a user searches
- [ ] My two queries, what they retrieve, and one sentence each on why keyword search would miss
- [ ] How to get and load the data (download, `selected_ids.txt`, run `ingest.py`)
- [ ] Vector DB and embedding model, and what downloads on the first run
- [ ] Install and run commands
- [ ] Short summary of how I used AI, plus citations (yc-oss/api, YC directory, Chroma docs)
- [ ] Any AI-generated docs go at the bottom under a clearly labeled "AI-generated" heading
- [ ] I've read the whole README and it matches the actual code

## 12. Prompt log (`prompt_log.md`, same folder as README, separate file)

- [ ] Tools and models, and what each was used for: **Claude (chat) for design and brainstorming this spec; Claude Code with Opus in VS Code for implementation.** Add a sentence on why.
- [ ] The development process from start to finish, organized by milestone
- [ ] Important, non-trivial prompts **verbatim**, including key prompts from the design chat
- [ ] At least one place the AI got something wrong and how I caught it (outdated Chroma API is a likely candidate)
- [ ] Shows ~4.5 hours of real work

## 13. Other deliverables
- [ ] Video (1–2 min): add a pitch, check an idea, show the verdict and failures, run at least one of the two queries. Upload, then test the link in incognito. **[OPEN: tool and host]**
- [ ] Portfolio entry: repo link, short description, screenshot or embedded video
- [ ] Google form: repo link, video link, basic info

## 14. Open decisions (in the order they block work)
- [ ] My two no-shared-words queries (Section 8). **Blocks Milestone 4; write a draft tonight**
- [ ] Hours available before Monday (plan needs ~5.5–6)
- [ ] Ollama model choice (depends on my laptop's RAM), or a hosted API
- [ ] Repo name and app name
- [ ] Final thresholds (Milestone 4)
- [ ] Video tool and host
- [ ] Optional: post the idea on Ed to confirm it passes the "earns its place" test

## 15. Next steps (tonight)
1. Start `pip install chromadb` in a new venv now, since it's slow.
2. Create the repo and `.gitignore`. Start `prompt_log.md` and paste in your key prompts from this design chat.
3. First Claude Code prompt, in your own words: Milestone 1 only.
4. Draft your two queries.
