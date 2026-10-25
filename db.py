"""Chroma access: the YC companies collection and the user's saved pitches."""
import uuid
from datetime import datetime, timezone
from functools import lru_cache

import chromadb

from config import CHROMA_PATH, COLLECTION, DUP_MAX, PITCHES_COLLECTION, SEARCH_N


@lru_cache(maxsize=1)
def get_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_companies():
    return get_client().get_collection(COLLECTION)


def search_companies(text, n=SEARCH_N, where=None):
    """Raw Chroma query result for one pitch: ids, documents, metadatas, distances, closest first."""
    return get_companies().query(query_texts=[text], n_results=n, where=where)


def company_filter(active_only=False, year_from=None):
    """Chroma `where` for the app's two optional filters, or None for no filter."""
    conds = []
    if active_only:
        conds.append({"status": "Active"})
    if year_from is not None:
        conds.append({"batch_year": {"$gte": year_from}})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def get_pitches():
    return get_client().get_or_create_collection(
        name=PITCHES_COLLECTION,
        configuration={"hnsw": {"space": "cosine"}},
    )


def reset_pitches():
    """Delete every saved pitch by dropping and recreating the collection."""
    client = get_client()
    if PITCHES_COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(PITCHES_COLLECTION)
    return get_pitches()


def add_pitch(text, verdict="", top_match=""):
    pitch_id = str(uuid.uuid4())
    get_pitches().add(
        ids=[pitch_id],
        documents=[text],
        metadatas=[{
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "verdict": verdict,
            "top_match": top_match,
        }],
    )
    return pitch_id


def find_similar_pitches(text, n=5):
    """[(id, text, created_at, distance)] closest first; [] when nothing is saved yet."""
    pitches = get_pitches()
    count = pitches.count()
    if count == 0:
        return []
    res = pitches.query(query_texts=[text], n_results=min(n, count))
    return [(i, doc, m["created_at"], dist)
            for i, doc, m, dist in zip(res["ids"][0], res["documents"][0],
                                       res["metadatas"][0], res["distances"][0])]


def list_pitches():
    """[(id, text, metadata)] for every saved pitch, oldest first."""
    res = get_pitches().get(include=["documents", "metadatas"])
    rows = list(zip(res["ids"], res["documents"], res["metadatas"]))
    return sorted(rows, key=lambda r: r[2]["created_at"])


def check_duplicate(text):
    """The closest saved pitch (id, text, created_at, distance) if within DUP_MAX, else None."""
    closest = find_similar_pitches(text, n=1)
    if closest and closest[0][3] <= DUP_MAX:
        return closest[0]
    return None
