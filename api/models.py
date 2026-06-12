from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from decimal import Decimal

class BillingInfo(BaseModel):
    name: str
    email: EmailStr
    address: str
    phone_number: str

class InvoiceItem(BaseModel):
    name: str
    description: Optional[str] = ""
    quantity: int
    price: Decimal = Field(ge=0)

class Invoice(BaseModel):
    invoice_id: str
    current_date: str
    due_date: str
    currency: str
    currency_symbol: str
    billing_to: BillingInfo
    billing_from: BillingInfo
    items: list[InvoiceItem]
    tax_rate: Decimal = Field(ge=0, le=100)
    discount: Decimal = Field(ge=0, le=100)
    notes: Optional[str] = ""