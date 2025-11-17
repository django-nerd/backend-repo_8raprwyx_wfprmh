"""
Database Schemas for Logistics Cargo Booking

Each Pydantic model corresponds to a MongoDB collection. The collection name is the lowercased
class name by convention (e.g., Shipment -> "shipment").
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class Shipper(BaseModel):
    name: str = Field(..., description="Company or individual name")
    email: str = Field(..., description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    address: Optional[str] = Field(None, description="Headquarters or primary address")

class Quote(BaseModel):
    origin: str
    destination: str
    mode: Literal["air", "sea", "road"] = "sea"
    weight_kg: float = Field(..., gt=0)
    volume_cbm: float = Field(..., gt=0)
    price_usd: float = Field(..., gt=0)
    eta_days: int = Field(..., gt=0)

class Shipment(BaseModel):
    tracking_number: str
    origin: str
    destination: str
    mode: Literal["air", "sea", "road"] = "sea"
    weight_kg: float = Field(..., gt=0)
    volume_cbm: float = Field(..., gt=0)
    shipper_name: str
    shipper_email: str
    status: Literal[
        "created", "booked", "in_transit", "customs", "out_for_delivery", "delivered"
    ] = "created"
    quote_id: Optional[str] = None

class TrackingEvent(BaseModel):
    tracking_number: str
    status: str
    location: Optional[str] = None
    note: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
