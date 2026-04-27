# solution.py
# Project 01: Dockerize a Python App — complete working solution.
#
# This file is the full implementation of app/main.py.
# In the real project structure, this lives at app/main.py.
# Copy it there to run inside Docker.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(
    title="My Dockerized API",
    version="1.0.0",
    description="A FastAPI app containerized with Docker best practices.",
)

# In-memory store — resets every time the container restarts.
# Good enough for learning. See Project 02 for Postgres persistence.
items_db: List[dict] = []
counter = {"value": 0}  # ← dict so we can mutate inside functions without 'global'


class Item(BaseModel):
    name: str
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float


@app.get("/")
def root():
    """Welcome endpoint — confirms the API is reachable."""
    return {
        "message": "Hello from Dockerized FastAPI!",
        "version": app.version,
    }


@app.get("/health")
def health():
    """
    Health check endpoint.
    Docker's HEALTHCHECK instruction polls this URL every 30 seconds.
    Return HTTP 200 with {"status": "ok"} when the app is healthy.
    Return HTTP 503 if something is wrong (e.g., dependency unreachable).
    """
    return {"status": "ok"}


@app.get("/items")
def list_items():
    """Return all items in the in-memory store."""
    return {"items": items_db}


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: Item):
    """Add a new item to the store."""
    counter["value"] += 1  # ← increment before use so IDs start at 1
    new_item = {"id": counter["value"], "name": item.name, "price": item.price}
    items_db.append(new_item)
    return new_item


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    """Retrieve a single item by ID."""
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
