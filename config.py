CHROMA_PATH = "./chroma_store"
COLLECTION = "yc_companies"
PITCHES_COLLECTION = "my_pitches"
RAW_PATH = "data/raw/yc_all.json"
SELECTED_IDS_PATH = "data/selected_ids.txt"

MIN_YEAR = 2015
TARGET_N = 1500
SEED = 113
MAX_DOC_CHARS = 1000
BATCH_SIZE = 200

# A saved pitch this close (cosine distance) to a new one counts as a near-duplicate
DUP_MAX = 0.15
# Closer than this (but past DUP_MAX) is "same idea, different words": shown, not blocked.
# pitch_test.py: heavy rewording 0.415, unrelated 0.729
SIMILAR_MAX = 0.45

# Verdict thresholds, all cosine distance (calibrated in explore_queries.py section 6)
TAKEN_MAX = 0.40          # best match this close: the idea already exists
RELEVANT_MAX = 0.53       # a match this close counts as a real neighbor
CROWDED_MIN_COUNT = 3     # this many relevant matches: crowded space; zero: open space
GRAVEYARD_MIN = 3         # this many Inactive companies in the top REPORT_TOP: graveyard warning
SEARCH_N = 20            # companies fetched per pitch, so relevant matches aren't capped at the top 5
REPORT_TOP = 5            # companies listed in the report

# Local LLM (Ollama); optional, the app works without it
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"
LLM_TIMEOUT = 60
LLM_SEED = 113            # with temperature 0, the same input gives the same rewrite/advice

# Companies the two test queries should retrieve; always in the sample
FORCE_INCLUDE = ["meetingbird", "hera", "cron", "allo", "poppy", "milo"]
