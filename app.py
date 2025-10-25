import os
from typing import List, Optional
from functools import lru_cache

from fastapi import FastAPI, Query, Header, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct  # optional; safe to keep

# -------- Config --------
RELAY_BEARER_TOKEN = os.getenv("RELAY_BEARER_TOKEN")  # optional
DEFAULT_COLLECTIONS = ["eurorack_manuals", "eurorack_forums", "eurorack_notes"]
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

app = FastAPI(title="Eurorack KB Relay", version="1.0.0")

# -------- Lazy singletons (fast startup, minimal RAM) --------
@lru_cache(maxsize=1)
def get_qdrant() -> QdrantClient:
    endpoint = os.getenv("QDRANT_ENDPOINT")
    api_key = os.getenv("QDRANT_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError("QDRANT_ENDPOINT and QDRANT_API_KEY must be set")
    return QdrantClient(url=endpoint, api_key=api_key, timeout=30)

@lru_cache(maxsize=1)
def get_model():
    # Import here so transformers/torch don't load until first use
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)

# -------- Models --------
class Hit(BaseModel):
    score: float
    text: str
    payload: dict

# -------- Auth helper --------
def _auth_or_401(authorization: Optional[str]):
    if RELAY_BEARER_TOKEN:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1].strip()
        if token != RELAY_BEARER_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid bearer token")

# -------- Routes --------
@app.get("/health")
def health():
    """Simple readiness probe for Render."""
    return {"ok": True}

@app.get("/healthz")
def healthz():
    """Alias health check (for Render port scan)."""
    return {"ok": True}

@app.get("/search", response_model=List[Hit])
def search(
    q: str = Query(..., description="Natural-language query"),
    k: int = Query(8, ge=1, le=50),
    collections: Optional[str] = Query(None, description="Comma-separated list of collections to search"),
    authorization: Optional[str] = Header(None),
):
    _auth_or_401(authorization)
    coll_list = collections.split(",") if collections else DEFAULT_COLLECTIONS

    model = get_model()
    vec = model.encode([q], normalize_embeddings=True)[0].tolist()

    client = get_qdrant()
    out: List[Hit] = []
    for coll in coll_list:
        res = client.search(
            collection_name=coll,
            query_vector=vec,
            limit=k,
            with_payload=True,
        )
        for r in res:
            payload = r.payload or {}
            text = payload.get("text") or payload.get("chunk") or ""
            out.append(Hit(score=r.score, text=text, payload=payload))

    out.sort(key=lambda x: x.score, reverse=True)
    return out[:k]
