import os
import tempfile

os.environ["INVENTORY_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
import app as inv  # noqa: E402

c = inv.app.test_client()
item = {"product_id": "P1", "name": "USB Cable", "category": "Accessories", "quantity": 10, "price": 199.5}


def test_add_and_duplicate_id():
    assert c.post("/api/products", json=item).status_code == 201
    assert c.post("/api/products", json=item).status_code == 409


def test_rejects_negative_quantity_and_price():
    assert c.post("/api/products", json={**item, "product_id": "P2", "quantity": -1}).status_code == 400
    assert c.post("/api/products", json={**item, "product_id": "P2", "price": -5}).status_code == 400


def test_search_found_and_not_found():
    assert len(c.get("/api/products?q=cable").json) == 1
    assert c.get("/api/products?q=zzz").json == []


def test_cannot_reduce_stock_below_zero():
    assert c.put("/api/products/P1", json={"quantity": -1}).status_code == 400
    assert c.get("/api/products/P1").json["quantity"] == 10


def test_update_low_stock_delete_and_missing():
    assert c.put("/api/products/P1", json={"quantity": 3}).json["quantity"] == 3
    assert len(c.get("/api/products?low=1").json) == 1
    assert c.put("/api/products/NOPE", json={"quantity": 1}).status_code == 404
    assert c.delete("/api/products/P1").status_code == 200
    assert c.delete("/api/products/P1").status_code == 404
