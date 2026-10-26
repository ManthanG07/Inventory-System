"""Inventory Management System - Flask REST API + SQLite."""
import os
import sqlite3

from flask import Flask, g, jsonify, request

DB_PATH = os.environ.get("INVENTORY_DB", "inventory.db")
LOW_STOCK = 5  # quantity at or below this counts as low stock

app = Flask(__name__, static_folder="static", static_url_path="")

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    category   TEXT NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity >= 0),
    price      REAL    NOT NULL CHECK (price >= 0)
)"""


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(SCHEMA)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def err(message, code=400):
    return jsonify(error=message), code


def number(value, whole=False):
    """Parse a finite number (or whole number); return None if invalid."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    if whole:
        return int(n) if n.is_integer() else None
    return n


def validate(data, partial=False):
    """Return (clean_values, error). With partial=True only present fields are checked."""
    if not isinstance(data, dict):
        return None, "Send a JSON object"
    out = {}
    for f in ("product_id", "name", "category"):
        if f in data or not partial:
            v = data.get(f)
            v = "" if v is None else str(v).strip()
            if not v:
                return None, f"{f.replace('_', ' ').capitalize()} is required"
            out[f] = v
    if "quantity" in data or not partial:
        q = number(data.get("quantity"), whole=True)
        if q is None:
            return None, "Quantity must be a whole number"
        if q < 0:
            return None, "Quantity cannot be negative"
        out["quantity"] = q
    if "price" in data or not partial:
        p = number(data.get("price"))
        if p is None:
            return None, "Price must be a number"
        if p < 0:
            return None, "Price cannot be negative"
        out["price"] = round(p, 2)
    return out, None


def fetch_one(pid):
    row = get_db().execute("SELECT * FROM products WHERE product_id = ?", (pid,)).fetchone()
    return dict(row) if row else None


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/products")
def list_products():
    """List products. ?q= searches ID/name/category; ?low=1 returns only low stock."""
    q = request.args.get("q", "").strip()
    where, args = [], []
    if q:
        where.append("(product_id LIKE ? OR name LIKE ? OR category LIKE ?)")
        args += [f"%{q}%"] * 3
    if request.args.get("low"):
        where.append("quantity <= ?")
        args.append(LOW_STOCK)
    sql = "SELECT * FROM products"
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = get_db().execute(sql + " ORDER BY name COLLATE NOCASE", args).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/products/<pid>")
def get_product(pid):
    product = fetch_one(pid)
    return jsonify(product) if product else err("Product not found", 404)


@app.post("/api/products")
def add_product():
    data, error = validate(request.get_json(silent=True))
    if error:
        return err(error)
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO products (product_id, name, category, quantity, price) "
                "VALUES (:product_id, :name, :category, :quantity, :price)",
                data,
            )
    except sqlite3.IntegrityError:
        return err(f"Product ID {data['product_id']} already exists", 409)
    return jsonify(data), 201


@app.put("/api/products/<pid>")
def update_product(pid):
    data, error = validate(request.get_json(silent=True), partial=True)
    if error:
        return err(error)
    data.pop("product_id", None)  # the ID is the key and cannot change
    if not data:
        return err("Nothing to update")
    sets = ", ".join(f"{k} = :{k}" for k in data)  # keys come from validate(), not the client
    with get_db() as db:
        cur = db.execute(f"UPDATE products SET {sets} WHERE product_id = :pid", {**data, "pid": pid})
    if cur.rowcount == 0:
        return err("Product not found", 404)
    return jsonify(fetch_one(pid))


@app.delete("/api/products/<pid>")
def delete_product(pid):
    with get_db() as db:
        cur = db.execute("DELETE FROM products WHERE product_id = ?", (pid,))
    if cur.rowcount == 0:
        return err("Product not found", 404)
    return jsonify(deleted=pid)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
