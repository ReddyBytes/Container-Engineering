# starter.py — Full-Stack on K8s
#
# This file scaffolds the FastAPI backend for the fullstack project.
# Fill in each TODO to complete the implementation.
# See solution.py for the full working version.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# TODO: Read DB connection parameters from environment variables.
# The ConfigMap sets: DB_HOST, DB_PORT, LOG_LEVEL, APP_ENV
# The Secret sets:    DB_USER, DB_PASSWORD, DB_NAME
DB_HOST = None
DB_PORT = None
DB_USER = None
DB_PASSWORD = None
DB_NAME = None


# TODO: Define a Pydantic model for creating an item.
# Fields: name (str), price (float)
class ItemCreate(BaseModel):
    pass


# TODO: Define a Pydantic model for an item response.
# Fields: id (int), name (str), price (float)
class Item(BaseModel):
    pass


def get_connection():
    """Return a new psycopg2 connection using the environment-sourced config."""
    # TODO: Call psycopg2.connect() with the DB_ variables above.
    pass


def init_db():
    """Create the items table if it does not exist."""
    # TODO: Connect to Postgres and run:
    # CREATE TABLE IF NOT EXISTS items (
    #     id    SERIAL PRIMARY KEY,
    #     name  TEXT NOT NULL,
    #     price FLOAT NOT NULL
    # );
    pass


@app.on_event("startup")
def startup():
    """Initialize the database table on startup."""
    # TODO: Call init_db() here.
    pass


@app.get("/health")
def health():
    """Return 200 with postgres connection status.
    Try a SELECT 1 query. If it succeeds, postgres is 'connected'.
    If it raises, return 'disconnected'.
    """
    # TODO: Implement health check.
    # Return: {"status": "ok", "postgres": "connected"} on success
    pass


@app.get("/")
def root():
    """Return a welcome message."""
    # TODO: Return {"message": "Full-Stack K8s Backend"}.
    pass


@app.get("/items")
def list_items():
    """Return all items from the database.
    Return format: {"items": [{"id": 1, "name": "...", "price": 9.99}, ...]}
    """
    # TODO: SELECT id, name, price FROM items ORDER BY id.
    pass


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    """Insert a new item and return it with its generated id."""
    # TODO: INSERT INTO items (name, price) VALUES (%s, %s) RETURNING id, name, price.
    pass


@app.get("/items/{item_id}")
def get_item(item_id: int):
    """Return a single item by id, or 404 if not found."""
    # TODO: SELECT id, name, price FROM items WHERE id = %s.
    # Raise HTTPException(status_code=404) if no row returned.
    pass
