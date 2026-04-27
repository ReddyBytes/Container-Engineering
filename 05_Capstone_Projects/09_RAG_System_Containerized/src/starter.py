"""
Project 09: RAG System Containerized
starter.py — skeleton for you to complete

Fill in all sections marked TODO.
Run with: uvicorn starter:app --host 0.0.0.0 --port 8000
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# TODO: import chromadb

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Configuration — read from environment variables
# ---------------------------------------------------------------------------

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")  # ← hostname of chromadb service
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8001"))  # ← port chromadb listens on
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "documents")  # ← shared collection name

# ---------------------------------------------------------------------------
# ChromaDB client — initialised on startup, not at module level
# This avoids a crash if ChromaDB isn't ready when the module is imported.
# ---------------------------------------------------------------------------

chroma_client = None  # ← will be set in startup()
collection = None     # ← will be set in startup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on startup and once on shutdown."""
    global chroma_client, collection

    # TODO: create a chromadb.HttpClient pointing at CHROMA_HOST:CHROMA_PORT
    # TODO: get-or-create a collection named COLLECTION_NAME
    # TODO: log how many documents are already in the collection

    yield  # app is running

    logger.info("Shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="RAG API", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    n_results: int = 3  # ← how many document chunks to retrieve


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """
    Returns 200 if the API is up and ChromaDB is reachable.
    Returns 503 if ChromaDB cannot be contacted.

    TODO:
    - Try to call collection.count() to verify the connection is live
    - Return {"status": "ok", "chromadb": "connected", "documents": <count>}
    - Raise HTTPException(503) if the call fails
    """
    return {"status": "not_implemented"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Embeds the question, retrieves the top-N relevant chunks from ChromaDB,
    and returns the results.

    TODO:
    - Embed request.question using sentence-transformers (all-MiniLM-L6-v2)
    - Call collection.query(query_embeddings=[...], n_results=request.n_results)
    - Format the retrieved documents into a readable answer string
    - Return QueryResponse with the answer and source filenames from metadata
    """
    raise HTTPException(status_code=501, detail="Not implemented")
