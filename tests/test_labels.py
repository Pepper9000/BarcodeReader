"""
Automated validation tests for Phase 2.5: Printable Demo Barcode Labels.

Validates that:
1. All 16 demo barcode labels exist as high-resolution PNGs.
2. Both printable PDF files (single-page 16-in-1 and 2-page large format) are generated.
3. Every generated PNG label is decoded by the vendored ZXing implementation.
4. Every decoded barcode value matches the exact expected string (BR000001 through BR000016).
5. Every decoded barcode value resolves to the correct product through /api/scan.
6. The PDF download endpoint /api/labels/pdf is functional.
"""

import json
from pathlib import Path
import subprocess
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.catalogue import default_catalogue
from scripts.generate_labels import generate_all_labels

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "generated" / "barcodes"
PNG_DIR = OUTPUT_DIR / "labels_png"
PRIMARY_PDF = OUTPUT_DIR / "demo_labels_a4.pdf"
LARGE_PDF = OUTPUT_DIR / "demo_labels_large_a4.pdf"
MANIFEST_FILE = OUTPUT_DIR / "MANIFEST.md"


@pytest.fixture(scope="session", autouse=True)
def ensure_labels_generated():
    """Ensure labels and PDFs are generated before running tests."""
    generate_all_labels()


def decode_png_with_zxing(image_path: Path) -> str:
    """Helper to decode a PNG label image using vendored ZXing via Node.js."""
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
    const bpp = 3; // RGB
    const stride = width * bpp + 1;
    const img = Buffer.alloc(width * height * bpp);

    for (let y = 0; y < height; y++) {
      const filter = raw[y * stride];
      const rowStart = y * stride + 1;
      const outStart = y * width * bpp;
      const prevOutStart = (y - 1) * width * bpp;
      for (let x = 0; x < width * bpp; x++) {
        const rawVal = raw[rowStart + x];
        const left = x >= bpp ? img[outStart + x - bpp] : 0;
        const up = y > 0 ? img[prevOutStart + x] : 0;
        const upleft = (y > 0 && x >= bpp) ? img[prevOutStart + x - bpp] : 0;
        let val = 0;
        if (filter === 0) val = rawVal;
        else if (filter === 1) val = (rawVal + left) & 0xff;
        else if (filter === 2) val = (rawVal + up) & 0xff;
        else if (filter === 3) val = (rawVal + Math.floor((left + up) / 2)) & 0xff;
        else if (filter === 4) {
          const p = left + up - upleft;
          const pa = Math.abs(p - left);
          const pb = Math.abs(p - up);
          const pc = Math.abs(p - upleft);
          let pr = left;
          if (pb < pa && pb <= pc) pr = up;
          else if (pc < pa) pr = upleft;
          val = (rawVal + pr) & 0xff;
        }
        img[outStart + x] = val;
      }
    }

    const luminances = new Uint8ClampedArray(width * height);
    for (let i = 0; i < width * height; i++) {
      const r = img[i * 3];
      const g = img[i * 3 + 1];
      const b = img[i * 3 + 2];
      luminances[i] = (r * 77 + g * 150 + b * 29) >> 8;
    }

    const hints = new Map();
    hints.set(zx.DecodeHintType.TRY_HARDER, true);
    hints.set(zx.DecodeHintType.POSSIBLE_FORMATS, [zx.BarcodeFormat.CODE_128]);

    const src = new zx.RGBLuminanceSource(luminances, width, height);
    const bm = new zx.BinaryBitmap(new zx.HybridBinarizer(src));
    const reader = new zx.MultiFormatReader();
    reader.setHints(hints);
    try {
      const res = reader.decode(bm);
      console.log(res.getText());
    } catch (e) {
      console.log('NOT_FOUND');
    }
    """
    result = subprocess.run(
        ["node", "-e", node_script, str(image_path)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_pdf_files_exist_and_non_empty():
    """Verify that both primary and large-format PDF label files are generated."""
    assert PRIMARY_PDF.exists(), f"Missing primary PDF: {PRIMARY_PDF}"
    assert PRIMARY_PDF.stat().st_size > 100_000, "Primary PDF size suspiciously small"

    assert LARGE_PDF.exists(), f"Missing large format PDF: {LARGE_PDF}"
    assert LARGE_PDF.stat().st_size > 200_000, "Large format PDF size suspiciously small"


def test_manifest_file_exists_and_complete():
    """Verify MANIFEST.md documents all 16 products."""
    assert MANIFEST_FILE.exists()
    content = MANIFEST_FILE.read_text(encoding="utf-8")
    for i in range(1, 17):
        code = f"BR{i:06d}"
        assert code in content


def test_all_16_png_labels_exist():
    """Verify all 16 product PNG files exist in generated/barcodes/labels_png/."""
    products = default_catalogue.get_products()
    assert len(products) == 16

    for prod in products:
        fn = f"{prod['barcode']}_{prod['id']}.png"
        fp = PNG_DIR / fn
        assert fp.exists(), f"Missing label PNG: {fp}"
        assert fp.stat().st_size > 5_000, f"Label file {fn} is too small"


@pytest.mark.parametrize(
    "product_index",
    list(range(16)),
)
def test_each_label_decodes_and_resolves_via_api(product_index):
    """
    For every one of the 16 products:
    1. Decode its generated PNG label using ZXing.
    2. Confirm decoded string exactly matches the expected barcode.
    3. Send decoded string to /api/scan and confirm product name, ID, and category match.
    """
    products = default_catalogue.get_products(resolve_categories=True)
    product = products[product_index]
    barcode = product["barcode"]
    prod_id = product["id"]

    label_file = PNG_DIR / f"{barcode}_{prod_id}.png"
    assert label_file.exists()

    decoded_code = decode_png_with_zxing(label_file)
    assert decoded_code == barcode, f"Decoded '{decoded_code}' does not match expected '{barcode}'"

    # Send to API /api/scan
    response = client.post("/api/scan", json={"barcode": decoded_code})
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == prod_id
    assert data["barcode"] == barcode
    assert data["name"] == product["name"]
    assert data["category_name"] == product["category_name"]
    assert data["category_id"] == product["category_id"]


def test_api_download_labels_pdf():
    """Verify endpoint /api/labels/pdf successfully serves the printable A4 PDF."""
    response = client.get("/api/labels/pdf")
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/pdf"
    assert len(response.content) > 100_000
