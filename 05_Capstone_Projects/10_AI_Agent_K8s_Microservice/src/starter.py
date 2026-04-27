"""
Project 10: AI Agent K8s Microservice
starter.py — skeleton for you to complete

Fill in all sections marked TODO.
The full working solution is in solution.py.

Run locally: uvicorn starter:app --host 0.0.0.0 --port 8000
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

# TODO: import anthropic
# TODO: import prometheus_client (Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")  # ← injected from K8s Secret
MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-5-haiku-20241022")  # ← configurable
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))

# ---------------------------------------------------------------------------
# Prometheus metrics
# TODO: define three metrics:
#   - agent_requests_total: Counter with labels [endpoint, status_code]
#   - agent_request_duration_seconds: Histogram with label [endpoint]
#   - agent_active_requests: Gauge (no labels)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tool definitions — define these as Python functions and register with Claude
# ---------------------------------------------------------------------------

def calculator(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.
    TODO: use ast.literal_eval or a safe eval approach — never bare eval()
    """
    raise NotImplementedError


def current_time() -> str:
    """Return the current UTC time as an ISO string."""
    raise NotImplementedError


def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo and return top 3 results.
    TODO: use the duckduckgo_search package (DDGS().text())
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tool registry — maps tool names to functions for the dispatch loop
# ---------------------------------------------------------------------------

TOOLS = {
    "calculator": calculator,
    "current_time": current_time,
    "web_search": web_search,
}

# ---------------------------------------------------------------------------
# Claude tool specs — passed in the tools= argument to client.messages.create
# TODO: define the tool schemas as a list of dicts matching Anthropic's format
# ---------------------------------------------------------------------------

TOOL_SPECS = []  # ← replace with actual tool spec dicts


# ---------------------------------------------------------------------------
# Anthropic client — initialised on startup
# ---------------------------------------------------------------------------

anthropic_client = None  # ← set in lifespan startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    global anthropic_client

    # TODO: initialise the Anthropic client with ANTHROPIC_API_KEY
    # TODO: do a lightweight API call to verify the key is valid (e.g. list models)
    # TODO: log success or raise a clear error if the key is invalid

    yield

    logger.info("Shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Agent", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    system: str = "You are a helpful assistant with access to tools."


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str]
    model: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Run the multi-tool agent loop:
    1. Send the user message to Claude with the tool specs
    2. If Claude returns tool_use blocks, call the corresponding Python functions
    3. Send tool results back to Claude
    4. Repeat until Claude returns a text response with no tool calls
    5. Return the final text response

    TODO: implement the agentic loop
    TODO: track which tools were called
    TODO: increment agent_requests_total counter
    TODO: record duration in agent_request_duration_seconds histogram
    TODO: use agent_active_requests gauge (increment at start, decrement at end)
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@app.get("/health")
async def health():
    """
    Liveness probe endpoint.
    Checks that the Anthropic API is reachable and the API key is valid.

    TODO: make a lightweight Claude API call (e.g. client.models.list())
    TODO: return {"status": "ok", "claude": "reachable", "tools": list(TOOLS.keys())}
    TODO: return 503 if the API call fails
    """
    return {"status": "not_implemented"}


@app.get("/ready")
async def ready():
    """
    Readiness probe endpoint.
    Checks that /health passes AND all tools are callable.

    TODO: call health() first
    TODO: test each tool function with a trivial input
    TODO: return 503 if any tool raises an exception
    """
    return {"status": "not_implemented"}


@app.get("/metrics")
async def metrics():
    """
    Expose Prometheus metrics in text format.

    TODO: return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    """
    raise HTTPException(status_code=501, detail="Not implemented")
