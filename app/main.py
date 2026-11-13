"""
FastAPI application for BarcodeReader.

Provides API endpoints for barcode scanning, category inspection,
catalogue browsing, and serves the static frontend UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.catalogue import (
    Catalogue,
    InvalidBarcodeError,
    ProductNotFoundError,
    default_catalogue,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
GENERATED_DIR = BASE_DIR.parent / "generated"

# Ensure directories exist for static and generated mounts
STATIC_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="BarcodeReader API",
    description="Barcode-Based Product Identification and Classification System (LDAM)",
    version="1.0.0",
)

# Enable CORS for local development and future controller integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and generated assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")


class ScanRequest(BaseModel):
    """Payload schema for barcode scan requests."""

    barcode: str = Field(..., description="Scanned barcode string")

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Barcode must be a string.")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Barcode cannot be empty or whitespace.")
        return cleaned


class ProductResponse(BaseModel):
    """Response schema for product information."""

    id: str
    barcode: str
    name: str
    category_id: int
    category_name: str
    category_code: str | None = None


@app.get("/", summary="Serve Frontend UI", include_in_schema=False)
async def serve_index():
    """Serve the primary HTML interface."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frontend index.html file not found.",
        )
    return FileResponse(index_file)


@app.get("/api/health", summary="Health Check")
async def health_check() -> Dict[str, Any]:
    """Return health status and catalogue readiness."""
    categories = default_catalogue.get_categories()
    products = default_catalogue.get_products(resolve_categories=False)
    return {
        "status": "healthy",
        "project": "BarcodeReader",
        "phase": 3,
        "categories_count": len(categories),
        "products_count": len(products),
    }


@app.get("/api/categories", summary="List All Categories")
async def get_categories() -> List[Dict[str, Any]]:
    """Return all categories with associated product counts."""
    return default_catalogue.get_category_summary()


@app.get("/api/products", summary="List All Products")
async def get_products() -> List[Dict[str, Any]]:
    """Return the complete product catalogue with resolved category names."""
    return default_catalogue.get_products(resolve_categories=True)


@app.get("/api/labels/pdf", summary="Download Printable Barcode Labels PDF")
async def download_labels_pdf():
    """Return the printable 16-label A4 PDF sheet for 100% scale printing."""
    pdf_file = GENERATED_DIR / "barcodes" / "demo_labels_a4.pdf"
    if not pdf_file.exists():
        try:
            from scripts.generate_labels import generate_all_labels
            generate_all_labels()
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Printable labels PDF generation failed: {err}",
            ) from err

    if not pdf_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Printable labels PDF could not be found or generated.",
        )

    return FileResponse(
        pdf_file,
        media_type="application/pdf",
        filename="demo_labels_a4.pdf",
    )


@app.post(
    "/api/scan",
    summary="Scan Barcode",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Product successfully identified."},
        400: {"description": "Empty or malformed barcode."},
        404: {"description": "Unknown barcode (no matching product)."},
    },
)
async def scan_barcode(request: ScanRequest) -> Dict[str, Any]:
    """
    Accept a barcode and look up product details and category.

    - Valid barcode: returns product details and category
    - Unknown barcode: returns 404 with descriptive error
    - Empty / malformed: returns 400 validation error
    """
    try:
        product = default_catalogue.lookup_by_barcode(request.barcode)
        return product
    except InvalidBarcodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port)
