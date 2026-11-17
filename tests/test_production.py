"""
Tests for Phase 4: Production readiness and deployment preparation.
"""

import os
import re
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app, STATIC_DIR

REPO_ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app)


def test_static_assets_accessible():
    """Verify core static assets are accessible via FastAPI mount in production."""
    # CSS
    css_res = client.get("/static/style.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers.get("content-type", "")
    assert len(css_res.content) > 100

    # Main JS
    js_res = client.get("/static/app.js")
    assert js_res.status_code == 200
    assert "javascript" in js_res.headers.get("content-type", "")
    assert "api/scan" in js_res.text

    # Vendored ZXing
    zxing_res = client.get("/static/vendor/zxing.min.js")
    assert zxing_res.status_code == 200
    assert "javascript" in zxing_res.headers.get("content-type", "")
    assert len(zxing_res.content) > 100_000


def test_no_hardcoded_api_endpoints_in_frontend():
    """Verify that frontend assets use relative URLs and do not hardcode localhost:port in fetch calls."""
    js_file = STATIC_DIR / "app.js"
    html_file = STATIC_DIR / "index.html"

    # Check that no fetch or url target points to http://localhost or http://127.0.0.1
    forbidden_patterns = [
        re.compile(r"fetch\s*\(\s*['\"`]https?://(?:localhost|127\.0\.0\.1)", re.IGNORECASE),
        re.compile(r"action\s*=\s*['\"`]https?://(?:localhost|127\.0\.0\.1)", re.IGNORECASE),
        re.compile(r"href\s*=\s*['\"`]https?://(?:localhost|127\.0\.0\.1)", re.IGNORECASE),
        re.compile(r"src\s*=\s*['\"`]https?://(?:localhost|127\.0\.0\.1)", re.IGNORECASE),
    ]

    for file_path in [js_file, html_file]:
        content = file_path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            matches = pattern.findall(content)
            assert not matches, f"Found hardcoded API endpoint match {matches} in {file_path.name}"


def test_procfile_present_and_valid():
    """Verify Procfile is present at repository root with correct uvicorn command."""
    procfile = REPO_ROOT / "Procfile"
    assert procfile.exists(), f"Procfile must exist at {procfile}"
    content = procfile.read_text(encoding="utf-8").strip()
    assert "uvicorn app.main:app" in content
    assert "--host 0.0.0.0" in content
    assert "--port $PORT" in content


def test_render_yaml_present_and_valid():
    """Verify render.yaml exists and defines web service, build and start commands."""
    render_file = REPO_ROOT / "render.yaml"
    assert render_file.exists(), f"render.yaml must exist at {render_file}"
    content = render_file.read_text(encoding="utf-8")
    assert "type: web" in content
    assert "name: barcodereader" in content
    assert "runtime: python" in content
    assert "pip install -r requirements.txt" in content
    assert "uvicorn app.main:app --host 0.0.0.0 --port $PORT" in content


def test_pdf_endpoint_regenerates_if_missing():
    """Verify /api/labels/pdf endpoint returns 200 and application/pdf."""
    res = client.get("/api/labels/pdf")
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/pdf"
    assert int(res.headers.get("content-length", 0)) > 1000


def test_favicon_endpoints_accessible():
    """Verify that /favicon.ico and static favicon assets are served correctly."""
    # Root favicon
    root_fav = client.get("/favicon.ico")
    assert root_fav.status_code == 200
    assert "image" in root_fav.headers.get("content-type", "").lower()
    assert len(root_fav.content) > 500

    # Static PNG favicon
    png_fav = client.get("/static/favicon-32x32.png")
    assert png_fav.status_code == 200
    assert "image/png" in png_fav.headers.get("content-type", "").lower()
    assert len(png_fav.content) > 500

    # HTML contains link tags for favicons
    html_res = client.get("/")
    assert html_res.status_code == 200
    assert 'rel="icon"' in html_res.text
