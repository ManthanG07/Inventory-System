# Inventory Management System

Flask REST API + SQLite + vanilla JS (Fetch API). Node.js is used for tooling (Prettier) only.

## Run
```bash
pip install flask pytest
npm install          # frontend tooling
npm start            # or: python app.py  ->  http://127.0.0.1:5000
npm test             # edge-case tests
npm run format       # format the frontend
```

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/products?q=term` | List / search by ID, name or category |
| GET | `/api/products?low=1` | Low-stock products (quantity <= 5) |
| POST | `/api/products` | Add product |
| PUT | `/api/products/<id>` | Update quantity, price, name or category |
| DELETE | `/api/products/<id>` | Delete product |

## Edge cases covered
- Negative quantity or price -> `400`
- Reducing stock below zero -> `400`, stock unchanged
- Duplicate product ID -> `409`
- Unknown product on update/delete -> `404`
- Search with no match -> empty list, "No products match" message
