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
