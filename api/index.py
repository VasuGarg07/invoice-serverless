from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from .models import Invoice
from .invoice_service import build_invoice_pdf

origins = os.environ.get("CORS_ORIGINS", "http://localhost:5187").split(",")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["POST"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.post("/api/invoice/generate")
def generate_invoice(invoice: Invoice):
    buffer = build_invoice_pdf(invoice)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice-{invoice.invoice_id}.pdf"
        }
    )