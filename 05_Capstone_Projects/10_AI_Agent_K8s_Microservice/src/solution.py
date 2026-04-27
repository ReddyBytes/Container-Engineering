"""
Project 10: AI Agent K8s Microservice
solution.py — complete working implementation

Includes:
  - FastAPI app with /chat, /health, /ready, /metrics
  - Multi-tool Claude agent (calculator, current_time, web_search)
  - Prometheus instrumentation
  - K8s YAML manifests as embedded strings at the bottom

Run locally: uvicorn solution:app --host 0.0.0.0 --port 8000
"""

import ast
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import anthropic                                              # ← Anthropic SDK
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import (                               # ← Prometheus instrumentation
    Counter,
    Gauge,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")  # ← injected from K8s Secret
MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-5-haiku-20241022")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))
MAX_TOOL_ROUNDS = int(os.environ.get("MAX_TOOL_ROUNDS", "5"))  # ← prevent infinite loops

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

REQUEST_COUNTER = Counter(
    "agent_requests_total",
    "Total requests by endpoint and status code",
    ["endpoint", "status_code"],                              # ← label names
)

REQUEST_DURATION = Histogram(
    "agent_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],  # ← LLM calls can be slow
)

ACTIVE_REQUESTS = Gauge(
    "agent_active_requests",
    "Number of requests currently being processed",
)

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.
    Uses AST parsing to reject anything that isn't a numeric expression.
    """
    try:
        # Parse the expression into an AST
        tree = ast.parse(expression, mode="eval")

        # Walk the tree and reject any node that isn't a safe numeric operation
        for node in ast.walk(tree):
            allowed = (
                ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
                ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
                ast.FloorDiv, ast.USub, ast.UAdd,
            )
            if not isinstance(node, allowed):
                return f"Error: unsafe expression (contains {type(node).__name__})"

        result = eval(compile(tree, "<calc>", "eval"))       # ← safe: AST already validated
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


def current_time() -> str:
    """Return the current UTC time in a human-readable format."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")


def web_search(query: str) -> str:
    """
    Search DuckDuckGo and return the top 3 results.
    duckduckgo-search requires no API key and has a generous free tier.
    """
    try:
        from duckduckgo_search import DDGS                   # ← import here to keep startup fast

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}")

        if not results:
            return "No results found."
        return "\n\n".join(results)
    except ImportError:
        return "Web search unavailable: duckduckgo-search not installed."
    except Exception as exc:
        return f"Search error: {exc}"


# ---------------------------------------------------------------------------
# Tool registry — maps name to function for the dispatch loop
# ---------------------------------------------------------------------------

TOOLS = {
    "calculator": calculator,
    "current_time": current_time,
    "web_search": web_search,
}

# ---------------------------------------------------------------------------
# Anthropic tool specs — must match Anthropic's tool definition format exactly
# ---------------------------------------------------------------------------

TOOL_SPECS = [
    {
        "name": "calculator",
        "description": "Evaluate a mathematical expression and return the numeric result. Use this for any arithmetic, including complex expressions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A mathematical expression, e.g. '2 + 2' or '847 * 23'",
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "current_time",
        "description": "Get the current UTC date and time. Use when the user asks what time or date it is.",
        "input_schema": {
            "type": "object",
            "properties": {},               # ← no inputs needed
            "required": [],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for current information. Use when the user asks about recent events, news, or facts you might not know.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
            },
            "required": ["query"],
        },
    },
]

# ---------------------------------------------------------------------------
# Anthropic client
# ---------------------------------------------------------------------------

anthropic_client = None  # ← set in lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    global anthropic_client

    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set — cannot start")

    logger.info("Initialising Anthropic client")
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Lightweight verification — list models to confirm the key is valid
    try:
        anthropic_client.models.list()
        logger.info("Anthropic API key verified successfully")
    except anthropic.AuthenticationError:
        raise RuntimeError("ANTHROPIC_API_KEY is invalid — cannot start")
    except Exception as exc:
        logger.warning(f"Could not verify API key on startup (will retry on requests): {exc}")

    yield

    logger.info("AI agent shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Agent", version="1.0.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    system: str = "You are a helpful assistant with access to tools. Use them when appropriate."


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str]
    model: str
    rounds: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Agentic loop: call Claude, handle tool_use blocks, send results back,
    repeat until Claude returns a final text response.
    """
    ACTIVE_REQUESTS.inc()                                     # ← track concurrency
    start = time.time()

    try:
        messages = [{"role": "user", "content": request.message}]
        tools_used = []
        rounds = 0

        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1

            response = anthropic_client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=request.system,
                tools=TOOL_SPECS,
                messages=messages,
            )

            # If Claude returned a text block without tool calls, we're done
            if response.stop_reason == "end_turn":
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                reply = "\n".join(text_blocks)
                REQUEST_COUNTER.labels(endpoint="/chat", status_code="200").inc()
                return ChatResponse(
                    reply=reply,
                    tools_used=tools_used,
                    model=MODEL,
                    rounds=rounds,
                )

            # Handle tool_use blocks
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                tools_used.append(tool_name)

                # Dispatch to the matching Python function
                if tool_name in TOOLS:
                    try:
                        tool_result = TOOLS[tool_name](**tool_input)  # ← unpack input dict
                    except Exception as exc:
                        tool_result = f"Tool error: {exc}"
                else:
                    tool_result = f"Unknown tool: {tool_name}"

                logger.info(f"Tool called: {tool_name}({tool_input}) → {tool_result[:80]}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,               # ← must match the tool_use id
                    "content": tool_result,
                })

            # Add Claude's tool_use response and our tool results to the message history
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        # Exceeded MAX_TOOL_ROUNDS — return whatever we have
        REQUEST_COUNTER.labels(endpoint="/chat", status_code="200").inc()
        return ChatResponse(
            reply="Agent reached maximum tool rounds without a final answer.",
            tools_used=tools_used,
            model=MODEL,
            rounds=rounds,
        )

    except anthropic.AuthenticationError:
        REQUEST_COUNTER.labels(endpoint="/chat", status_code="401").inc()
        raise HTTPException(status_code=401, detail="Invalid API key")
    except anthropic.RateLimitError:
        REQUEST_COUNTER.labels(endpoint="/chat", status_code="429").inc()
        raise HTTPException(status_code=429, detail="Claude API rate limit hit")
    except Exception as exc:
        REQUEST_COUNTER.labels(endpoint="/chat", status_code="500").inc()
        logger.error(f"Chat error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        duration = time.time() - start
        REQUEST_DURATION.labels(endpoint="/chat").observe(duration)
        ACTIVE_REQUESTS.dec()


@app.get("/health")
async def health():
    """
    Liveness probe.
    Verifies the Anthropic API is reachable and the key is valid.
    Returns 200 on success, 503 on failure.
    """
    REQUEST_COUNTER.labels(endpoint="/health", status_code="200").inc()
    try:
        anthropic_client.models.list()                       # ← lightweight, no charge
        return {
            "status": "ok",
            "claude": "reachable",
            "tools": list(TOOLS.keys()),
        }
    except Exception as exc:
        REQUEST_COUNTER.labels(endpoint="/health", status_code="503").inc()
        raise HTTPException(status_code=503, detail=f"Claude API unreachable: {exc}")


@app.get("/ready")
async def ready():
    """
    Readiness probe.
    Verifies health AND that all tools return without raising.
    Returns 200 if ready, 503 if not yet ready to serve traffic.
    """
    # First check Claude connectivity
    try:
        anthropic_client.models.list()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Claude API not ready: {exc}")

    # Test each tool with trivial inputs
    test_inputs = {
        "calculator": {"expression": "1+1"},
        "current_time": {},
        "web_search": {"query": "test"},
    }
    for name, inputs in test_inputs.items():
        try:
            TOOLS[name](**inputs)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Tool '{name}' not ready: {exc}")

    REQUEST_COUNTER.labels(endpoint="/ready", status_code="200").inc()
    return {"status": "ready", "tools": list(TOOLS.keys())}


@app.get("/metrics")
async def metrics():
    """
    Expose Prometheus metrics in text exposition format.
    Scraped by Prometheus every 15s.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# K8s YAML manifests — embedded here for reference / apply with kubectl
# ---------------------------------------------------------------------------

K8S_NAMESPACE = """
apiVersion: v1
kind: Namespace
metadata:
  name: ai-agent
"""

K8S_SECRET_EXAMPLE = """
# Create with kubectl — never store the actual key in this file:
#   kubectl create secret generic anthropic-secret \\
#     --from-literal=ANTHROPIC_API_KEY=sk-ant-... \\
#     --namespace ai-agent
#
# The YAML below is for reference only (value is a placeholder):
apiVersion: v1
kind: Secret
metadata:
  name: anthropic-secret
  namespace: ai-agent
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "REPLACE_ME"        # never commit a real key here
"""

K8S_DEPLOYMENT = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agent
  namespace: ai-agent
  labels:
    app: ai-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-agent
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1                  # at most 1 pod down during updates
      maxSurge: 1                        # spin up 1 extra pod before terminating old ones
  template:
    metadata:
      labels:
        app: ai-agent
      annotations:
        prometheus.io/scrape: "true"     # Prometheus auto-discovery
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: ai-agent
          image: ai-agent:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
          env:
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef:
                  name: anthropic-secret
                  key: ANTHROPIC_API_KEY  # ← never hardcoded, always from Secret
            - name: CLAUDE_MODEL
              value: "claude-3-5-haiku-20241022"
            - name: MAX_TOKENS
              value: "1024"
          resources:
            requests:
              cpu: "100m"                # ← required for HPA to calculate utilization
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15      # ← give the app time to start
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 2
"""

K8S_SERVICE = """
apiVersion: v1
kind: Service
metadata:
  name: ai-agent-svc
  namespace: ai-agent
spec:
  selector:
    app: ai-agent
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
"""

K8S_HPA = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-agent-hpa
  namespace: ai-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60        # ← scale up when average CPU > 60%
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # ← wait 5min before scaling down (prevents thrashing)
    scaleUp:
      stabilizationWindowSeconds: 0    # ← scale up immediately
"""

K8S_INGRESS = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-agent-ingress
  namespace: ai-agent
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: agent.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ai-agent-svc
                port:
                  number: 80
"""

DOCKERFILE = """
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target /install -r requirements.txt

FROM python:3.12-slim AS runtime

RUN useradd --create-home appuser
WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.12/site-packages
COPY src/solution.py .

USER appuser
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "solution:app", "--host", "0.0.0.0", "--port", "8000"]
"""
