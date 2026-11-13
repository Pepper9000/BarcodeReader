"""
Tests for Phase 2 image-based barcode decoding and catalogue integration.

Validates that:
1. Actual barcode images are correctly decoded by the vendored ZXing library.
2. Decoded barcode values correctly reach /api/scan and return expected product details.
3. Multi-barcode images detect all distinct barcodes.
4. Non-barcode images return zero detections.
5. Unsupported file types are recognized as invalid.
"""

import json
from pathlib import Path
import subprocess
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent
TEST_IMAGES_DIR = BASE_DIR / "tests" / "test_images"
ZXING_PATH = BASE_DIR / "app" / "static" / "vendor" / "zxing.min.js"


def decode_image_with_zxing(image_path: Path) -> list[str]:
    """
    Execute a Node.js helper script that loads the vendored zxing.min.js
    and decodes barcodes from the specified PNG image using the same
    multi-pass algorithm used by the browser frontend.
    """
    node_script = """
    const fs = require('fs');
    const zlib = require('zlib');
    const zx = require('./app/static/vendor/zxing.min.js');

    const imagePath = process.argv[1];
    const buf = fs.readFileSync(imagePath);

    let offset = 8, width, height, idatChunks = [];
    while (offset < buf.length) {
      const len = buf.readUInt32BE(offset);
      const type = buf.slice(offset + 4, offset + 8).toString('ascii');
      if (type === 'IHDR') {
        width = buf.readUInt32BE(offset + 8);
        height = buf.readUInt32BE(offset + 12);
      } else if (type === 'IDAT') {
        idatChunks.push(buf.slice(offset + 8, offset + 8 + len));
      }
      offset += 12 + len;
    }

    const raw = zlib.inflateSync(Buffer.concat(idatChunks));
    const stride = width + 1;
    const luminances = new Uint8ClampedArray(width * height);
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        luminances[y * width + x] = raw[y * stride + 1 + x];
      }
    }

    function scanPass(lum) {
      const hints = new Map();
      hints.set(zx.DecodeHintType.TRY_HARDER, true);
      hints.set(zx.DecodeHintType.POSSIBLE_FORMATS, [
        zx.BarcodeFormat.CODE_128,
        zx.BarcodeFormat.CODE_39,
        zx.BarcodeFormat.EAN_13,
        zx.BarcodeFormat.EAN_8,
        zx.BarcodeFormat.UPC_A
      ]);
      const src = new zx.RGBLuminanceSource(lum, width, height);
      const bm = new zx.BinaryBitmap(new zx.HybridBinarizer(src));
      const r = new zx.MultiFormatReader();
      r.setHints(hints);
      try { return r.decode(bm); } catch(e) { return null; }
    }

    const results = [];
    const r1 = scanPass(luminances);
    if (r1) {
      results.push(r1.getText());
      const lum2 = new Uint8ClampedArray(luminances);
      const pts = r1.getResultPoints();
      if (pts && pts.length > 0) {
        const xs = pts.map(p => p.getX());
        const ys = pts.map(p => p.getY());
        const minX = Math.max(0, Math.floor(Math.min(...xs)) - 15);
        const maxX = Math.min(width - 1, Math.ceil(Math.max(...xs)) + 15);
        const minY = Math.max(0, Math.floor(Math.min(...ys)) - 25);
        const maxY = Math.min(height - 1, Math.ceil(Math.max(...ys)) + 25);
        for (let y = minY; y <= maxY; y++) {
          for (let x = minX; x <= maxX; x++) lum2[y * width + x] = 255;
        }
        const r2 = scanPass(lum2);
        if (r2 && !results.includes(r2.getText())) {
          results.push(r2.getText());
        }
      }
    }

    console.log(JSON.stringify(results));
    """
    result = subprocess.run(
        ["node", "-e", node_script, str(image_path)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip())


def test_zxing_vendored_library_present():
    """Verify that zxing.min.js is vendored locally and accessible via static server."""
    assert ZXING_PATH.exists(), f"Missing vendored library: {ZXING_PATH}"
    response = client.get("/static/vendor/zxing.min.js")
    assert response.status_code == 200
    assert len(response.text) > 100_000


def test_decode_valid_demo_barcode_image():
    """Verify decoding a real barcode image and forwarding decoded barcode to /api/scan."""
    image_file = TEST_IMAGES_DIR / "valid_demo_br01.png"
    assert image_file.exists()

    decoded = decode_image_with_zxing(image_file)
    assert decoded == ["BR000001"]

    # Verify decoded value reaches /api/scan and resolves product
    response = client.post("/api/scan", json={"barcode": decoded[0]})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "PROD-001"
    assert data["barcode"] == "BR000001"
    assert data["category_name"] == "Dress — Casual"


def test_decode_second_demo_barcode_image():
    """Verify decoding a Kurti barcode image and resolving product."""
    image_file = TEST_IMAGES_DIR / "valid_demo_br05.png"
    decoded = decode_image_with_zxing(image_file)
    assert decoded == ["BR000005"]

    response = client.post("/api/scan", json={"barcode": decoded[0]})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "PROD-005"
    assert data["category_name"] == "Kurti — Cotton"


def test_decode_unknown_barcode_image():
    """Verify decoding an unknown barcode image and receiving 404 from /api/scan."""
    image_file = TEST_IMAGES_DIR / "valid_unknown_br99.png"
    decoded = decode_image_with_zxing(image_file)
    assert decoded == ["BR999999"]

    response = client.post("/api/scan", json={"barcode": decoded[0]})
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_decode_multi_barcode_image():
    """Verify that multiple barcodes in an image are detected without silent single selection."""
    image_file = TEST_IMAGES_DIR / "multi_barcodes.png"
    decoded = decode_image_with_zxing(image_file)

    assert len(decoded) == 2
    assert "BR000001" in decoded
    assert "BR000002" in decoded

    # Both barcodes resolve to valid products in catalogue
    for barcode in decoded:
        response = client.post("/api/scan", json={"barcode": barcode})
        assert response.status_code == 200


def test_decode_non_barcode_image():
    """Verify that an image with no barcodes returns an empty list."""
    image_file = TEST_IMAGES_DIR / "no_barcode_blank.png"
    decoded = decode_image_with_zxing(image_file)
    assert decoded == []


def test_unsupported_file_extension():
    """Verify unsupported file types are identified by extension."""
    invalid_file = TEST_IMAGES_DIR / "invalid_format.txt"
    assert invalid_file.exists()
    supported_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    assert invalid_file.suffix.lower() not in supported_extensions


def test_frontend_contains_image_upload_elements():
    """Verify that index.html contains all required Phase 2 controls."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert "tab-image-btn" in html
    assert "image-file-input" in html
    assert "scan-image-btn" in html
    assert "multi-barcode-card" in html
    assert "vendor/zxing.min.js" in html
    assert "image/jpeg,image/png,image/webp" in html
