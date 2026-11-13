# BarcodeReader — Barcode-Based Product Identification and Classification

An academic project for **Logic Design and Microprocessor (LDAM)** implementing a complete barcode identification system.

- **Phase 1:** Core software foundation (FastAPI backend, JSON product catalogue, dynamic category resolution, USB keyboard-wedge barcode scanner terminal, automated tests).
- **Phase 2:** Client-side image-based barcode scanning (upload JPG, JPEG, PNG, WEBP from mobile gallery or filesystem, client-side ZXing decoding, multi-barcode detection with interactive selection, error handling).
- **Phase 2.5:** Printable Code 128 barcode labels and A4 sheets for all 16 demo products with barcode verification.
- **Phase 3:** Live mobile phone camera scanning (real-time viewfinder, central ROI decoding, dual-engine ZXing / BarcodeDetector, duplicate suppression, mobile Chrome optimization).
- **Phase 4:** Production readiness & public HTTPS deployment preparation (zero hardcoded hosts, dynamic `$PORT` binding on `0.0.0.0`, working-directory-independent paths, `Procfile`, `render.yaml`, regression suite).

---

## Technology Stack

- **Backend:** Python 3.11+ / FastAPI
- **Server:** Uvicorn ASGI Server
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (zero external framework dependencies)
- **Barcode Decoding Engine:** Vendored ZXing (`@zxing/library`) running client-side with native `BarcodeDetector` dual-engine fallback
- **Data Storage:** JSON Files (`app/data/categories.json`, `app/data/products.json`)
- **Testing:** Pytest & HTTPX TestClient (61 passing tests)
- **Deployment:** Render / Railway / PaaS (`Procfile`, `render.yaml`, `$PORT` compatible)

---

## Project Structure

```text
BarcodeReader/
├── .gitignore                   # Git ignore patterns for Python, venv, and caches
├── .pytest_cache/               # Pytest cache directory
├── .venv/                       # Python virtual environment
├── LDAM_MAPPING.md              # LDAM hardware architecture & transition mapping
├── Procfile                     # Production process configuration for PaaS (Render / Railway / Heroku)
├── render.yaml                  # Render Blueprint Infrastructure-as-Code specification
├── pytest.ini                   # Pytest configuration (pythonpath and testpaths)
├── README.md                    # Project documentation, deployment and setup guide
├── requirements.txt             # Production and development dependencies
├── app/
│   ├── __init__.py              # Application package initializer
│   ├── catalogue.py             # Catalogue manager, data validation, and lookup engine
│   ├── main.py                  # FastAPI application, route handlers, and production entrypoint
│   ├── data/
│   │   ├── categories.json      # Category catalogue (8 initial categories)
│   │   └── products.json        # Product catalogue (16 demo products)
│   └── static/
│       ├── app.js               # Frontend logic, camera scanner, ZXing image scanner & history
│       ├── index.html           # 3-in-1 web interface (Manual / Image Upload / Live Camera)
│       ├── style.css            # Clean, responsive styling with mobile support
│       ├── samples/             # Real sample barcode images for quick testing
│       └── vendor/
│           └── zxing.min.js     # Self-contained, offline ZXing barcode library
├── generated/
│   └── barcodes/                # Printable labels & PDF exports
│       ├── demo_labels_a4.pdf   # 16-in-1 A4 printable PDF sheet (100% scale)
│       ├── demo_labels_large_a4.pdf # Large-format 2-page A4 PDF sheet
│       ├── MANIFEST.md          # Index of generated labels
│       └── labels_png/          # 16 individual high-res PNG label cards
├── scripts/
│   └── generate_labels.py       # Standalone label & PDF generation utility (cross-platform fonts)
└── tests/
    ├── __init__.py              # Test package initializer
    ├── test_api.py              # FastAPI endpoint integration tests
    ├── test_camera.py           # Live camera integration, UI and JS contracts
    ├── test_catalogue.py        # Unit tests for lookup logic & data integrity
    ├── test_image_decoding.py   # Automated tests for image decoding & /api/scan
    ├── test_labels.py           # Automated tests for label decoding & PDF export
    ├── test_production.py       # Production readiness, path independence, Procfile, & asset tests
    └── test_images/             # Test suite barcode image files
```

---

## Initial Product Categories

Category data is maintained strictly in `app/data/categories.json` and resolved dynamically:

1. **Dress — Casual**
2. **Dress — Party Wear**
3. **Kurti — Cotton**
4. **Category 4 — name to be confirmed**
5. **Abaya**
6. **Rental — Bridal**
7. **Dress — Dress Material**
8. **Dress — Ready Wear**

---

## Windows PowerShell Setup Guide

Follow these steps from the root directory (`C:\BarcodeReader`):

### 1. Activate Virtual Environment

In PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

> **Note:** If script execution is disabled on PowerShell, allow it for the current process:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
> ```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Run the Application

Start the FastAPI application with Uvicorn:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, access the web interface in your browser:

- **Frontend Application:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive API Docs (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## Scanning Modes

The interface provides three dedicated scanning modes accessible via tabs:

### Mode 1: Manual / USB Scanner Terminal
- Designed for USB handheld barcode scanners operating in **HID Keyboard Wedge Mode**.
- Input field maintains automatic focus and intercepts the scanner's trailing `Enter` (CR/LF) keypress.
- Provides quick-fill demo chips (`BR000001` through `BR000015`) for testing without hardware.

### Mode 2: Image-Based Barcode Scanning
- **File Upload:** Click or drag & drop any JPG, JPEG, PNG, or WEBP image.
- **Mobile Support:** Tap the upload area on a mobile browser to choose directly from the phone photo gallery or file manager.
- **Image Preview:** Displays the loaded image thumbnail, filename, pixel dimensions, and file size.
- **Client-Side Decoding:** Decodes barcodes entirely within the browser using the vendored ZXing library with `TRY_HARDER` multi-pass heuristics. No image is uploaded to external servers.
- **Supported Formats:** Code 128, EAN-13, EAN-8, UPC-A, UPC-E, Code 39, ITF, QR Code, Data Matrix.
- **Multi-Barcode Detection:** If an image contains multiple barcodes, the system identifies all distinct values and presents an interactive selection list so the user can choose which product to identify.
- **Large Image Handling:** Canvas downscaling prevents memory exhaustion on high-resolution smartphone photos (up to 4K+) while preserving barcode contrast.
- **Sample Images:** Clickable sample chips allow instant testing with pre-generated barcode images (`valid_demo_br01.png`, `multi_barcodes.png`, `no_barcode_blank.png`).

### Mode 3: Live Mobile Camera Scanning (Phase 3)
- **On-Demand Permission:** Camera permission is requested only when the user explicitly clicks **Start Camera**.
- **Mobile Rear Camera Preference:** Prioritizes `facingMode: { ideal: "environment" }` on Android Chrome and iOS devices.
- **Interactive Viewfinder:** Shows real-time video preview with an animated target reticle and laser guide.
- **Optimized Central ROI:** Decodes the central targeting region at high frame rates while keeping CPU and battery consumption low.
- **Duplicate Prevention:** On detection, scanning pauses instantly, the reticle flashes emerald green, a confirmation beep plays, and a **"Scan Another Barcode"** button appears.
- **Resource Management:** Switching tabs or clicking **Stop Camera** immediately terminates all camera tracks and stops CPU processing.
- **HTTPS & Security Note:** Browsers restrict `navigator.mediaDevices.getUserMedia` to secure origins (`https://` or `http://localhost`). When testing from a mobile phone over a local Wi-Fi IP, access the app via HTTPS, configure Chrome's port-forwarding (`chrome://inspect`), or use the **Upload Image** mode as a fallback.

---

## Printable Demo Barcode Labels (Phase 2.5)

Printable barcode labels are generated for all 16 demo products using `app/catalogue.py` as the single source of truth.

### Generated Label Files
All output files are saved in the [`generated/barcodes/`](file:///c:/BarcodeReader/generated/barcodes/) directory:
- **Primary A4 Sheet (16-in-1):** [`generated/barcodes/demo_labels_a4.pdf`](file:///c:/BarcodeReader/generated/barcodes/demo_labels_a4.pdf) — All 16 labels arranged in a clean 2×8 grid on a single A4 page.
- **Large Format A4 Sheet (8-in-1 × 2 Pages):** [`generated/barcodes/demo_labels_large_a4.pdf`](file:///c:/BarcodeReader/generated/barcodes/demo_labels_large_a4.pdf) — Extra-tall barcodes for product boxes and long-range scanning.
- **Individual High-Resolution PNGs:** [`generated/barcodes/labels_png/`](file:///c:/BarcodeReader/generated/barcodes/labels_png/) — 16 standalone PNG cards (`BR000001_PROD-001.png` through `BR000016_PROD-016.png`).
- **Catalogue Manifest:** [`generated/barcodes/MANIFEST.md`](file:///c:/BarcodeReader/generated/barcodes/MANIFEST.md) — Reference table of all generated labels.

### Regenerating Labels
To re-generate all PNG labels and PDFs at any time:
```powershell
python scripts/generate_labels.py
```

### Printing, Cutting & Testing Instructions

1. **Download / Open the PDF:**
   - Either open [`generated/barcodes/demo_labels_a4.pdf`](file:///c:/BarcodeReader/generated/barcodes/demo_labels_a4.pdf), or click the **"Print Labels (A4 PDF)"** badge in the web application header, or visit `http://127.0.0.1:8000/api/labels/pdf`.
2. **Print Settings (Crucial for Barcode Accuracy):**
   - Paper Size: **A4** (210 × 297 mm).
   - Scale: **100% / Actual Size**. Do **NOT** use "Fit to Printable Area" or "Shrink to Fit", as scaling can distort narrow barcode bar widths.
   - Quality: Standard or High on normal white paper or sticker paper.
3. **Cutting:**
   - Cut along the light-gray dashed guidelines with scissors or a paper trimmer. Each label includes a category header badge, product ID, product name, Code 128 barcode, and human-readable text.
4. **Testing the Labels:**
   - **Image Upload:** Take a picture of any printed label with your phone or webcam, upload it to the **Upload Image** tab in the web interface, and click **Scan Image for Barcode**.
   - **Manual/USB Scanner:** Point a USB barcode scanner at any printed label to instantly test hardware scanning.

---

## Phase 4: Production Deployment Guide (HTTPS & Cloud PaaS)

The application is architected as a lightweight, single-service FastAPI solution that serves both the JSON REST API and the static frontend UI.

### Why Single-Service PaaS (Render / Railway / Fly.io)?
1. **Zero Architecture Drift:** No need to manage separate frontend hosting (Vercel/Netlify) and backend servers.
2. **Built-in Automatic HTTPS:** Required by modern browsers for `navigator.mediaDevices.getUserMedia` (Live Mobile Camera scanning).
3. **Dynamic Port Binding:** Automatically detects the cloud provider's `$PORT` environment variable and binds to `0.0.0.0`.
4. **Path-Independent Resolution:** All catalogue files, static assets, and generated label PDFs resolve relative to source files rather than working directories.
5. **On-Demand PDF Generation Fallback:** If the PDF label sheet is missing on a fresh container build, `/api/labels/pdf` automatically generates it on the fly.
6. **No External CDNs or Secrets:** The ZXing barcode engine is vendored locally, eliminating external network dependencies or tracking.

---

### Production Start Commands

#### Standard Cloud PaaS (via Procfile or Dashboard)
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### Build Command
```bash
pip install -r requirements.txt && python scripts/generate_labels.py
```

#### Local Fallback
When `$PORT` is not defined in the environment, the server defaults to port `8000`:
```bash
python -m app.main
```

---

### Step-by-Step Deployment on Render (Recommended)

1. **Push your code to GitHub / GitLab:**
   ```bash
   git init
   git add .
   git commit -m "feat: complete Phase 4 production readiness"
   git remote add origin https://github.com/<your-username>/barcodereader.git
   git push -u origin main
   ```

2. **Deploy via Render Blueprint (One-Click):**
   - In your Render Dashboard, click **New +** > **Blueprint**.
   - Connect your `barcodereader` repository.
   - Render automatically detects `render.yaml` and configures:
     - **Service Type:** Web Service (Python 3.11)
     - **Build Command:** `pip install -r requirements.txt && python scripts/generate_labels.py`
     - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     - **Auto-deploy:** On git push
   - Click **Apply**.

3. **Deploy via Render Manual Web Service (Alternative):**
   - Click **New +** > **Web Service**.
   - Connect your repository.
   - Set **Runtime** to `Python 3`.
   - Set **Build Command** to: `pip install -r requirements.txt && python scripts/generate_labels.py`
   - Set **Start Command** to: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Click **Deploy Web Service**.

4. **Verify Deployment:**
   - Once deployed, Render provisions a secure URL (e.g. `https://barcodereader-xyz.onrender.com`).
   - Open `/api/health` to confirm catalogue metrics.
   - Open `/` to interact with the full web application.

---

### Testing Live Camera on a Physical Mobile Device via Public HTTPS

1. Open the public HTTPS deployment link (`https://<your-subdomain>.onrender.com`) on your smartphone (Android Chrome or iOS Safari).
2. Because the connection is authenticated over valid HTTPS SSL/TLS (`window.isSecureContext === true`), the browser permits camera access.
3. Switch to the **Live Camera** tab.
4. Tap **Start Camera** — when prompted, tap **Allow** for camera access.
5. Point the phone at any printed demo label (or another screen displaying the label from [`generated/barcodes/labels_png/`](file:///c:/BarcodeReader/generated/barcodes/labels_png/)).
6. The viewfinder reticle flashes green, a confirmation tone sounds, and the decoded product and category details display immediately.

---

## Executing the Test Suite

Run the full automated test suite using pytest:

```powershell
pytest
```

For verbose output with each individual test case:

```powershell
pytest -v
```

The test suite validates 61 test cases across 6 test modules:
- **`tests/test_api.py` (10 tests):** Barcode lookups, whitespace handling, 404 responses for unknown codes, 400/422 validation errors, category listings, and health metrics.
- **`tests/test_catalogue.py` (13 tests):** Core catalogue integrity, category mapping resolution, unique barcode assertions, unique product ID assertions, and file error handling.
- **`tests/test_image_decoding.py` (8 tests):** Vendored ZXing library delivery, real barcode image decoding (`valid_demo_br01.png`, `valid_demo_br05.png`, `valid_unknown_br99.png`), multi-barcode detection (`multi_barcodes.png`), non-barcode rejection (`no_barcode_blank.png`), unsupported file type rejection, and UI controls presence.
- **`tests/test_labels.py` (20 tests):** End-to-end verification that all 16 generated label images decode correctly and map to the exact expected products and categories via `/api/scan`, plus PDF integrity.
- **`tests/test_camera.py` (5 tests):** Live camera DOM controls, video feed elements, switching tab listeners, JavaScript security guards (`isSecureContext`), and CSS reticle styling.
- **`tests/test_production.py` (5 tests):** Static asset delivery via FastAPI mounts, zero hardcoded API endpoints, `Procfile` command validation, `render.yaml` configuration, and dynamic label PDF regeneration on demand.

---

## Hardware Architecture & Future Roadmap

For comprehensive documentation on how software concepts map to microcontroller hardware (UART communication, circular FIFO buffers, Finite State Machines, and LCD/LED actuation), refer to [LDAM_MAPPING.md](file:///c:/BarcodeReader/LDAM_MAPPING.md).
