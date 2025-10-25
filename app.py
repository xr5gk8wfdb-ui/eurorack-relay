import os
from typing import List, Optional
from fastapi import FastAPI, Query, Header, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from sentence_transformers import SentenceTransformer

QDRANT_ENDPOINT = os.environ["QDRANT_ENDPOINT"]
QDRANT_API_KEY  = os.environ["QDRANT_API_KEY"]
RELAY_BEARER_TOKEN = os.environ.get("RELAY_BEARER_TOKEN")  # optional

DEFAULT_COLLECTIONS = ["eurorack_manuals","eurorack_forums","eurorack_notes"]
EMBED_MODEL = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

app = FastAPI(title="Eurorack KB Relay", version="1.0.0")

# init outside request path so model and client are reused
_client = QdrantClient(url=QDRANT_ENDPOINT, api_key=QDRANT_API_KEY, timeout=30)
_model  = SentenceTransformer(EMBED_MODEL)  # 384-dim

class Hit(BaseModel):
    score: float
    text: str
    payload: dict

def _auth_or_401(authorization: Optional[str]):
    if RELAY_BEARER_TOKEN:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1].strip()
        if token != RELAY_BEARER_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid bearer token")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/search", response_model=List[Hit])
def search(
    q: str = Query(..., description="Natural-language query"),
    k: int = Query(8, ge=1, le=50),
    collections: Optional[str] = Query(None, description="Comma-separated list of collections to search"),
    authorization: Optional[str] = Header(None)
):
    _auth_or_401(authorization)
    coll_list = collections.split(",") if collections else DEFAULT_COLLECTIONS
    vec = _model.encode([q], normalize_embeddings=True)[0].tolist()

    out: List[Hit] = []
    for coll in coll_list:
        res = _client.search(
            collection_name=coll,
            query_vector=vec,
            limit=k,
            with_payload=True
        )
        for r in res:
            payload = r.payload or {}
            text = payload.get("text") or payload.get("chunk") or ""
            out.append(Hit(score=r.score, text=text, payload=payload))
    out.sort(key=lambda x: x.score, reverse=True)
    return out[:k]
