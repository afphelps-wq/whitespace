"""ChromaDB smoke test: persistence, cosine distance, default embeddings. No real data."""
from pprint import pprint

import chromadb

COMPANIES = [
    ("c01", "AI assistant that reads your inbox, finds a time slot that works for every attendee, and books it on everyone's calendar.", "Active", 2023),
    ("c02", "Social app that pairs people who just relocated with small local groups built around a shared hobby, from hiking to chess.", "Active", 2022),
    ("c03", "Payroll and benefits software for restaurants with hourly staff.", "Active", 2019),
    ("c04", "Marketplace connecting homeowners with vetted plumbers and electricians.", "Acquired", 2016),
    ("c05", "Telehealth platform for prescribing and monitoring blood pressure medication.", "Active", 2021),
    ("c06", "API that detects fraudulent credit card transactions in real time.", "Acquired", 2017),
    ("c07", "Subscription box delivering locally roasted coffee beans each month.", "Inactive", 2015),
    ("c08", "Robotics startup automating warehouse picking and packing.", "Active", 2020),
    ("c09", "Tutoring platform matching high school students with college mentors for SAT prep.", "Inactive", 2018),
    ("c10", "Open-source observability tool for tracing slow database queries.", "Active", 2024),
    ("c11", "Carbon accounting software that helps manufacturers report emissions.", "Active", 2022),
    ("c12", "Pet insurance with instant claims paid out through a mobile app.", "Inactive", 2016),
]

QUERIES = [
    "I waste half my week emailing back and forth to find a time that works for everyone",
    "I moved to a new city and don't know anyone who's into climbing",
]
NONSENSE = "purple elephant tax law banana"

client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_or_create_collection(
    name="smoke",
    configuration={"hnsw": {"space": "cosine"}},
)
print("configuration:", collection.configuration)

if collection.count() == 0:
    collection.add(
        ids=[c[0] for c in COMPANIES],
        documents=[c[1] for c in COMPANIES],
        metadatas=[{"status": c[2], "batch_year": c[3]} for c in COMPANIES],
    )
    print("added", len(COMPANIES), "items")
else:
    print("collection already populated, skipping add")

print("count:", collection.count())

for q in QUERIES:
    print(f"\n== query: {q!r} ==")
    pprint(collection.query(query_texts=[q], n_results=3), width=120)

print(f"\n== nonsense query: {NONSENSE!r} ==")
res = collection.query(query_texts=[NONSENSE], n_results=3)
print("ids:", res["ids"][0])
print("distances:", res["distances"][0])
