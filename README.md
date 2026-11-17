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
│       ├── favicon.ico          # Multi-resolution favicon (16x16, 32x32, 48x48)
│       ├── favicon-32x32.png    # Retina 32x32 PNG favicon
│       ├── favicon-16x16.png    # Standard 16x16 PNG favicon
│       ├── apple-touch-icon.png # iOS home screen icon (180x180)
│       ├── icon-192.png / icon-512.png # PWA icons
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
│   ├── evaluate_recovery.py     # Evaluation harness for damaged EAN-13 recovery
│   ├── generate_favicon.py      # Favicon & multi-resolution app icon generator
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

The test suite validates 83 test cases across 9 test modules:
- **`tests/test_api.py` (10 tests):** Barcode lookups, whitespace handling, 404 responses for unknown codes, 400/422 validation errors, category listings, and health metrics.
- **`tests/test_catalogue.py` (13 tests):** Core catalogue integrity, category mapping resolution, unique barcode assertions, unique product ID assertions, and file error handling.
- **`tests/test_image_decoding.py` (8 tests):** Vendored ZXing library delivery, real barcode image decoding (`valid_demo_br01.png`, `valid_demo_br05.png`, `valid_unknown_br99.png`), multi-barcode detection (`multi_barcodes.png`), non-barcode rejection (`no_barcode_blank.png`), unsupported file type rejection, and UI controls presence.
- **`tests/test_labels.py` (20 tests):** End-to-end verification that all 16 generated label images decode correctly and map to the exact expected products and categories via `/api/scan`, plus PDF integrity.
- **`tests/test_camera.py` (5 tests):** Live camera DOM controls, video feed elements, switching tab listeners, JavaScript security guards (`isSecureContext`), and CSS reticle styling.
- **`tests/test_production.py` (6 tests):** Static asset delivery via FastAPI mounts, `/favicon.ico` root route and HTML link tags, zero hardcoded API endpoints, `Procfile` command validation, `render.yaml` configuration, and dynamic label PDF regeneration on demand.
- **`tests/test_recovery.py` (10 tests):** Check digit math, EAN-13 validation, standard ZXing fallback, recovery of low contrast, fading, skew, scratches, smudges, and abstention on blank/noise.
- **`tests/test_submissions.py` (6 tests):** Hardened submission intake returning 503 Service Unavailable, removal of public GET submissions queue, non-leakage of pending counts in catalog overview, disk data preservation, catalog isolation, and `/api/recover` endpoint.
- **`tests/test_ui_features.py` (3 tests):** HTML DOM controls for all features, JavaScript contracts for request sequencing, comparison "Not available" flags, non-inventory batching, and disabled submission safety handling.

---

## Safe Damaged EAN-13 Barcode Recovery Pipeline

### Technical Contribution & Research Scope

This project implements and evaluates a **structure-aware safe recovery pipeline** for damaged EAN-13 barcodes integrated directly into the application.

> **Research Question:**  
> *"For EAN-13 barcodes damaged by fading, scratches, smudges, low contrast, or skew, can a structure-aware recovery pipeline improve exact product-code recovery over a standard decoder without increasing false product identifications?"*

Existing literature documents degraded 1D barcode signal recovery. This project does not claim to be the first barcode-repair system, nor does it claim universal recovery of every damaged barcode. Rather, it implements a safe, deterministic pipeline that improves recovery while strictly preventing false identifications through unambiguous evidence thresholds.

### Pipeline Architecture (`app/recovery.py`)

1. **Standard Decoder First:** The captured image is always presented to the project's standard decoder (vendored ZXing) first. If cleanly decoded, it returns `decoded_normally` without repair heuristics.
2. **Deterministic Preprocessing:**
   - **Contrast Normalization:** `ImageOps.autocontrast` expands dynamic range, lifting faint or low-contrast bars.
   - **Skew Estimation & Alignment:** 1D projection gradient variance optimization scans candidate angles $\theta \in [-30^\circ, +30^\circ]$ to find the orientation maximizing vertical bar projection variance, correcting rotational misalignments up to 25°.
3. **Multi-Scanline Horizontal Waveform Extraction:**
   - Samples 40 horizontal scanlines across the vertical height of the barcode.
   - Binary run-length demodulation identifies start guard (`101`), center guard (`01010`), and stop guard (`101`).
   - Calibrates module width grids independently on the left half ($w_L$) and right half ($w_R$).
   - Demodulates 6 left digits (testing L and G patterns) and 6 right digits (R patterns), and determines the leading digit from left parity.
4. **Strict Safety & Decision Rule:**
   - **Validation, Not Correction:** The EAN-13 check digit is used strictly to validate candidates. It is never used to synthesize or invent missing bars.
   - **Consensus Threshold:** A candidate GTIN is only accepted if at least **5 independent horizontal scanlines** decode the exact same valid code.
   - **Margin of Victory:** The top candidate must have $\ge 3\times$ the vote count of any runner-up candidate. If competing candidates exist with close vote counts, the pipeline abstains as ambiguous.
   - **Catalog Independence:** The recovery engine is strictly isolated from catalogue lookups and never accepts a candidate simply because it matches a product in the catalog.
   - **Safe Abstention:** If evidence is insufficient, guards are unidentifiable, or signals are ambiguous, the pipeline returns `abstained` and clearly explains why it refused to guess.
5. **UI Transparency:**
   - The UI distinguishes `"Decoded normally"` from `"Recovered from damaged image"` and `"Recovery Abstained"`.
   - When recovery is attempted, side-by-side **Captured Image Crop** and **Enhanced & Aligned Crop** are displayed with the explicit notice:  
     *“Transparency Notice: The enhanced crop is displayed for visual inspection of the signal processing steps and is not proof that the physical barcode was restored.”*

### Known Recovery Limitations

- **Physical Substrate Tears:** If guard patterns (start `101`, center `01010`, or stop `101`) are torn across all vertical heights, the pipeline safely abstains.
- **Perspective / 3D Warping:** High perspective distortions across cylindrical bottles beyond 2D affine rotation require planar recalibration.
- **Severe Blurring / Defocus:** When camera lens defocus completely merges adjacent bars into an unresolvable blur, the pipeline abstains rather than inventing values.

---

## Reproducible Evaluation Harness

### Running the Evaluation Benchmark

Run the evaluation harness from PowerShell:

```powershell
python scripts/evaluate_recovery.py --generate-dataset
```

The script evaluates both the standard decoder and the recovery pipeline on a paired dataset across controlled damage conditions, writing structured results to `generated/evaluation_report.json` and `generated/EVALUATION_REPORT.md`.

### Evaluation Findings (Benchmark Dataset)

| Metric | Standard Decoder (ZXing) | Standard + Recovery Pipeline | Delta |
| :--- | :--- | :--- | :--- |
| **Exact Recovery Count** | 24 / 42 | **35 / 42** | **+11 recoveries (+26.2%)** |
| **Exact Recovery Rate** | 57.1% | **83.3%** | **+26.2% improvement** |
| **False Identification Count** | **0 / 42** | **0 / 42** | **0 false product identifications** |
| **False Identification Rate** | **0.0%** | **0.0%** | **Maintained strict 0.0% false ID rate** |
| **Abstention Count** | 18 / 42 (42.9%) | **7 / 42 (16.7%)** | Safely abstains on unrecoverable noise |

### Breakdown by Controlled Damage Type

| Damage Condition | N | Standard Decoder Exact | Recovery Pipeline Exact | False Identifications | Abstentions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Control** | 6 | 6 / 6 (100%) | **6 / 6 (100%)** | 0 (0.0%) | 0 |
| **Fading (Low Amplitude)** | 6 | 6 / 6 (100%) | **6 / 6 (100%)** | 0 (0.0%) | 0 |
| **Scratches (Horizontal Cuts)** | 6 | 6 / 6 (100%) | **6 / 6 (100%)** | 0 (0.0%) | 0 |
| **Smudges (Ink Blotches)** | 6 | 6 / 6 (100%) | **6 / 6 (100%)** | 0 (0.0%) | 0 |
| **Low Contrast (15-Level Window)**| 6 | 0 / 6 (0%) | **6 / 6 (100%)** | 0 (0.0%) | 0 |
| **Skew (25° Rotation)** | 6 | 0 / 6 (0%) | **5 / 6 (83.3%)** | 0 (0.0%) | 1 |
| **Severe Unrecoverable Noise** | 6 | 0 / 6 (0%) | **0 / 6 (0%)** | **0 (0.0%)** | **6 (100% abstention)** |

> **Synthetic Dataset Disclosure:** All automated benchmark images are synthetic degradations with verified ground-truth GTINs. They serve as a controlled ablation suite and must not be presented as real-world field data.

### Extending with Real Captured Barcode Images

Instructions for adding real-world photographed barcode images to the benchmark:
1. Save the captured photo into `tests/evaluation_dataset/images/` (e.g. `images/real_retail_box_01.png`).
2. Verify the true product GTIN from the packaging.
3. Add a corresponding entry in `tests/evaluation_dataset/manifest.json`:
   ```json
   {
     "filename": "real_retail_box_01.png",
     "relative_path": "images/real_retail_box_01.png",
     "ground_truth_code": "4006381333931",
     "damage_type": "real_glare_crease",
     "synthetic": false,
     "provenance": "Photographed using mobile phone under store lighting",
     "description": "Packaging fold with specular glare"
   }
   ```
4. Re-run `python scripts/evaluate_recovery.py` to evaluate the real-world sample alongside the synthetic set.

---

## Frontend Interface Redesign & Navigation Architecture

The web interface is organized into a clean, minimal, 9-tab single-page application where only one focused section is active at any time. The interface adopts a calm, accessible aesthetic adhering to the palette extracted from design specifications (`#475569` Slate primary, `#58788C` Steel Blue secondary, `#738B7D` Sage tertiary, `#EDEEF0` soft warm-gray background):

1. **Scan (Main):**
   - 3 input modes: Live Camera, Image Upload, and Manual / USB Entry.
   - Real-time states: Scanning, Looking up, Product found, Not in catalogue, Invalid code, and Network/lookup error.
   - Displays detected code, product name, category, and lookup origin badge (`Normal scan`, `Recovered`, `Manual entry`).
2. **Damaged Barcode Recovery:**
   - Dedicated workspace for damaged EAN-13 recovery with live test fixtures (Fading, Scratch, Smudge, Low contrast, Skew).
   - Side-by-side display of original capture and processed barcode crop.
   - Required Transparency Notice explaining that image enhancement is an evidence extraction aid, not a physical reconstruction.
   - Technical signal metrics (skew angle, scanline agreement %, candidate pattern validation) are tucked under an optional `<details>` "More technical details" disclosure so non-technical users are not overwhelmed.
3. **Scan History:**
   - Displays recent scans in the current session with timestamp, detected barcode, method, and lookup outcome.
   - Search filter by barcode or name; filter by method and outcome.
   - Click to reopen any prior result immediately.
   - Session disclosure: Explains that history is session-only and does not sync across devices.
4. **Products (Full Catalogue):**
   - Live search across all 16 catalogue products with category filter pills (All 16, Dress, Ethnic, Casual, Formal, Sports, etc.).
   - Interactive product inspector displaying verified attributes (`id`, `barcode`, `name`, `category`) and explicitly labeling unrecorded attributes (Price, Dimensions, Stock, Brand) as "Not available".
5. **Batch:**
   - Temporary scan collection session with duplicate count aggregation (`2×`, `3×`, etc.).
   - Non-inventory disclaimer clarifying that batching does not mutate stock.
6. **Saved Products:**
   - Bookmark products with one click.
   - Persisted in local browser storage (`localStorage`) with clear device/browser-specific disclaimer.
7. **Compare:**
   - Side-by-side comparison table of selected catalogue products using verified fields.
   - Missing fields cleanly rendered as "Not available".
8. **Catalog Overview:**
   - Verified counts (16 products, 8 categories) and category summary breakdown.
   - Notice of paused missing-product submissions.
9. **Print Labels:**
   - Direct download and access for the 16-in-1 printable A4 PDF sheet (`/api/labels/pdf`) and large format PDF with 100% scale guidelines.

---

## Practical Application Features

### 1. Manual Barcode Entry
- Allows entering barcode values manually when camera scanning is hindered.
- Validates input format (Code 128 or 13-digit EAN-13 with check digit calculation).
- Routes through the exact same lookup and state display as camera scanning.

### 2. Scan History & Result Reopening
- Tracks recent scans in the active session with timestamp, barcode, product name, and matching status.
- Every history item is clickable, immediately reopening its product details.
- Stores minimal data without persisting sensitive session tokens.

### 3. Saved Products (Bookmarks)
- Users can bookmark products with a single tap (`★ Bookmark`).
- Persisted in local browser storage (`localStorage`), accompanied by clear disclosure:  
  *“Saved items are stored in your local browser storage and are device/browser-specific.”*
- Provides view and deletion controls.

### 4. Batch Scan Session
- Allows scanning multiple items sequentially into a temporary collection list.
- Intelligently handles duplicate scans by updating the scan count (e.g. `2x`, `3x`) and timestamp without altering server stock counts.
- Dedicated drawer displays all items with options to inspect, remove, or clear the session.

### 5. Product Comparison
- Side-by-side comparison of up to 4 catalogue products.
- Uses strictly existing fields in the product model (`id`, `barcode`, `name`, `category_id`, `category_name`, `category_code`).
- Attributes not stored in the application (Price, Dimensions, Brand, Material, Stock) are explicitly rendered as **“Not available”** without fabricating values.

### 6. Missing-Product Submissions (Hardened & Intake Temporarily Disabled)
- **Current Intake Status:** Submissions are **temporarily disabled** (returning `HTTP 503 Service Unavailable`). Unregistered barcodes cannot be submitted or saved at this time.
- **Hosting & Ephemeral Storage Architecture:** The deployed application runs on stateless container infrastructure (`render.yaml` web service with no persistent disk or database). Writes to local files (such as `app/data/pending_submissions.json`) do not persist across instance restarts, redeployments, or container cycling. To prevent misleading users and avoid data loss, intake is disabled until durable storage exists.
- **Privacy & Security Protection:** The previously exposed unauthenticated `GET /api/submissions` queue endpoint has been removed. No unprotected admin routes were created. Internal pending submission lists and queues are not accessible to public users.
- **User Experience & Feedback:** In the frontend UI, clicking the missing-product information button opens an informative notice explaining that submission intake is temporarily disabled due to lack of durable storage and moderation. Form controls are disabled, preventing futile submission attempts.
- **Preservation of Existing Data:** Existing historical pending entries in `app/data/pending_submissions.json` remain preserved on disk and are not deleted or corrupted.
- **Prerequisites for Production Re-enablement:**
  1. *Durable Storage:* Provisioning an external database (e.g. PostgreSQL, Redis) or an attached persistent volume so records survive restarts.
  2. *Authenticated Administrative Review:* Implementing secure administrative authentication (e.g., session auth, OAuth2, or API tokens) and a protected moderation interface before submitted items can be reviewed and approved into the public catalogue.
- **Remaining Limitations:** Missing-product submissions are strictly **not production-safe** in the current architecture and remain disabled until both durable persistent storage and an authenticated review path are implemented.

### 7. Catalog Overview & Category Breakdown
- **Verified Public Metrics:** `GET /api/catalog-overview` reports verified catalogue metrics: 16 products, 8 categories, and the complete category breakdown with codes and descriptions.
- **Queue Privacy:** Internal pending submission counts and queue metrics are strictly excluded from public responses to prevent operational information leakage.
- **Coverage Disclaimer:** Explicitly states: *“Category coverage percentages are not reported because total potential market products per category are unrecorded in this system.”*


---

## Hardware Architecture & Future Roadmap

For comprehensive documentation on how software concepts map to microcontroller hardware (UART communication, circular FIFO buffers, Finite State Machines, and LCD/LED actuation), refer to [LDAM_MAPPING.md](file:///c:/BarcodeReader/LDAM_MAPPING.md).
