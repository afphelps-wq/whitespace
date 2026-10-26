# Whitespace


## What it does and why I chose it
My app allows students to validate startup ideas. The user can type a full pitch or even just jot down a quick idea and the app searches through Y Combinator companies by meaning and tells the user how crowded the field is, whether similar ideas have failed, a market summary, specific angles to stand out, and what companies to look at. The app also keeps a history of your pitches so you can search through your past ideas.

I chose this becuase coming up with startup/business ideas is hard and knowing what has already been done, what works, and what openings in the market there are is very useful information. 
Note that the market summary and angles come from an **optional local LLM (Ollama)**, and everything else works without it.

## What's stored in the database
One item is a company that is a document with the name: one liner. long description. Documents are capped at 1000 characters, which keeps the starts of the description. The metadata includes the batch year, status of the company, the industry, and the website. The user pitch metadata includes when it was created, the verdict, and the top match. However the pitches are not mixed into the YC results.

The source is yc-oss API. There are 1500 compaines that I sampled propotionally by batch year from 5238 companies from 2015 to present. I force included 6 companies for test queries. I removed hiring/ "join us" sentences out of 110 of the documents. 

The pitches are a seperate collection so that your old ideas don't show up as competitors. 

## How to add and search
Option 1 checks an idea and saves it to your pitch history. There is also a duplicate warning. Option 2 searches past pitches with a reqrite toggle. 

## Two queries that prove a vector database earns its place
Query 1: "I waste half my week emailing back and forth to find a time that works for everyone" -> Hera at #3 (raw text, rewrite off), no shared content words even with prefix matching. 
Query 2: "We just moved in and have no idea who on our street could watch the kids in a pinch" -> Allo at #5, zero shared wors. Keyword search matches 112 docs but never finds Allo. 

## Limitations
- complaint style input scores far from everything, so the LLM rewrites to solve this. 
- The rewrite can drift meaning from the original pitch

## How I used AI
I used Claude in chat for brainstorming and creating the spec. I then used a seperate Claude agent to review outputs from Claud Code (Opus) in VS Code that was used for implementing based on the milestones outlined in the spec. I reviewed the output after every milestone before moving on. I used yc-oss.api, the YC company directory, Chroma docs, and Ollama as well. 

---

### Getting the data
The raw dataset is not in this repo.
1. `python3.14 ingest.py` builds the database. It downloads `https://yc-oss.github.io/api/companies/all.json` to `data/raw/yc_all.json` if the file isn't already there. **[verify: confirm ingest.py downloads it; otherwise run `python3.14 inspect_data.py` first]**
2. Ingest loads exactly the companies listed in `data/selected_ids.txt` (committed), so you get the same 1,500 companies I used. The source updates daily, so if any company has since been removed upstream, ingest prints a warning and skips it.
3. To rebuild from scratch: `python3.14 ingest.py --rebuild`. Embedding 1,500 companies takes about 35 seconds on a laptop CPU.

### Vector database and models
- **ChromaDB 1.5.9**, `PersistentClient` at `./chroma_store/`, cosine distance. Two collections: `yc_companies` and `my_pitches`.
- **Embedding model:** Chroma's default `all-MiniLM-L6-v2`. It downloads once (~79 MB) to `~/.cache/chroma` on first use.
- **Optional LLM:** `llama3.2:3b` via Ollama (~2 GB download), used for the pitch rewrite and the advice. Temperature 0 with a fixed seed.

### Install and run
Requires Python 3.14 (developed on macOS).
```
python3.14 -m pip install -r requirements.txt
python3.14 ingest.py
python3.14 app.py
```
- `python3.14 app.py --reset-pitches` clears your saved pitch history before starting.
- Optional LLM features:
  ```
  brew install ollama
  brew services start ollama
  ollama pull llama3.2:3b
  ```
  If Ollama isn't running, the app turns the rewrite off automatically and everything else still works.
