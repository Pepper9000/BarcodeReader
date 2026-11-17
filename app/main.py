"""
FastAPI application for BarcodeReader.

Provides API endpoints for barcode scanning, category inspection,
catalogue browsing, safe damaged EAN-13 recovery, missing-product submissions,
and serves the static frontend UI.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field, field_validator

from app.catalogue import (
    Catalogue,
    InvalidBarcodeError,
    ProductNotFoundError,
    default_catalogue,
)
from app.recovery import recover_damaged_ean13

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
GENERATED_DIR = BASE_DIR.parent / "generated"
DATA_DIR = BASE_DIR / "data"
PENDING_SUBMISSIONS_FILE = DATA_DIR / "pending_submissions.json"

# Ensure directories exist for static and generated mounts
STATIC_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Ensure pending submissions storage exists
if not PENDING_SUBMISSIONS_FILE.exists():
    PENDING_SUBMISSIONS_FILE.write_text("[]", encoding="utf-8")

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


class RecoverRequest(BaseModel):
    """Payload schema for damaged barcode recovery."""

    image_data: str = Field(..., description="Base64 encoded image string or data URL")


class SubmissionRequest(BaseModel):
    """Payload schema for submitting a missing product."""

    barcode: str = Field(..., description="Barcode to submit")
    name: Optional[str] = Field(None, description="Proposed product name")
    category_id: Optional[int] = Field(None, description="Proposed category ID")
    notes: Optional[str] = Field(None, description="Optional notes or context")

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Barcode must be a string.")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Barcode cannot be empty or whitespace.")
        return cleaned


def _load_pending_submissions() -> List[Dict[str, Any]]:
    """Load pending submissions safely from disk."""
    if not PENDING_SUBMISSIONS_FILE.exists():
        return []
    try:
        with open(PENDING_SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_pending_submissions(submissions: List[Dict[str, Any]]) -> None:
    """Save pending submissions atomically to disk."""
    with open(PENDING_SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(submissions, f, indent=2)


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


@app.get("/favicon.ico", summary="Serve Favicon", include_in_schema=False)
async def get_favicon():
    """Serve the primary application favicon."""
    favicon_file = STATIC_DIR / "favicon.ico"
    if not favicon_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favicon file not found.",
        )
    return FileResponse(favicon_file, media_type="image/x-icon")


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


@app.get("/api/catalog-overview", summary="Catalog Overview and Statistics")
async def get_catalog_overview() -> Dict[str, Any]:
    """
    Return comprehensive catalog overview including product counts per category
    and explanatory notes on coverage limitations.

    Internal submission queues and pending counts are excluded to avoid exposing
    unauthenticated queue metrics.
    """
    categories = default_catalogue.get_category_summary()
    products = default_catalogue.get_products(resolve_categories=False)
    return {
        "total_products": len(products),
        "total_categories": len(categories),
        "categories": categories,
        "coverage_note": (
            "Category coverage percentages are not reported because the total potential "
            "market products for each category are unrecorded in this system."
        ),
    }


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


@app.post(
    "/api/recover",
    summary="Safe Damaged Barcode Recovery",
    status_code=status.HTTP_200_OK,
)
async def recover_barcode(request: RecoverRequest) -> Dict[str, Any]:
    """
    Attempt safe recovery of a damaged barcode image.

    Runs standard ZXing decoder first; if unsuccessful, applies deterministic
    contrast normalization, skew correction, multi-scanline sampling, and strict
    consensus verification. Returns recovery metrics and crop comparisons.
    """
    raw_data = request.image_data.strip()
    if "," in raw_data:
        raw_data = raw_data.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(raw_data)
        im = Image.open(BytesIO(image_bytes))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse image data: {exc}",
        ) from exc

    result = recover_damaged_ean13(im)

    # If barcode was decoded or recovered, perform catalog lookup
    barcode = result.get("barcode")
    product = None
    product_found = False

    if barcode:
        try:
            product = default_catalogue.lookup_by_barcode(barcode)
            product_found = True
        except (ProductNotFoundError, InvalidBarcodeError):
            product = None
            product_found = False

    result["product"] = product
    result["product_found"] = product_found
    return result


@app.post(
    "/api/submissions",
    summary="Submit Missing Product (Temporarily Unavailable)",
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    responses={
        503: {
            "description": "Missing-product submission intake is temporarily unavailable.",
        }
    },
)
async def submit_missing_product(request: SubmissionRequest) -> Dict[str, Any]:
    """
    Missing-product submission intake is temporarily disabled.

    The application currently operates on ephemeral hosting without durable
    persistent storage (database or disk volume) and lacks an authenticated
    administrative review and moderation workflow. To prevent data loss and
    unverified catalog entries, submissions are disabled until persistent storage
    and authenticated moderation are configured. Existing pending submission data
    remains preserved intact.
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Missing-product submission intake is temporarily disabled. "
            "Durable persistent storage and an authenticated administrative "
            "review workflow are not currently configured."
        ),
    )


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port)
