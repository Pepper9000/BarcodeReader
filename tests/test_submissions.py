"""
Tests for hardened missing-product submissions, catalog overview, and recovery API endpoints.
"""

import base64
from io import BytesIO
import json
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app, PENDING_SUBMISSIONS_FILE
from app.catalogue import default_catalogue
from tests.test_recovery import generate_ean13

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_pending_submissions(tmp_path):
    """Ensure pending submissions are reset before each test."""
    PENDING_SUBMISSIONS_FILE.write_text("[]", encoding="utf-8")
    yield
    PENDING_SUBMISSIONS_FILE.write_text("[]", encoding="utf-8")


def test_submit_missing_product_temporarily_disabled():
    """Verify POST /api/submissions returns 503 Service Unavailable with clear rationale."""
    res = client.post(
        "/api/submissions",
        json={
            "barcode": "5901234123457",
            "name": "Organic Green Tea",
            "category_id": 3,
            "notes": "Found in local supermarket",
        },
    )
    assert res.status_code == 503
    data = res.json()
    assert "temporarily disabled" in data["detail"].lower()
    assert "storage" in data["detail"].lower() or "review" in data["detail"].lower()


def test_public_get_submissions_removed():
    """Verify GET /api/submissions is no longer exposed to unauthenticated public requests."""
    res = client.get("/api/submissions")
    # Method Not Allowed (405) or Not Found (404) — must not return 200 or submission queues
    assert res.status_code in (404, 405)
    assert res.status_code != 200


def test_catalog_overview_does_not_leak_pending_counts():
    """Verify GET /api/catalog-overview does not expose pending submission counts or internal queues."""
    res = client.get("/api/catalog-overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_products"] == 16
    assert data["total_categories"] == 8
    assert "pending_submissions_count" not in data
    assert "submissions" not in data
    assert "coverage_note" in data
    assert "not reported" in data["coverage_note"].lower()


def test_existing_pending_submissions_data_intact():
    """Verify existing pending submissions data on disk is kept intact and not wiped."""
    sample_data = [
        {
            "id": "SUB-0001",
            "barcode": "5901234123457",
            "name": "Historical Pre-Hardening Item",
            "status": "pending_review",
        }
    ]
    PENDING_SUBMISSIONS_FILE.write_text(json.dumps(sample_data), encoding="utf-8")

    # Access public endpoints and attempt a disabled submission
    client.get("/api/catalog-overview")
    client.get("/api/health")
    client.post("/api/submissions", json={"barcode": "1111111111116"})

    # Check file contents
    loaded = json.loads(PENDING_SUBMISSIONS_FILE.read_text(encoding="utf-8"))
    assert len(loaded) == 1
    assert loaded[0]["id"] == "SUB-0001"
    assert loaded[0]["barcode"] == "5901234123457"


def test_submissions_do_not_pollute_public_catalogue():
    """Verify that uncatalogued products do NOT appear in the public catalog."""
    res = client.post(
        "/api/submissions",
        json={"barcode": "5901234123457", "name": "Pending Item"},
    )
    assert res.status_code == 503

    # 1. /api/products should still have exactly 16 products
    prod_res = client.get("/api/products")
    assert prod_res.status_code == 200
    assert len(prod_res.json()) == 16

    # 2. Scanning the uncatalogued barcode should still return 404
    scan_res = client.post("/api/scan", json={"barcode": "5901234123457"})
    assert scan_res.status_code == 404


def test_api_recover_endpoint():
    """Verify POST /api/recover endpoint recovers damaged barcode and matches catalog."""
    code = "4006381333931"
    clean = generate_ean13(code)
    # Low contrast degradation
    w, h = clean.size
    lc = Image.new("L", (w, h))
    for y in range(h):
        for x in range(w):
            p = clean.getpixel((x, y))
            lc.putpixel((x, y), int(125 + (p / 255.0) * 15))

    buf = BytesIO()
    lc.save(buf, format="PNG")
    b64_data = base64.b64encode(buf.getvalue()).decode("ascii")

    res = client.post("/api/recover", json={"image_data": f"data:image/png;base64,{b64_data}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "recovered_from_damaged_image"
    assert data["barcode"] == code
    assert data["standard_decoder_success"] is False
    assert data["product_found"] is False  # not in demo catalog
