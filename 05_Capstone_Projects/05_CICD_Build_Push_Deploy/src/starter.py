# starter.py — CI/CD Build, Push, Deploy
#
# This file scaffolds the FastAPI app used in the CI/CD pipeline project.
# Fill in each TODO. The CI pipeline will build and test this app.
# See solution.py for the full working version.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI()

# In-memory store for this project (no database — keeps CI setup simple).
# Items are stored as a list of dicts: [{"id": 1, "name": "...", "price": 9.99}]
_items: List[Dict[str, Any]] = []
_next_id = 1  # auto-increment counter


# TODO: Define a Pydantic model for creating an item.
# Fields: name (str), price (float)
class ItemCreate(BaseModel):
    pass


# TODO: Define a Pydantic model for an item response.
# Fields: id (int), name (str), price (float)
class Item(BaseModel):
    pass


@app.get("/health")
def health():
    """Liveness/readiness probe. Returns {"status": "ok"}."""
    # TODO: Return {"status": "ok"}.
    pass


@app.get("/")
def root():
    """Root endpoint. Returns a welcome message."""
    # TODO: Return {"message": "CI/CD Demo API"}.
    pass


@app.get("/items")
def list_items():
    """Return all items.
    Return format: {"items": [...]}
    """
    # TODO: Return all items from _items.
    pass


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    """Create a new item and return it with its assigned id.
    Hint: use the global _next_id counter.
    """
    # TODO: Build a new item dict, append to _items, increment _next_id.
    # Return the new item dict.
    global _next_id
    pass


@app.get("/items/{item_id}")
def get_item(item_id: int):
    """Return a single item by id. Raise 404 if not found."""
    # TODO: Search _items for an item where item["id"] == item_id.
    # If not found, raise HTTPException(status_code=404, detail="Item not found").
    pass
