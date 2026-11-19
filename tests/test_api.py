"""
Integration tests for FastAPI endpoints in BarcodeReader.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_serve_frontend():
    """Verify that root endpoint serves the HTML frontend."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Barcode Reader" in response.text
    assert "barcode-input" in response.text


def test_api_health():
    """Verify health check endpoint returns 200 and correct catalogue metrics."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == "BarcodeReader"
    assert data["categories_count"] == 8
    assert data["products_count"] == 16


def test_get_categories():
    """Verify categories endpoint returns all 8 categories."""
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 8

    # Verify expected categories are present
    category_names = [c["name"] for c in data]
    assert "Dress — Casual" in category_names
    assert "Dress — Party Wear" in category_names
    assert "Kurti — Cotton" in category_names
    assert "Category 4 — name to be confirmed" in category_names
    assert "Abaya" in category_names
    assert "Rental — Bridal" in category_names
    assert "Dress — Dress Material" in category_names
    assert "Dress — Ready Wear" in category_names

    # Check product counts
    for c in data:
        assert c["product_count"] == 2


def test_get_products():
    """Verify products endpoint returns all 16 products with resolved category names."""
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 16

    for prod in data:
        assert "id" in prod
        assert "barcode" in prod
        assert "name" in prod
        assert "category_id" in prod
        assert "category_name" in prod
        assert prod["category_name"] != "Unknown Category"


def test_scan_valid_barcode():
    """Verify scanning an existing barcode returns 200 and correct product details."""
    response = client.post("/api/scan", json={"barcode": "BR000003"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "PROD-003"
    assert data["barcode"] == "BR000003"
    assert data["name"] == "DEMO: Sequin Evening Cocktail Gown"
    assert data["category_id"] == 2
    assert data["category_name"] == "Dress — Party Wear"


def test_scan_valid_barcode_with_whitespace():
    """Verify scanning barcode with whitespace is trimmed and succeeds."""
    response = client.post("/api/scan", json={"barcode": "  BR000005  "})
    assert response.status_code == 200
    data = response.json()
    assert data["barcode"] == "BR000005"
    assert data["category_name"] == "Kurti — Cotton"


def test_scan_unknown_barcode():
    """Verify scanning an unregistered barcode returns 404 with clear message."""
    response = client.post("/api/scan", json={"barcode": "BR999999"})
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_scan_empty_barcode():
    """Verify submitting an empty barcode returns a validation error."""
    response = client.post("/api/scan", json={"barcode": ""})
    assert response.status_code in (400, 422)
    data = response.json()
    assert "detail" in data


def test_scan_whitespace_only_barcode():
    """Verify submitting whitespace-only barcode returns a validation error."""
    response = client.post("/api/scan", json={"barcode": "   "})
    assert response.status_code in (400, 422)
    data = response.json()
    assert "detail" in data


def test_scan_missing_field():
    """Verify submitting missing barcode field returns 422 unprocessable entity."""
    response = client.post("/api/scan", json={})
    assert response.status_code == 422


def test_api_recover_clean_image():
    """Verify /api/recover decodes a clean image and looks up catalog product."""
    import base64
    from pathlib import Path

    img_path = Path(__file__).parent / "test_images" / "valid_demo_br01.png"
    b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
    response = client.post("/api/recover", json={"image_data": f"data:image/png;base64,{b64}"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "decoded_normally"
    assert data["barcode"] == "BR000001"
    assert data["product_found"] is True
    assert data["product"]["id"] == "PROD-001"
    assert data["original_crop"].startswith("data:image/png;base64,")


def test_api_recover_skewed_image():
    """Verify /api/recover deskews and recovers tilted catalog barcode image."""
    import base64
    from io import BytesIO
    from pathlib import Path
    from PIL import Image

    img_path = Path(__file__).parent / "test_images" / "valid_demo_br01.png"
    im = Image.open(img_path)
    skewed = im.rotate(20, expand=True, fillcolor=255)
    buf = BytesIO()
    skewed.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    response = client.post("/api/recover", json={"image_data": f"data:image/png;base64,{b64}"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recovered_from_damaged_image"
    assert data["barcode"] == "BR000001"
    assert data["product_found"] is True
    assert data["product"]["id"] == "PROD-001"
    assert abs(data["skew_angle_deg"]) >= 10.0


def test_api_recover_invalid_payloads():
    """Verify /api/recover handles empty, malformed, and missing payloads cleanly with informative errors."""
    # Missing image_data
    r1 = client.post("/api/recover", json={})
    assert r1.status_code == 422
    assert "detail" in r1.json()

    # Empty image_data
    r2 = client.post("/api/recover", json={"image_data": "   "})
    assert r2.status_code == 400
    assert "empty" in r2.json()["detail"].lower()

    # Unparseable image_data
    r3 = client.post("/api/recover", json={"image_data": "invalid-base64-random-string"})
    assert r3.status_code == 400
    assert "could not parse" in r3.json()["detail"].lower()
