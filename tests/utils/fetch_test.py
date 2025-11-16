import sqlite3, json
import requests
from pathlib import Path
from collections import Counter
DB_PATH = "/Users/b.ajay/Downloads/dummy_papers.db". # <- modify the path as needed
SCRIPT_PATH = "/Users/b.ajay/Downloads/validate_papers.py" # <- modify the path as needed
def fetch_openalex(doi):
    url=f"https://api.openalex.org/works/doi:{doi}"
    r=requests.get(url)
    if r.status_code==200:
        data=r.json()
        return {
            "title":data.get("title"),
            "authors":[a["author"]["display_name"] for a in data.get("authorships", [])],
            "year":int(data["publication_year"]) if "publication_year" in data else None,
            "doi":data.get("doi")
        }
    return None
def fetch_arxiv(query):
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results=1"
    r = requests.get(url)
    if r.status_code == 200:
        # Arxiv returns XML feed, we’d need feedparser
        import feedparser
        feed = feedparser.parse(r.text)
        if feed.entries:
            e = feed.entries[0]
            return {
                "title": e.title,
                "authors": [a.name for a in e.authors],
                "year": int(e.published.split("-")[0]) if hasattr(e, "published") else None,
                "doi": e.get("arxiv_doi", None)
            }
    return None

def fetch_crossref(doi):
    url=f"https://api.crossref.org/works/{doi}"
    r=requests.get(url)
    if r.status_code==200:
        data=r.json()["message"]
        return {
            "title":data["title"][0] if "title" in data and data["title"] else None,
            "authors":[f"{a.get('given','')} {a.get('family','')}".strip() for a in data.get("author", [])],
            "year":data["issued"]["date-parts"][0][0] if "issued" in data else None,
            "doi":data.get("DOI")
        }
    return None
def fetch_semantic_scholar(doi):
    url=f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,authors,year,externalIds"
    r=requests.get(url)
    if r.status_code==200:
        data=r.json()
        return {
            "title":data.get("title"),
            "authors":[a["name"] for a in data.get("authors", [])],
            "year":data.get("year"),
            "doi":doi
        }
    return None
def maj_vote(values):
    from collections import Counter
    normalized=[(src,json.dumps(val,sort_keys=True)) for src,val in values if val]


ORDERED_SOURCES = ["openalex", "semantic_scholar", "crossref", "arxiv"]



#print(fetch_openalex("10.1038/s41586-020-2649-2"))
    
def maj_vote(values):
    from collections import Counter
    normalized=[(src,json.dumps(val,sort_keys=True)) for src,val in values if val]
    if not normalized:
        return None, []
    counts=Counter(val for src,val in normalized)
    max_count=max(counts.values())
    top_values=[val for val,count in counts.items() if count==max_count]
    if len(top_values)==1:
        return json.loads(top_values[0]), [src for src,val in normalized if val==top_values[0]]
    # Tie-breaker based on source priority
    PRIORITY_ORDER = {src: i for i, src in enumerate(ORDERED_SOURCES)}
    top_values.sort(key=lambda v: min(PRIORITY_ORDER.get(src, float('inf')) for src, val in normalized if val == v))
    return json.loads(top_values[0]), [src for src,val in normalized if val==top_values[0]]

def validate(id,fetcher):
    data={}
    for name, func in fetcher.items():
        try:
            data[name]=func(id)
        except Exception as e:
            #print(f"Error fetching from {name}: {e}")
            data[name]=None
    if not any(data.values()):
        arxiv=fetch_arxiv(id)
        data['arxiv']=arxiv
        if not arxiv:
            return {"raw": data, "validated": None, "reason": "No data from sources."}
    fields=["title","authors","year","doi"]
    validated={}
    field_sources={}
    for field in fields:
        vals=[]
        for src, content in data.items():
            if content and field in content:
                vals.append((src, content[field]))
        val, sources=maj_vote(vals)
        validated[field]=val
        field_sources[field]=sources
    return {"raw": data, "validated": validated, "sources": field_sources}


if Path(DB_PATH).exists():
    Path(DB_PATH).unlink()
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()     
c.execute("CREATE TABLE sources (id INTEGER PRIMARY KEY, identifier TEXT, source TEXT, payload TEXT)")
c.execute("CREATE TABLE validated_papers (id INTEGER PRIMARY KEY, identifier TEXT, validated_payload TEXT, metadata TEXT)")
conn.commit()


def store_raw_sources(conn, identifier, raw):
    c = conn.cursor()
    for src, payload in raw.items():
        c.execute("INSERT INTO sources (identifier, source, payload) VALUES (?, ?, ?)", (identifier, src, json.dumps(payload)))
    conn.commit()

def store_validated(conn, identifier, validated, field_sources):
    c = conn.cursor()
    metadata = {"field_sources": field_sources}
    c.execute("INSERT INTO validated_papers (identifier, validated_payload, metadata) VALUES (?, ?, ?)", (identifier, json.dumps(validated), json.dumps(metadata)))
    conn.commit()
fetchers = {"openalex": fetch_openalex, "semanticscholar": fetch_semantic_scholar, "crossref": fetch_crossref}
ids = ["10.1000/xyz123", "10.1000/conflict", "10.1000/unknown"]
results = {}
for ident in ids:
    res = validate(ident, fetchers)
    results[ident] = res
    store_raw_sources(conn, ident, res.get("raw", {}))
    if res.get("validated") is not None:
        store_validated(conn, ident, res["validated"], res.get("field_sources", {}))

print("=== sources ===")
for row in c.execute("SELECT id, identifier, source, payload FROM sources ORDER BY id"):
    print(row)
print("\n=== validated_papers ===")
for row in c.execute("SELECT id, identifier, validated_payload, metadata FROM validated_papers ORDER BY id"):
    print(row)

conn.close()


