# solution.py — Full-Stack on K8s
#
# Full working FastAPI backend.
# Reads database config from environment variables set by
# ConfigMap (backend-config) and Secret (backend-secret).

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# Read connection params from environment.
# ConfigMap provides non-sensitive config; Secret provides credentials.
DB_HOST = os.environ["DB_HOST"]         # set by ConfigMap: postgres.fullstack.svc.cluster.local
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ["DB_USER"]         # set by Secret (base64-decoded by K8s)
DB_PASSWORD = os.environ["DB_PASSWORD"] # set by Secret
DB_NAME = os.environ["DB_NAME"]         # set by Secret


class ItemCreate(BaseModel):
    name: str
    price: float


class Item(BaseModel):
    id: int
    name: str
    price: float


def get_connection():
    """Open and return a new database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
    )


def init_db():
    """Create the items table if it does not exist yet."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id    SERIAL PRIMARY KEY,
                    name  TEXT NOT NULL,
                    price FLOAT NOT NULL
                )
                """
            )
        conn.commit()
    finally:
        conn.close()


@app.on_event("startup")
def startup():
    """Run once when the pod starts — ensure the schema exists."""
    init_db()


@app.get("/health")
def health():
    """Liveness/readiness probe endpoint.
    K8s calls this on a schedule to decide whether to route traffic here.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")  # ← cheapest possible connectivity check
        conn.close()
        return {"status": "ok", "postgres": "connected"}
    except Exception:
        return {"status": "ok", "postgres": "disconnected"}


@app.get("/")
def root():
    return {"message": "Full-Stack K8s Backend"}


@app.get("/items")
def list_items():
    """Return all items. The React frontend polls this endpoint."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, price FROM items ORDER BY id")
            rows = cur.fetchall()
        return {"items": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    """Insert a new item and return it with the database-assigned id."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO items (name, price) VALUES (%s, %s) RETURNING id, name, price",
                (item.name, item.price),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row)
    finally:
        conn.close()


@app.get("/items/{item_id}")
def get_item(item_id: int):
    """Fetch a single item by primary key."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, price FROM items WHERE id = %s",
                (item_id,),
            )
            row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return dict(row)
    finally:
        conn.close()
