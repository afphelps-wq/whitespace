# Prompt Log

Whitespace was built milestone by milestone from [spec.md](spec.md) (Section 10), from Thursday
10/22 to Monday 10/26/2026. \

## Tools and models used

| Tool | Model | Used for |
|---|---|---|
| Claude (claude.ai chat) | Claude | Brainstorming the idea and writing [spec.md](spec.md): data choices, verdict logic, milestones, test queries. The 10 calibration pitches in Milestone 4 were drafted by Claude at my request. |
| Claude Code in VS Code | Claude Opus 5.5 (`claude-opus-5-5`) | All implementation, testing, and git/GitHub. Four sessions, one prompt per milestone step. Every commit has a `Co-Authored-By` trailer naming it. |
| A separate Claude agent | Claude | Reviewing Claude Code's output after each milestone before I moved on. |
| Inside the app | `all-MiniLM-L6-v2` (Chroma's default embedder); `llama3.2:3b` via Ollama | Embedding the 1,500 YC descriptions and pitches; the optional pitch rewrite and market advice. |


Sources: [yc-oss/api](https://yc-oss.github.io/api/companies/all.json), the YC company directory,
Chroma docs, Ollama.

## Timeline

| When (EDT) | Milestone (spec Section 10) | Prompts |
|---|---|---|
| Before Thu 10/22 | Design: idea, spec, open decisions (Claude chat) | [D](#design-claude-chat) |
| Thu 10/22, 9:18–9:37 pm | 1 Inspect data · 2 Chroma smoke test · target lookup | [1](#1-milestone-1-inspect-the-data)–[5](#5-allo-and-its-competitors) |
| Fri 10/23, 1:37–3:09 pm | 3 Ingest · 4 Raw queries and calibration · 5 Saved pitches · 6 Scoring | [6](#6-milestone-3-ingest-timed-on-50)–[13](#13-milestone-6-verdicts) |
| Fri 10/23, 4:37 pm – Sat 10/24, 1:33 pm | 6b Local LLM | [14](#14-milestone-6b-local-llm)–[15](#15-install-ollama-simplify-open) |
| Sun 10/25, 3:37–4:10 pm | 6b fixes · 7 Menu app · code freeze | [16](#16-stricter-rewrite-graveyard-and-advice-rules)–[19](#19-cleanup-and-git-init) |
| Sun 10/25, 4:14–4:20 pm | Publish to GitHub | [20](#20-create-the-repo-and-push)–[22](#22-check-the-state) |
| Sun 10/25, 7:37 pm – Mon 10/26, 6:57 pm | Full test pass · bug fixes · README push · this log | [23](#23-full-test-pass)–[27](#27-prompt-log-requirements) |



## Milestones 1–2 and target lookup (Thu 10/22)

### 1. Milestone 1: inspect the data
*9:18 pm. First sent at 9:18:03, interrupted, and resent in a fresh session 30 seconds later.*

```
I'm building a CLI startup-idea checker on top of ChromaDB, using Y Combinator company descriptions as the corpus. Before writing any database code, I want to understand the data.

Only do this step:
1. Create a .gitignore that excludes data/raw/, chroma_store/, .venv/, __pycache__/, and .env.
2. Write inspect_data.py that downloads https://yc-oss.github.io/api/companies/all.json to data/raw/yc_all.json (skip the download if the file already exists), then prints:
   - total row count and the full list of keys on a record
   - how many records have an empty or missing one_liner, and the same for long_description
   - median and 90th-percentile character length of one_liner and long_description
   - how the batch field is formatted, and counts of companies per batch year
   - status value counts overall, and status counts by batch year for 2015 onward
   - total number of companies from 2015 onward that have a non-empty description
   - 3 full example records
3. Run it and show me the output.

Don't build ingest, Chroma, or the app yet. After it runs, briefly explain any field names or formats that turned out different from what I listed here.
```

*Result: 6,322 records, 29 keys. "Failed" companies are `status: Inactive`. Recorded in spec 4.2.*

### 2. Milestone 2: ChromaDB smoke test
*9:27 pm. I pinned the 1.x API up front so the agent wouldn't use older Chroma calls.*

```
Next step: a smoke test for ChromaDB before touching the real data. I'm on chromadb 1.5.9, Python 3.14 — use the current 1.x API only (no Client(Settings(...)), no .persist()), and check the current docs for how to set cosine distance on a collection in this version.

Write smoke_test.py that:
1. Creates a PersistentClient at ./chroma_store and a collection "smoke" with cosine distance.
2. Adds 12 short, made-up company descriptions in a single add() call, each with metadata {"status": ..., "batch_year": ...}. Include one calendar/scheduling assistant and one app for meeting new people with shared hobbies, but don't use the words "schedule," "meeting," "friends," or "interests" in their descriptions.
3. Prints collection.count().
4. Runs two queries and prints the full raw result object:
   - "I waste half my week emailing back and forth to find a time that works for everyone"
   - "I moved to a new city and don't know anyone who's into climbing"
5. Runs one nonsense query ("purple elephant tax law banana") and prints its distances too.
6. Only adds items if the collection is empty, so I can rerun it.

Run it twice and show me both outputs, so we can confirm the count persists and the embedding model works on Python 3.14. Then explain the shape of the query result and what the distance numbers mean.
```

*Result: count persisted across runs; `collection.configuration` reports `'space': 'cosine'`.*

### 3. Find real target companies for my two queries
*9:30 pm*

```
Before writing ingest, I need to find which real YC companies my two test queries should retrieve, so I can force-include them in my 1,500-company sample.

Write find_targets.py that loads data/raw/yc_all.json, keeps only 2015-onward companies with a non-empty long_description, and prints up to 15 candidates for each topic:
- Topic A: tools that find meeting times / manage calendars (search one_liner + long_description for words like calendar, scheduling, availability, booking)
- Topic B: apps for meeting new people or finding communities around hobbies (words like community, social, hobby, meetup, local, connect)

For each candidate print: slug, name, batch, status, one_liner. Don't change anything else — I'll pick the targets myself.
```

### 4. Targeted search and word-overlap check
*9:33 pm*

```
Two things, both read-only. Don't modify find_targets.py or inspect_data.py; put this in check_targets.py and reuse the same loading/filtering (2015+, non-empty long_description).

1. Topic B, targeted search. Search one_liner + long_description for these phrases only:
   "new city", "move", "moved", "relocat", "meet people", "meet new", "neighbor", "activity partner", "sports", "outdoor", "climbing", "hobby", "hobbies", "lonely", "loneliness".
   Use prefix matching ("relocat" should hit relocate/relocation), case-insensitive. Rank by number of distinct phrases matched, one_liner hits count double. Print the top 15: slug, name, batch, status, one_liner, matched phrases.

2. Word-overlap check. For each of these slugs: meetingbird, cron, hera, plus the top 3 results from step 1:
   - print the full cleaned long_description (collapse \r\n and repeated whitespace)
   - list every content word it shares with the matching query below, after lowercasing, removing punctuation (treat "back-and-forth" as "back", "and", "forth"), dropping common English stopwords, and reducing simple word forms (email/emails/emailing count as one word; moved/move count as one)
   Query A (for meetingbird, cron, hera): "I waste half my week emailing back and forth to find a time that works for everyone"
   Query B (for the step-1 results): "I moved to a new city and don't know anyone who's into climbing"

Print the overlap as "SHARED: [words]" or "SHARED: none". Don't pick targets for me — just show the results.
```

*Allo (neighboring families helping each other) turned up in step 1 on "neighbor", and I rebuilt
Query B around it in the next prompt.*

### 5. Allo and its competitors
*9:37 pm. Sent again verbatim Fri 1:37 pm; Claude said step 3 already existed and didn't rerun it.*

```
Extend check_targets.py (don't touch the other scripts) with a step 3, using the same overlap logic as step 2:

3a. For slug "allo": print the full cleaned long_description and the SHARED words against:
    Query B: "We just moved in and have no idea who on our street could watch the kids in a pinch"

3b. Search the same pool for other companies in Allo's space so I can force-include a few real competitors. Prefix-match, case-insensitive, on one_liner + long_description: "neighbor", "neighbour", "babysit", "childcare", "nanny", "parents", "families", "local community", "nextdoor". Rank like step 1. Print the top 10: slug, name, batch, status, one_liner, matched, and the SHARED words against Query B for each.

Only run step 3 this time.
```

*Result: Allo SHARED: none. I picked meetingbird, hera, cron, allo, poppy, milo as force-includes.*

## Milestones 3–6 (Fri 10/23)

### 6. Milestone 3: ingest, timed on 50
*1:42 pm*

```
Now the real ingest. Use the 1.x API and configuration={"hnsw": {"space": "cosine"}} as in smoke_test.py. Don't reuse the "smoke" collection.

1. config.py: CHROMA_PATH="./chroma_store", COLLECTION="yc_companies", RAW_PATH, SELECTED_IDS_PATH="data/selected_ids.txt", MIN_YEAR=2015, TARGET_N=1500, SEED=113, MAX_DOC_CHARS=1000, BATCH_SIZE=200, FORCE_INCLUDE=["meetingbird","hera","cron","allo","poppy","milo"].

2. ingest.py:
   - Pool: batch year >= 2015 (drop "Unspecified"), non-empty long_description.
   - Clean: collapse \r\n/whitespace; drop lines starting with "*"; drop sentences about hiring (simple regex: hiring, join us, open roles, we're looking for) and print how many were removed; strip trailing "…" from one_liner.
   - Document = "{name}: {one_liner}. {long_description}", truncated to MAX_DOC_CHARS.
   - Selection: if data/selected_ids.txt exists, use exactly those slugs and warn about any missing upstream. Otherwise include FORCE_INCLUDE, then fill to TARGET_N with a random sample proportional to each batch year's share of the pool (fixed SEED), and write the slugs to selected_ids.txt.
   - Metadata per company: name, one_liner, batch, batch_year (int), status, industries (comma-joined str), website ("" if missing), yc_url. No lists, no None.
   - id = slug. Add in batches of BATCH_SIZE, printing progress.
   - Skip if the collection already has items unless --rebuild is passed.
   - Add a --limit N flag.

3. Run it with --limit 50 first, time it, and estimate the full run. Stop there and show me the timing, the estimate, the hiring-sentence count, and 2 example documents exactly as embedded. Don't run the full 1,500 yet.
```

*Result: 50 companies in 1.3 s, about 40 s estimated for 1,500. The simple hiring regex was too broad.*

### 7. Tighter hiring regex, cut-off one-liners, full run
*1:46 pm*

```
Two fixes to ingest.py, then the full run:
1. Replace the hiring regex with:
   r"\b(we['’]?re hiring|(is|are) hiring|join (us|our team)|check out our open roles|we['’]?re looking for)\b"
   Keep printing every removed sentence.
2. If a one_liner ends in "…" (before stripping) and long_description is non-empty, leave the one_liner out of the embedded document — document becomes "{name}: {long_description}". Keep the original one_liner (with "…") in metadata.

Keep the existing data/selected_ids.txt. Run python3.14 ingest.py --rebuild for all 1,500.

Show me: total time, final count, every removed hiring sentence with its slug, how many documents dropped a cut-off one_liner, the status breakdown (Active/Inactive/Acquired/Public) of the 1,500, and the allo document exactly as embedded.
```

*Result: 1,500 in 34 s; Active 1,146 · Inactive 196 · Acquired 155 · Public 3. The printed list
showed one removal had wiped out most of Langfuse's description (see
[where the AI got it wrong](#where-the-ai-got-it-wrong-and-how-i-caught-it)).*

### 8. Langfuse fix
*1:56 pm*

```
Yes to the Langfuse fix: in clean_description, also treat original line breaks and " - " list markers as sentence boundaries. Rebuild with --rebuild, then show me the langfuse document as embedded and the new list of removed sentences.
```

### 9. Milestone 4: query the real collection
*2:01 pm*

```
Milestone 4: query the real collection and look at raw results. Don't build the app yet. Write explore_queries.py:

1. Print the full raw result object (n_results=5) for Query A: "I waste half my week emailing back and forth to find a time that works for everyone"
2. For each query below, print rank, slug, name, status, batch, and distance:
   - Query A (target: meetingbird; also want hera, cron)
   - Query B: "We just moved in and have no idea who on our street could watch the kids in a pinch" (target: allo; also want poppy)
   - 3 realistic pitches: "AI that drafts insurance claims for small clinics", "help restaurants stop throwing away food at the end of the night", "make it easy for landlords to screen tenants"
   - 3 nonsense queries: "purple elephant tax law banana", "asdf qwerty zxcv", "the weather was nice yesterday"
3. For Queries A and B: report the rank of each target, and re-run the word-overlap check against the target's full embedded document (not just long_description).
4. Keyword baseline: for Queries A and B, do a plain case-insensitive search over all 1,500 documents for each query content word (same stopword list and word-form merging as check_targets.py). Report which companies match any word and whether the targets appear.
5. Summary table: for each query, best distance, 5th distance, and gap (5th minus best).

Show me all output.
```

*Result: complaint-style queries ("I waste half my week…") land 0.2–0.3 farther from the right
companies than product-style pitches. This is what led to the LLM rewrite in 6b.*

### 10. Query variants and calibration pitches
*2:24 pm. The 10 calibration pitches were drafted by Claude (chat) at my request.*

```
Extend explore_queries.py (don't touch ingest). For every query print: top 5 (slug, name, status, distance), and for queries with targets also target rank, target distance, and SHARED words vs. the target's full document. Flag any variant where SHARED isn't empty.

Query A variants (targets: hera, meetingbird):
- I waste half my week emailing back and forth to find a time that works for everyone
- I hate trying to figure out what times to meet with people, everyone's so busy 
- I hate wasting time scheduling meetings

Query B variants (targets: allo, poppy):
- We just moved in and have no idea who on our street could watch the kids in a pinch
- I need to be able to find someone to watch my kids quickly!
- How do I know who to contact for child care when I just moved to a new neighborhood? 

Calibration pitches (no targets):
Expected crowded:
Corporate cards for startups that automatically categorize every expense
An AI bot that reviews pull requests and leaves comments like a senior engineer
Software that automates medical billing and appeals denied insurance claims for hospitals
Payroll and compliance for companies hiring contractors in other countries
Open-source tracing and evaluation tools for LLM applications
Expected open or niche:
A subscription service that rents out trained goats to clear invasive weeds
Matching amateur choirs with retirement homes for weekly concerts
A marketplace for renting idle church kitchens to food startups
A smart collar that turns cat sounds into mood alerts for owners
Booking professional mourners for funerals

End with one table: query, group (A / B / crowded / niche), best distance, 5th distance.
```

### 11. Lock the README queries
*2:34 pm. "[my own rewrite]" was sent as a literal placeholder, so Claude skipped B3c.*

```
Quick check before I lock my README queries. In explore_queries.py add section 7:

1. Run these B variants against targets allo and poppy (rank, distance, SHARED vs. full doc), using prefix matching for SHARED this time (so "neighborhood" counts as sharing "neighbor" with "neighbors"):
   - B3: "How do I know who to contact for child care when I just moved to a new neighborhood?"
   - B3b: "How do I know who to contact for child care when I just moved somewhere new?"
   - B3c: [my own rewrite]
2. Re-run A1 with the same prefix-based SHARED check against hera.
3. Keyword baseline (same as section 4) for whichever B variant has allo in the top 5 with SHARED none: report total docs matched and whether allo appears.
```

*Result: under prefix matching, B3 and B3b both share words with Allo ("child" ~ "children"). B1
still had zero shared words and the keyword baseline missed Allo, so I locked A1 → Hera and B1 → Allo.*

### 12. Milestone 5: saved pitches
*2:45 pm*

```
Milestone 5: user-added pitches. Don't build the menu yet.

1. db.py: get_client(), get_companies() (existing yc_companies), get_pitches() — a new collection "my_pitches", cosine, same configuration form as ingest.
   - add_pitch(text, verdict="", top_match="") → id = uuid4, metadata {created_at: ISO string, verdict, top_match}. Use add(), not upsert().
   - find_similar_pitches(text, n=5) → list of (id, text, created_at, distance).
   - check_duplicate(text) → the closest saved pitch and its distance if distance <= DUP_MAX (put DUP_MAX = 0.15 in config.py), else None.
2. pitch_test.py that, starting from an empty my_pitches:
   - adds 3 different pitches
   - searches for one of them immediately with different wording, and shows it comes back first
   - prints check_duplicate distances for: the exact same text, a light rewording, a heavy rewording of the same idea, and an unrelated pitch
   - runs twice, so I can confirm the pitches persist
   - has a --reset flag that deletes and recreates my_pitches
Show me the output of both runs.
```

### 13. Milestone 6: verdicts
*3:09 pm*

```
Milestone 6: turn search results into a verdict. No LLM and no menu yet.

scoring.py with one main function, analyze(results) → a dict, using thresholds from config.py (all cosine distance):
- TAKEN_MAX=0.40, RELEVANT_MAX=0.53, CROWDED_MIN_COUNT=3, OPEN_MIN=0.55
- verdict: "Taken" if best <= TAKEN_MAX; else "Crowded" if count(dist <= RELEVANT_MAX) >= CROWDED_MIN_COUNT; else "Open" if best > OPEN_MIN; else "Some neighbors"
- status breakdown of the relevant matches (Active / Acquired+Public / Inactive)
- graveyard warning if Inactive is the largest group among relevant matches (and there are at least 2)
- recency note if most relevant matches have batch_year >= current year - 1
- for each of the top 5: name, batch, status, distance, one_liner, website, yc_url

Also a format_report(analysis) → a readable string for the CLI.

Write scoring_test.py that runs the 10 calibration pitches (from explore_queries.py) through search + analyze and prints each report. I expect: corporate cards, LLM tracing, medical billing → Taken; PR bot → Crowded; payroll, church kitchens → Some neighbors; goats, choirs, cat collar, mourners → Open. Tell me any that come out differently and why.
```

*Result: all 10 matched. That is circular, since I fit the thresholds to those 10 pitches, so 6b adds 5 holdout pitches.*

## Milestone 6b: local LLM (Fri 10/23 – Sat 10/24)

### 14. Milestone 6b: local LLM
*Fri 4:37 pm*

```
Milestone 6b: llm.py using a local Ollama model (llama3.2:3b). Call Ollama's local HTTP API (localhost:11434) with requests — no new dependency. Timeout 60s. If Ollama isn't running or errors, every function returns None and prints one line saying the LLM is unavailable; nothing crashes.

1. rewrite_to_pitch(user_text) → one sentence describing the product: what it does and for whom. No company names, no marketing fluff, low temperature. If the input is already a pitch, keep it close to the original.
2. advise(user_text, top5) → (a) 2–3 sentence market summary and (b) 2–3 concrete differentiation angles. Use ONLY the 5 companies given (name, one_liner, status, batch); tell the model not to invent other companies.

Then llm_test.py:
- A1 and B1 (from explore_queries.py) with rewrite ON: print the rewrite, run search + analyze on it, print the report and whether hera / allo are in the top 5, and whether the graveyard warning fired.
- 5 holdout pitches (thresholds were NOT fit on these), rewrite ON, print rewrite + verdict:
  - "Uber for dog walking"
  - "Software that helps small farms sell directly to restaurants"
  - "An app that reminds people to call their grandparents"
  - "AI that writes first drafts of grant proposals for nonprofits"
  - "Rent-a-telescope service for backyard astronomers"
- Run once with Ollama stopped to show the fallback works.
Report timing per LLM call.
```

*Result: fallback verified with Ollama off. Claude asked before installing Ollama.*

### 15. Install Ollama, simplify "Open"
*Sat 1:33 pm*

```
Yes, install it: brew install ollama, start it as a background service (brew services start ollama), and ollama pull llama3.2:3b.

Also update scoring.py: remove OPEN_MIN; verdict is "Open" when there are zero relevant matches (best > RELEVANT_MAX). Re-run scoring_test.py to confirm the 10 calibration verdicts don't change.

Then run llm_test.py with Ollama up and report:
- each rewrite, next to the original
- verdict, best match, relevant count, target in top 5 (A1/B1), graveyard fired?
- the advice output for A1
- seconds per rewrite call and per advise call
```

*Result: the rewrite pulled targets much closer (Hera 0.671 → 0.486, Allo 0.752 → 0.555). It also
showed three LLM problems (see [where the AI got it wrong](#where-the-ai-got-it-wrong-and-how-i-caught-it)).*

## Milestone 7 and code freeze (Sun 10/25)

### 16. Stricter rewrite, graveyard, and advice rules
*3:37 pm*

```
Yes, do the stricter rewrite prompt: start with "Software/An app/A service that…", max ~20 words, keep the user's core nouns, ban "helps", "streamline", "saving time", "This AI tool" and marketing adjectives.

Two more changes:
- Graveyard warning: fire if >= 3 of the top 5 results are Inactive, regardless of distance.
- advise(): tell the model not to state or infer any company's status (the app shows status separately). Each angle must be one full sentence naming which listed company it differs from and how.

Rerun llm_test.py once and show me the same table plus A1's advice. Don't tune further after this run.
```

### 17. Milestone 7: menu app
*3:52 pm*

```
Milestone 7: app.py, numbered menu loop.
1. Check a new idea — multi-line input (ends on empty line), shows the pitch template as a hint, warns if > 150 words. Optional filters: active only (y/N), batch year from (blank = all). If rewrite is ON: show original + rewrite, search the rewrite, show full report + advice. If rewrite is OFF: search the raw text, show top 5 with distances but NO verdict, plus a note that verdicts are calibrated for pitch-style text. Then the duplicate check (DUP_MAX blocks with "Save anyway? y/N", SIMILAR_MAX just informs) and save to my_pitches with verdict + top match.
2. Search my past pitches
3. Show all saved pitches
4. Toggle rewrite ON/OFF (default ON; auto-OFF with a note if Ollama is unreachable at startup)
5. Stats (counts, status breakdown, data snapshot info)
6. Quit
Then test end to end: check A1 (rewrite on), check B1, toggle off and check A1 raw, search past pitches, quit, relaunch, confirm pitches persist. Show me the transcript.
```

*Result: end-to-end passed. The rewrite was still non-deterministic between runs.*

### 18. Final changes, then freeze
*3:57 pm*

```
Last code changes, then I'm freezing the code:
1. llm.py: temperature 0 and a fixed seed for both calls.
2. app.py: --reset-pitches flag that empties my_pitches (no test pitches added) before starting the menu.
3. Run A1 and B1 through option 1 with rewrite ON, twice each, and confirm the rewrites are identical across runs. Show me the final rewrite + verdict + top 5 for each.
4. requirements.txt with exact versions (chromadb==1.5.9, requests, anything else imported). Confirm .gitignore covers data/raw/, chroma_store/, .venv/, __pycache__/, .env, and that data/selected_ids.txt is NOT ignored.
5. Delete or move into a scratch/ folder anything not needed to run the app (smoke_test.py etc. can stay if useful — list what you'd keep).
```

*Result: rewrites identical across runs. Claude pointed out that the project folder was inside a git repo rooted at my home folder.*

### 19. Cleanup and git init
*4:10 pm*

```
1. Yes, delete the "smoke" collection from chroma_store.
2. Confirm whether ingest.py downloads data/raw/yc_all.json when it's missing. If it doesn't, add that (reuse the download from inspect_data.py) and test by temporarily renaming the file.
3. Inside ideate/, run git init, then git status, and show me the list of files that would be committed. Don't commit or push yet.
```

## Publish (Sun 10/25)

### 20. Create the repo and push
*First sent at 4:14 pm from the old session. I had just renamed the project folder from `ideate/`
to `Whitespace/`, so that session couldn't run commands. I told it so ("the folder is now called
Whitespace") and resent this prompt from a new session at 4:17 pm.*

```
Create the GitHub repo and push the code. Stop and ask me if any step fails — don't work around it.

1. Check that the GitHub CLI is installed and authenticated (gh auth status). If it isn't, stop and tell me what to run.
2. Confirm app.py's menu header says "--- Whitespace ---".
3. Leave README_draft.md out of this commit (I'm still writing it; it'll be committed later as README.md). Everything else from the dry-run list goes in.
4. Before committing, scan the files being committed for anything that looks like a secret, API key, token, or a personal file path containing my username, and show me what you find.
5. Commit with the message: "Whitespace: startup idea checker on ChromaDB (code freeze)".
6. Create a PUBLIC repo named "whitespace" under my account (afphelps-wq) with the description "Check whether your startup idea is taken, crowded, or open — semantic search over 1,500 YC companies (ChromaDB + optional local LLM)". Set it as origin and push the main branch.
7. Show me the repo URL and the output of git log --oneline and git status.
```

*Claude stopped at step 2: the header still said `--- Startup Idea Checker ---`.*

### 21. Fix the header and continue
*4:17 pm*

```
change line 16 to --- Whitespace --- and carry on with steps 3–7.
```

*The secrets scan found nothing. Claude committed `6a6bc32` and created the repo, but the push failed
(`Permission denied (publickey)`), and Claude stopped as instructed instead of switching to HTTPS. I pushed from my own terminal.*

### 22. Check the state
*4:20 pm*

```
check the state
```

## Test pass, fixes, and log (Sun 10/25 – Mon 10/26)

### 23. Full test pass
*Sun 7:37 pm. This paste is cut off in the saved transcript after the first lines; the rest is lost.*

```
Run a full test pass on Whitespace and write up the results. The code is frozen: do NOT modify app.py, config.py, db.py, scoring.py, llm.py, or ingest.py. If a test reveals a bug, record it in the report — don't fix it.

Setup
- Create tests/ with: run_tests.py (drives app.py by piping stdin, plus direct calls to db/scoring/llm where piping isn't practical), transcripts/ (one
```

*Result: 124 checks, 115 pass, 2 fail, 7 warn. Full report in [tests/REPORT.md](tests/REPORT.md).*

### 24. Unfreeze and fix
*Mon 6:17 pm*

```
fix the bugs found, unfreeze the code
```

*Result: 126 checks, 122 pass, 0 fail, 4 warn. A1, B1, and all 10 calibration verdicts unchanged.*

### 25. Push README and fixes
*Mon 6:36 pm*

```
push the new updated readme to github and code changes as well that fixed the bug
```


## Where the AI got it wrong and how I caught it

1. **The hiring filter deleted a real description (Milestone 3).** Langfuse's description is a
   bulleted list with no sentence breaks, so the whole thing counted as one "sentence" containing
   "We are hiring" and was removed. I caught it because prompt 7 required printing every removed
   sentence with its slug. Prompt 8 fixed it by treating line breaks and " - " markers as sentence
   boundaries.
2. **The local LLM's rewrites and advice were wrong in three ways (Milestone 6b).** Filler like
   "This AI tool helps… streamlining" made the grant-proposal holdout come out falsely Crowded
   (20+ "relevant" matches). B1's rewrite turned "who can watch the kids" into "neighborhood watch
   program". The advice stated a wrong status fact (that only Waypoint was active). I caught all
   three by asking for each rewrite next to its original and checking verdicts on holdout pitches
   the thresholds weren't fit to (prompt 15). Prompt 16 fixed them with a stricter rewrite prompt
   and a rule that the advice never states company status. I documented the remaining drift as a
   README limitation instead of tuning against the demo queries.
3. **Bugs in the frozen code (test pass).** Superscript year digits crashed the app. The
   "Turn rewrite on" hint showed even when rewrite was already on. A distance printed as 0.530
   didn't count as within the 0.53 cutoff. I caught these with a separate test pass that was told
   to record bugs, not fix them (prompt 23), then fixed them on 10/26 (prompt 24).
4. **The rename never made it into the code (publish).** The menu header still said "Startup Idea
   Checker". It was caught because I made "confirm the header" an explicit step and told Claude to
   stop on any failure (prompt 20).
5. **Prevented: outdated Chroma API.** In Milestone 2 I told the agent to use only the 1.x API
   (no `Client(Settings(...))`, no `.persist()`) and to check the current docs for the cosine
   setting. Prompt 6 held ingest to the same API and cosine setting.
