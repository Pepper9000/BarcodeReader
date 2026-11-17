"""
Tests for UI features, frontend DOM elements, and safety contracts.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app, STATIC_DIR, PENDING_SUBMISSIONS_FILE

client = TestClient(app)
INDEX_HTML = STATIC_DIR / "index.html"
APP_JS = STATIC_DIR / "app.js"
STYLE_CSS = STATIC_DIR / "style.css"


@pytest.fixture(autouse=True)
def clean_pending():
    """Ensure pending submissions are reset."""
    PENDING_SUBMISSIONS_FILE.write_text("[]", encoding="utf-8")
    yield
    PENDING_SUBMISSIONS_FILE.write_text("[]", encoding="utf-8")


def test_ui_elements_for_new_features_present():
    """Verify index.html contains all required DOM containers and controls for new features."""
    html = INDEX_HTML.read_text(encoding="utf-8")

    # Header action buttons
    assert 'id="btn-open-catalog"' in html
    assert 'id="btn-open-saved"' in html
    assert 'id="btn-open-batch"' in html
    assert 'id="btn-open-compare"' in html

    # Badges
    assert 'id="saved-count-badge"' in html
    assert 'id="batch-count-badge"' in html
    assert 'id="compare-count-badge"' in html

    # Batch Mode toggle
    assert 'id="batch-mode-checkbox"' in html

    # Persistent barcode display & source badge
    assert 'id="detected-barcode-display"' in html
    assert 'id="decoding-source-badge"' in html

    # State panels
    assert 'id="product-looking-up"' in html
    assert 'id="product-not-found"' in html
    assert 'id="product-invalid-code"' in html
    assert 'id="product-lookup-error"' in html
    assert 'id="product-details"' in html

    # Transparency card
    assert 'id="recovery-transparency-card"' in html
    assert 'id="transparency-original-img"' in html
    assert 'id="transparency-enhanced-img"' in html
    assert "Transparency Notice" in html

    # Modals
    assert 'id="modal-submission"' in html
    assert 'id="modal-comparison"' in html
    assert 'id="modal-saved"' in html
    assert 'id="modal-batch"' in html
    assert 'id="modal-catalog"' in html

    # Mobile camera snapshot recovery
    assert 'id="camera-snap-recover-btn"' in html


def test_js_safety_and_feature_contracts():
    """Verify app.js implements the safety rules and feature contracts."""
    js = APP_JS.read_text(encoding="utf-8")

    # 1. Monotonic request sequencing to prevent race conditions
    assert "currentLookupRequestId" in js
    assert "activeAbortController" in js

    # 2. Reopening scan history
    assert "li.addEventListener(\"click\"" in js
    assert "performScan(item.barcode" in js

    # 3. LocalStorage persistence for saved products with disclaimer
    assert "barcodereader_saved_products" in js
    assert "device/browser-specific" in js or "local browser storage" in js

    # 4. Product comparison with explicit "Not available" label
    assert "Not available" in js

    # 5. Non-inventory batch scanning
    assert "batchSession" in js
    assert "existing.count += 1" in js

    # 6. Submission administrative review notice
    assert "pending administrative review" in js or "administrative moderation" in js


def test_missing_product_submission_flow():
    """Verify that an unknown barcode lookup returns 404 and submission intake safely rejects with 503."""
    test_code = "9876543210985"
    # Ensure not in catalog
    scan_res = client.post("/api/scan", json={"barcode": test_code})
    assert scan_res.status_code == 404

    # Submit attempt returns 503 Service Unavailable
    sub_res = client.post(
        "/api/submissions",
        json={
            "barcode": test_code,
            "name": "Handmade Silk Scarf",
            "category_id": 1,
            "notes": "Verified from test tag",
        },
    )
    assert sub_res.status_code == 503
    assert "temporarily disabled" in sub_res.json()["detail"].lower()

    # Confirm it does NOT appear in public catalog
    products = client.get("/api/products").json()
    assert all(p["barcode"] != test_code for p in products)
    assert len(products) == 16
