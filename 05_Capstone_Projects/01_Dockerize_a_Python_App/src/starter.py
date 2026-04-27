# starter.py
# Project 01: Dockerize a Python App
#
# Fill in each TODO. Run with: uvicorn starter:app --reload
# Then move on to the Dockerfile once all endpoints return correct responses.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(
    title="My Dockerized API",
    version="1.0.0",
)

# TODO: Define an in-memory list to store items and a counter dict
# items_db = ...
# counter = ...


# TODO: Define a Pydantic model called Item with fields:
#   - name: str
#   - price: float
class Item(BaseModel):
    pass  # TODO: add fields


# TODO: Define a Pydantic model called ItemResponse with fields:
#   - id: int
#   - name: str
#   - price: float
class ItemResponse(BaseModel):
    pass  # TODO: add fields


@app.get("/")
def root():
    # TODO: Return a dict with keys "message" and "version"
    # message should say "Hello from Dockerized FastAPI!"
    # version should come from app.version
    pass


@app.get("/health")
def health():
    # TODO: Return {"status": "ok"}
    # This endpoint is called by Docker's HEALTHCHECK instruction.
    # It must return HTTP 200. Returning a dict from FastAPI does that automatically.
    pass


@app.get("/items")
def list_items():
    # TODO: Return {"items": items_db}
    pass


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: Item):
    # TODO:
    # 1. Increment counter["value"] by 1
    # 2. Build a new_item dict with id, name, price
    # 3. Append new_item to items_db
    # 4. Return new_item
    pass


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    # TODO:
    # 1. Loop through items_db looking for item["id"] == item_id
    # 2. Return the item if found
    # 3. Raise HTTPException(status_code=404, detail=f"Item {item_id} not found") if not found
    pass
