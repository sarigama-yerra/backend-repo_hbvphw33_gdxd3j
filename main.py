import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order

app = FastAPI(title="Anti-Tarnish Jewellery Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_doc(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return doc


@app.get("/")
def read_root():
    return {"message": "Anti-Tarnish Jewellery API ready"}


@app.get("/api/products")
def list_products(category: Optional[str] = None, limit: int = 50):
    filt = {"category": category} if category else {}
    try:
        items = get_documents("product", filt, limit)
        return [serialize_doc(i) for i in items]
    except Exception:
        # If no products yet or DB not connected, seed a small catalogue in-memory for response
        sample = [
            Product(
                title="Luna Halo Ring",
                description="Anti-tarnish sterling silver ring with cubic zirconia halo.",
                price=59.0,
                category="Rings",
                images=[
                    "https://images.unsplash.com/photo-1520962918287-7448c2878f65?q=80&w=1200&auto=format&fit=crop",
                ],
                in_stock=True,
                stock_qty=25,
                color_tone="rose-gold",
                highlights=["Anti-tarnish coat", "Hypoallergenic", "Shimmer finish"],
            ).model_dump(),
            Product(
                title="Aurora Tennis Bracelet",
                description="Dainty bracelet with brilliant shine and long-lasting finish.",
                price=89.0,
                category="Bracelets",
                images=[
                    "https://images.unsplash.com/photo-1599643477877-530eb83abc8e?q=80&w=1200&auto=format&fit=crop",
                ],
                stock_qty=18,
                color_tone="platinum",
                highlights=["Water resistant", "Nickel-free", "Everyday wear"],
            ).model_dump(),
            Product(
                title="Celeste Pendant Necklace",
                description="Minimal pendant that catches light like a star.",
                price=72.0,
                category="Necklaces",
                images=[
                    "https://images.unsplash.com/photo-1617038260897-1039e0c1f16f?q=80&w=1200&auto=format&fit=crop",
                ],
                stock_qty=30,
                color_tone="rose-gold",
                highlights=["Anti-tarnish", "Lightweight", "Gift-ready"],
            ).model_dump(),
            Product(
                title="Nova Stud Earrings",
                description="Classic studs with mirror polish and protective finish.",
                price=45.0,
                category="Earrings",
                images=[
                    "https://images.unsplash.com/photo-1616400619175-5beda3a97703?q=80&w=1200&auto=format&fit=crop",
                ],
                stock_qty=40,
                color_tone="platinum",
                highlights=["Secure clasp", "Daily wear", "Anti-tarnish"],
            ).model_dump(),
        ]
        # attach fake ids for frontend linking
        for idx, s in enumerate(sample):
            s["id"] = f"seed-{idx}"
        if category:
            sample = [s for s in sample if s.get("category") == category]
        return sample[:limit]


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    # If looks like a Mongo ObjectId try DB, else return from seeded list by index
    if len(product_id) == 24:
        try:
            doc = db["product"].find_one({"_id": ObjectId(product_id)})
            if not doc:
                raise HTTPException(status_code=404, detail="Product not found")
            return serialize_doc(doc)
        except Exception:
            pass
    # fallback to seeded items mapping
    base = list_products()
    for p in base:
        if p.get("id") == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")


class CartItem(BaseModel):
    product_id: str
    quantity: int


class CheckoutRequest(BaseModel):
    items: List[CartItem]
    customer_name: str
    customer_email: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    notes: Optional[str] = None


@app.post("/api/checkout")
def checkout(payload: CheckoutRequest):
    # Fetch products to compute totals and validate stock
    ids = [ObjectId(i.product_id) for i in payload.items if len(i.product_id) == 24]
    prod_map = {}
    try:
        if ids:
            products = list(db["product"].find({"_id": {"$in": ids}}))
            for p in products:
                prod_map[str(p["_id"])]=p
    except Exception:
        pass

    order_items = []
    subtotal = 0.0
    for ci in payload.items:
        # If product not found in DB, fallback price
        base = prod_map.get(ci.product_id)
        if base:
            price = float(base.get("price", 0))
            title = base.get("title", "Item")
            image = (base.get("images") or [None])[0]
        else:
            # fallback seed lookup
            seed = None
            if not base:
                for p in list_products():
                    if p.get("id") == ci.product_id:
                        seed = p
                        break
            price = float((seed or {}).get("price", 50.0))
            title = (seed or {}).get("title", "Jewellery Piece")
            image = (seed or {}).get("images", [None])[0]
        line = price * ci.quantity
        subtotal += line
        order_items.append({
            "product_id": ci.product_id,
            "title": title,
            "price": price,
            "quantity": ci.quantity,
            "image": image,
        })

    shipping = 0 if subtotal >= 100 else 6.0
    total = round(subtotal + shipping, 2)

    order = Order(
        items=order_items,
        subtotal=round(subtotal, 2),
        shipping=shipping,
        total=total,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
        notes=payload.notes,
    )

    try:
        order_id = create_document("order", order)
    except Exception:
        order_id = None

    return {"order_id": order_id, "subtotal": order.subtotal, "shipping": order.shipping, "total": order.total}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
