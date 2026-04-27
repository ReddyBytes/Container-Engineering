"""
Project 09: RAG System Containerized
solution.py — complete working implementation

This file contains:
  1. FastAPI app with /query and /health endpoints
  2. Ingestion worker function (called as __main__ for the worker container)
  3. docker-compose.yml and Dockerfile examples as embedded strings

Run API:     uvicorn solution:app --host 0.0.0.0 --port 8000
Run worker:  python solution.py ingest
"""

import os
import sys
import glob
import logging
import hashlib
from contextlib import asynccontextmanager

import chromadb                                   # ← chromadb[client] for HTTP mode
from chromadb.config import Settings
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer  # ← local embedding model

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8001"))
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "documents")
DOCUMENTS_PATH = os.environ.get("DOCUMENTS_PATH", "/documents")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")  # ← small, fast, good quality

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def get_chroma_client() -> chromadb.HttpClient:
    """Create a ChromaDB HTTP client. Raises ConnectionError if unreachable."""
    return chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        settings=Settings(anonymized_telemetry=False),  # ← disable telemetry pings
    )


def get_embedding_model() -> SentenceTransformer:
    """Load the sentence-transformer model. Downloaded on first run, cached after."""
    logger.info(f"Loading embedding model: {EMBED_MODEL}")
    return SentenceTransformer(EMBED_MODEL)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks by character count.
    Overlap ensures context isn't cut off at chunk boundaries.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap  # ← step forward, leaving overlap behind
    return [c for c in chunks if c]   # ← drop empty strings


def stable_id(filename: str, chunk_index: int) -> str:
    """
    Deterministic chunk ID based on filename and position.
    Re-running ingestion upserts (updates) existing chunks instead of duplicating them.
    """
    raw = f"{filename}_{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]  # ← short but collision-resistant


# ---------------------------------------------------------------------------
# FastAPI lifespan — connect to ChromaDB once at startup
# ---------------------------------------------------------------------------

chroma_client = None
collection = None
embed_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chroma_client, collection, embed_model

    logger.info(f"Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
    chroma_client = get_chroma_client()
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # ← cosine similarity for text embeddings
    )
    embed_model = get_embedding_model()
    count = collection.count()
    logger.info(f"Collection '{COLLECTION_NAME}' ready — {count} chunks indexed")

    yield  # ← app serves requests here

    logger.info("API shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="RAG API", version="1.0.0", lifespan=lifespan)


class QueryRequest(BaseModel):
    question: str
    n_results: int = 3


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    chunks_retrieved: int


@app.get("/health")
async def health():
    """
    Liveness + readiness combined.
    Returns 200 with document count if ChromaDB is reachable.
    Returns 503 if the ChromaDB connection is broken.
    """
    try:
        count = collection.count()  # ← lightweight call, just checks connectivity
        return {"status": "ok", "chromadb": "connected", "documents": count}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"ChromaDB unreachable: {exc}")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    1. Embed the question with the same model used during ingestion
    2. Query ChromaDB for the top-N most similar chunks
    3. Assemble a context string from the results
    4. Return the context as the "answer" (swap in an LLM call here to generate prose)
    """
    if collection.count() == 0:
        raise HTTPException(
            status_code=422,
            detail="No documents ingested yet. Run the ingestion worker first.",
        )

    # Embed the question — must use the same model as ingestion
    query_embedding = embed_model.encode([request.question]).tolist()  # ← list of lists

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(request.n_results, collection.count()),  # ← can't request more than exist
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]   # ← outer list is per query; we sent one query
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # Build a readable answer from retrieved chunks
    # In production, pass this context to an LLM (e.g. Claude) for a prose answer
    context_parts = []
    sources = []
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        source = meta.get("source", "unknown")
        sources.append(source)
        context_parts.append(f"[Source: {source}, similarity: {1 - dist:.2f}]\n{doc}")

    answer = "\n\n---\n\n".join(context_parts)

    return QueryResponse(
        question=request.question,
        answer=answer,
        sources=list(dict.fromkeys(sources)),  # ← deduplicate while preserving order
        chunks_retrieved=len(documents),
    )


# ---------------------------------------------------------------------------
# Ingestion worker — run as: python solution.py ingest
# ---------------------------------------------------------------------------

def run_ingestion():
    """
    Walk DOCUMENTS_PATH, load all .pdf and .txt files,
    chunk them, embed them, and upsert into ChromaDB.
    Exits with code 0 on success, code 1 on error.
    """
    logger.info(f"Ingestion worker starting — scanning {DOCUMENTS_PATH}")

    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        model = get_embedding_model()
    except Exception as exc:
        logger.error(f"Failed to connect to ChromaDB: {exc}")
        sys.exit(1)

    # Find all supported files
    patterns = ["**/*.pdf", "**/*.txt"]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(DOCUMENTS_PATH, pattern), recursive=True))

    if not files:
        logger.warning(f"No .pdf or .txt files found in {DOCUMENTS_PATH}")
        sys.exit(0)

    logger.info(f"Found {len(files)} file(s) to ingest")

    total_chunks = 0
    for filepath in files:
        filename = os.path.basename(filepath)
        logger.info(f"Processing: {filename}")

        # Load file content
        try:
            if filepath.endswith(".pdf"):
                text = _load_pdf(filepath)
            else:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
        except Exception as exc:
            logger.error(f"Failed to read {filename}: {exc}")
            continue

        if not text.strip():
            logger.warning(f"Empty content: {filename}")
            continue

        # Split into chunks
        chunks = chunk_text(text)
        logger.info(f"  → {len(chunks)} chunks")

        # Embed all chunks in one batch (faster than one-at-a-time)
        embeddings = model.encode(chunks).tolist()

        # Upsert into ChromaDB
        col.upsert(
            ids=[stable_id(filename, i) for i in range(len(chunks))],
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"source": filename, "chunk": i} for i in range(len(chunks))],
        )
        total_chunks += len(chunks)

    logger.info(f"Ingestion complete — {total_chunks} chunks across {len(files)} file(s)")
    sys.exit(0)


def _load_pdf(filepath: str) -> str:
    """
    Extract text from a PDF using PyPDF2.
    Falls back to empty string if extraction fails (e.g. scanned image PDFs).
    """
    try:
        import PyPDF2  # ← optional dependency; add to requirements.txt
        text_parts = []
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("PyPDF2 not installed — treating PDF as unreadable")
        return ""
    except Exception as exc:
        logger.error(f"PDF extraction error: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Entry point — allows this file to run as both API and worker
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        run_ingestion()
    else:
        import uvicorn
        uvicorn.run("solution:app", host="0.0.0.0", port=8000, reload=False)


# ---------------------------------------------------------------------------
# Reference: docker-compose.yml
# ---------------------------------------------------------------------------

DOCKER_COMPOSE_YAML = """
version: "3.9"

services:

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"                         # host:8001 → container:8000
    volumes:
      - chroma_data:/chroma/chroma          # persist vector index
    environment:
      - ANONYMIZED_TELEMETRY=false
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s
    networks:
      - rag-net

  fastapi:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - CHROMA_HOST=chromadb               # Docker DNS resolves service name
      - CHROMA_PORT=8000                   # port inside the docker network
      - COLLECTION_NAME=documents
      - EMBED_MODEL=all-MiniLM-L6-v2
    depends_on:
      chromadb:
        condition: service_healthy         # wait for ChromaDB health check to pass
    networks:
      - rag-net

  ingestor:
    build:
      context: .
      dockerfile: Dockerfile.ingestor
    volumes:
      - documents:/documents               # read PDFs from shared staging volume
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - COLLECTION_NAME=documents
      - DOCUMENTS_PATH=/documents
    depends_on:
      chromadb:
        condition: service_healthy
    profiles:
      - ingest                             # only runs with: docker compose --profile ingest up
    restart: "no"                          # do not restart after exit
    networks:
      - rag-net

volumes:
  chroma_data:                             # vector index persistence
  documents:                               # PDF staging area

networks:
  rag-net:
    driver: bridge
"""

# ---------------------------------------------------------------------------
# Reference: Dockerfile.api
# ---------------------------------------------------------------------------

DOCKERFILE_API = """
# Stage 1: install Python dependencies
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target /install -r requirements.txt

# Stage 2: lean runtime image
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.12/site-packages  # copy deps
COPY src/solution.py .                                                  # copy app code

USER appuser
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "solution:app", "--host", "0.0.0.0", "--port", "8000"]
"""

# ---------------------------------------------------------------------------
# Reference: Dockerfile.ingestor (shares builder stage with API)
# ---------------------------------------------------------------------------

DOCKERFILE_INGESTOR = """
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target /install -r requirements.txt

FROM python:3.12-slim AS runtime

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.12/site-packages
COPY src/solution.py .

USER appuser

CMD ["python", "solution.py", "ingest"]   # worker entrypoint
"""
