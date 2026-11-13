"""
Automated validation tests for Phase 3: Live Mobile Camera Scanning.

Validates that:
1. All required HTML5 camera elements, controls, and fallbacks are present in index.html.
2. The video element contains mobile-friendly attributes (playsinline, muted, autoplay).
3. The API health check confirms Phase 3 readiness.
4. Camera stream security constraints (HTTPS / local context handling) are in place.
5. Camera track cleanup and duplicate prevention mechanisms are implemented in client scripts.
6. Decoded barcodes from camera streams successfully resolve against the /api/scan endpoint.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.catalogue import default_catalogue

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = BASE_DIR / "app" / "static" / "index.html"
APP_JS = BASE_DIR / "app" / "static" / "app.js"
STYLE_CSS = BASE_DIR / "app" / "static" / "style.css"


def test_api_health_phase3():
    """Verify health endpoint reports Phase 3."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["phase"] == 3
    assert data["categories_count"] == 8
    assert data["products_count"] == 16


def test_camera_html_elements_present():
    """Verify that all Phase 3 camera UI controls and containers exist in index.html."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # Tab and panels
    assert 'id="tab-camera-btn"' in html
    assert 'id="panel-camera"' in html

    # Controls
    assert 'id="camera-start-btn"' in html
    assert 'id="camera-stop-btn"' in html
    assert 'id="camera-device-select"' in html
    assert 'id="camera-torch-btn"' in html

    # Video & Viewfinder
    assert 'id="camera-video"' in html
    assert 'playsinline' in html
    assert 'muted' in html
    assert 'autoplay' in html
    assert 'id="camera-viewfinder-container"' in html
    assert 'id="viewfinder-frame"' in html
    assert 'id="viewfinder-laser"' in html
    assert 'id="camera-status-chip"' in html

    # Post-scan resume controls
    assert 'id="camera-scan-success-bar"' in html
    assert 'id="camera-resume-btn"' in html

    # Fallback and Security Info
    assert 'id="camera-fallback-card"' in html
    assert 'id="btn-fallback-manual"' in html
    assert 'id="btn-fallback-upload"' in html
    assert "Mobile Security Notice" in html


def test_camera_js_implementation_rules():
    """Verify that app.js follows strict mobile and security rules."""
    js_content = APP_JS.read_text(encoding="utf-8")

    # 1. Environment rear camera preference
    assert 'facingMode: { ideal: "environment" }' in js_content

    # 2. Camera permission requested only on user action
    assert 'cameraStartBtn.addEventListener("click", startCamera)' in js_content

    # 3. Duplicate request prevention (paused state on detection)
    assert "isScanningPaused = true" in js_content

    # 4. Stream cleanup when switching tabs
    assert "stopCamera()" in js_content
    assert "track.stop()" in js_content

    # 5. Secure context / HTTPS check
    assert "window.isSecureContext" in js_content or "location.hostname" in js_content

    # 6. Audio acoustic feedback
    assert "playSuccessBeep" in js_content

    # 7. No backend image upload (frames processed in client canvas)
    assert "drawImage(cameraVideo" in js_content


def test_camera_css_styling_present():
    """Verify style.css contains styling for camera components and animations."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")
    assert ".viewfinder-container" in css_content
    assert ".viewfinder-frame" in css_content
    assert ".viewfinder-laser" in css_content
    assert "@keyframes scanLaser" in css_content
    assert ".camera-toolbar" in css_content
    assert ".camera-success-bar" in css_content


def test_camera_scan_api_resolution():
    """Verify that camera-decoded barcodes query /api/scan and resolve product."""
    products = default_catalogue.get_products()
    for prod in [products[0], products[4], products[8], products[15]]:
        response = client.post("/api/scan", json={"barcode": prod["barcode"]})
        assert response.status_code == 200
        data = response.json()
        assert data["barcode"] == prod["barcode"]
        assert data["name"] == prod["name"]
        assert data["category_name"] == prod["category_name"]
