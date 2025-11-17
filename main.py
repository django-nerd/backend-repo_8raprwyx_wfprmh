import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Shipper, Quote, Shipment, TrackingEvent

app = FastAPI(title="LogiFlow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "LogiFlow backend running"}

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
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
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

    return response

# --------- Models for request bodies ---------
class QuoteRequest(BaseModel):
    origin: str
    destination: str
    mode: str
    weight_kg: float
    volume_cbm: float

class BookShipmentRequest(QuoteRequest):
    shipper_name: str
    shipper_email: str

# --------- Helper functions ---------

def _collection(name: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    return db[name]

# --------- Quote Endpoints ---------
@app.post("/api/quotes", response_model=Quote)
def create_quote(payload: QuoteRequest):
    # Simple price model: base + weight + volume + mode multiplier
    base = 50
    multipliers = {"sea": 1.0, "road": 1.2, "air": 2.0}
    m = multipliers.get(payload.mode, 1.0)
    price = round(base + m * (payload.weight_kg * 0.8 + payload.volume_cbm * 20), 2)
    eta = {"sea": 21, "road": 7, "air": 3}.get(payload.mode, 14)
    quote = Quote(
        origin=payload.origin,
        destination=payload.destination,
        mode=payload.mode,
        weight_kg=payload.weight_kg,
        volume_cbm=payload.volume_cbm,
        price_usd=price,
        eta_days=eta,
    )
    qid = create_document("quote", quote)
    return quote

@app.get("/api/quotes", response_model=List[Quote])
def list_quotes(limit: int = 50):
    docs = get_documents("quote", {}, limit)
    # Map to model, ignoring DB-specific fields
    results: List[Quote] = []
    for d in docs:
        results.append(Quote(
            origin=d.get("origin"),
            destination=d.get("destination"),
            mode=d.get("mode"),
            weight_kg=d.get("weight_kg"),
            volume_cbm=d.get("volume_cbm"),
            price_usd=d.get("price_usd"),
            eta_days=d.get("eta_days"),
        ))
    return results

# --------- Shipment Endpoints ---------
@app.post("/api/shipments", response_model=Shipment)
def book_shipment(payload: BookShipmentRequest):
    # Create a tracking number
    import random, string
    tracking = "LGF-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    shipment = Shipment(
        tracking_number=tracking,
        origin=payload.origin,
        destination=payload.destination,
        mode=payload.mode,
        weight_kg=payload.weight_kg,
        volume_cbm=payload.volume_cbm,
        shipper_name=payload.shipper_name,
        shipper_email=payload.shipper_email,
    )
    create_document("shipment", shipment)
    # Initial tracking event
    event = TrackingEvent(tracking_number=tracking, status="created", location=payload.origin)
    create_document("trackingevent", event)
    return shipment

@app.get("/api/shipments")
def list_shipments(limit: int = 50):
    docs = get_documents("shipment", {}, limit)
    return docs

# --------- Tracking Endpoints ---------
@app.get("/api/track/{tracking_number}")
def get_tracking(tracking_number: str):
    events = get_documents("trackingevent", {"tracking_number": tracking_number})
    if not events:
        raise HTTPException(status_code=404, detail="Tracking number not found")
    # Sort by timestamp if present
    try:
        events.sort(key=lambda e: e.get("timestamp"))
    except Exception:
        pass
    return {"tracking_number": tracking_number, "events": events}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
