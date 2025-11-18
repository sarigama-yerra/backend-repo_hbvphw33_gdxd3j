"""
Database Schemas for Anti-Tarnish Jewellery Store

Each Pydantic model represents a collection in MongoDB. The collection name
is the lowercase of the class name (e.g., Product -> "product").
"""
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class Product(BaseModel):
    """
    Products collection schema
    Collection: "product"
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in USD")
    category: str = Field(..., description="Product category, e.g., 'Rings', 'Necklaces'")
    images: List[HttpUrl] = Field(default_factory=list, description="List of product image URLs")
    in_stock: bool = Field(True, description="Availability flag")
    stock_qty: int = Field(0, ge=0, description="Quantity in stock")
    rating: float = Field(4.8, ge=0, le=5, description="Average rating")
    anti_tarnish: bool = Field(True, description="Anti-tarnish coated")
    color_tone: Optional[str] = Field("rose-gold", description="Visual tone, used for UI accents")
    highlights: List[str] = Field(default_factory=list, description="Key selling points")


class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int = Field(..., ge=1)
    image: Optional[HttpUrl] = None


class Order(BaseModel):
    """
    Orders collection schema
    Collection: "order"
    """
    items: List[OrderItem]
    subtotal: float = Field(..., ge=0)
    shipping: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    customer_name: str
    customer_email: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    notes: Optional[str] = None
