# starter.py
# Project 03: Deploy an App to Kubernetes — scaffolded app
#
# This is the same FastAPI app from Project 01.
# In this project the containerization is handled — your task is the Kubernetes manifests.
#
# Use this file to understand what the app does, then write the k8s/ YAML files
# that deploy it to a cluster.
#
# Run locally (no Kubernetes needed):
#   uvicorn starter:app --reload

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(
    title="My Dockerized API",
    version="1.0.0",
)

# In-memory store — resets on pod restart.
# This is intentional for this project: focus is K8s manifests, not persistence.
# See Project 04 for StatefulSets and Postgres in K8s.
items_db: List[dict] = []
counter = {"value": 0}

# These environment variables come from the ConfigMap and Secret you will write.
# The app reads them at startup.
APP_ENV = os.getenv("APP_ENV", "development")    # ← injected by ConfigMap
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")       # ← injected by ConfigMap
DB_USER = os.getenv("DB_USER", "")               # ← injected by Secret
DB_PASSWORD = os.getenv("DB_PASSWORD", "")       # ← injected by Secret


class Item(BaseModel):
    name: str
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float


@app.get("/")
def root():
    # TODO: Return a welcome message that also includes APP_ENV and LOG_LEVEL
    # so you can confirm the ConfigMap values are being injected correctly.
    return {
        "message": "Hello from Kubernetes!",
        "version": app.version,
        # TODO: add "env": APP_ENV and "log_level": LOG_LEVEL
    }


@app.get("/health")
def health():
    # This endpoint is used by BOTH the readiness and liveness probes.
    # It must return HTTP 200. Kubernetes will mark the pod unhealthy if it returns anything else.
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return {"items": items_db}


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: Item):
    counter["value"] += 1
    new_item = {"id": counter["value"], "name": item.name, "price": item.price}
    items_db.append(new_item)
    return new_item


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

# ---------------------------------------------------------------------------
# Your main task: write the four YAML files in k8s/
# ---------------------------------------------------------------------------
# k8s/configmap.yaml  — APP_ENV, LOG_LEVEL, WORKERS
# k8s/secret.yaml     — DB_USER, DB_PASSWORD, DB_NAME (base64-encoded)
# k8s/deployment.yaml — 3 replicas, resource limits, readiness + liveness probes
# k8s/service.yaml    — NodePort on 30080
#
# Then: kubectl apply -f k8s/
