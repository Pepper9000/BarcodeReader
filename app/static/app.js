/**
 * Frontend JavaScript for BarcodeReader LDAM System — Phase 3
 *
 * Implements:
 * 1. Manual / USB Scanner Terminal (Keyboard Wedge emulation, auto-refocus)
 * 2. Client-side Image-Based Barcode Scanning via ZXing (@zxing/library)
 * 3. Live Mobile Camera Barcode Scanning (Environment rear camera preference,
 *    continuous frame decoding loop, ROI optimization, duplicate prevention,
 *    visual/audio feedback, Android Chrome touch optimization, secure context checks)
 * 4. Multi-format support (Code 128, Code 39, EAN-13, EAN-8, UPC-A, UPC-E, ITF, QR, DataMatrix)
 * 5. Dynamic category resolution, scan history, and error recovery
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements - Mode Switch Tabs
  const tabManualBtn = document.getElementById("tab-manual-btn");
  const tabImageBtn = document.getElementById("tab-image-btn");
  const tabCameraBtn = document.getElementById("tab-camera-btn");

  const panelManual = document.getElementById("panel-manual");
  const panelImage = document.getElementById("panel-image");
  const panelCamera = document.getElementById("panel-camera");

  // DOM Elements - Manual Scan
  const scanForm = document.getElementById("scan-form");
  const barcodeInput = document.getElementById("barcode-input");
  const scanBtn = document.getElementById("scan-btn");
  const demoChips = document.querySelectorAll("#panel-manual .chip");

  // DOM Elements - Image Scan
  const dropZone = document.getElementById("drop-zone");
  const dropZonePrompt = document.getElementById("drop-zone-prompt");
  const imageFileInput = document.getElementById("image-file-input");
  const previewWrapper = document.getElementById("preview-wrapper");
  const imagePreview = document.getElementById("image-preview");
  const previewFilename = document.getElementById("preview-filename");
  const previewDetails = document.getElementById("preview-details");
  const removeImageBtn = document.getElementById("remove-image-btn");
  const scanImageBtn = document.getElementById("scan-image-btn");
  const scanImageBtnText = document.getElementById("scan-image-btn-text");
  const scanImageSpinner = document.getElementById("scan-image-spinner");
  const multiBarcodeCard = document.getElementById("multi-barcode-card");
  const multiBarcodeOptions = document.getElementById("multi-barcode-options");
  const sampleChips = document.querySelectorAll(".chip-sample");

  // DOM Elements - Live Camera Scan (Phase 3)
  const cameraStartBtn = document.getElementById("camera-start-btn");
  const cameraStopBtn = document.getElementById("camera-stop-btn");
  const cameraDeviceSelect = document.getElementById("camera-device-select");
  const cameraTorchBtn = document.getElementById("camera-torch-btn");

  const cameraPlaceholder = document.getElementById("camera-placeholder");
  const cameraActiveView = document.getElementById("camera-active-view");
  const cameraVideo = document.getElementById("camera-video");
  const viewfinderFrame = document.getElementById("viewfinder-frame");
  const cameraStatusText = document.getElementById("camera-status-text");

  const cameraScanSuccessBar = document.getElementById("camera-scan-success-bar");
  const cameraResumeBtn = document.getElementById("camera-resume-btn");

  const cameraFallbackCard = document.getElementById("camera-fallback-card");
  const cameraFallbackTitle = document.getElementById("camera-fallback-title");
  const cameraFallbackMessage = document.getElementById("camera-fallback-message");
  const btnFallbackManual = document.getElementById("btn-fallback-manual");
  const btnFallbackUpload = document.getElementById("btn-fallback-upload");
  const linkSwitchUpload = document.getElementById("link-switch-upload");

  // DOM Elements - Status & Product Card
  const statusAlert = document.getElementById("status-alert");
  const alertIcon = document.getElementById("alert-icon");
  const alertTitle = document.getElementById("alert-title");
  const alertMessage = document.getElementById("alert-message");

  const productStatusBadge = document.getElementById("product-status-badge");
  const productPlaceholder = document.getElementById("product-placeholder");
  const productDetails = document.getElementById("product-details");

  const productName = document.getElementById("product-name");
  const productCategoryName = document.getElementById("product-category-name");
  const productBarcode = document.getElementById("product-barcode");
  const productId = document.getElementById("product-id");
  const productCategoryId = document.getElementById("product-category-id");
  const productCategoryCode = document.getElementById("product-category-code");

  const categorySummaryList = document.getElementById("category-summary-list");
  const totalCategoriesCount = document.getElementById("total-categories-count");

  const historyEmpty = document.getElementById("history-empty");
  const historyList = document.getElementById("history-list");
  const clearHistoryBtn = document.getElementById("clear-history-btn");

  // Application State
  let activeTab = "manual"; // 'manual' | 'image' | 'camera'
  let currentLoadedImage = null; // HTMLImageElement
  let currentLoadedFile = null;  // File object
  let isImageScanning = false;
  const scanHistory = [];

  // Live Camera State (Phase 3)
  let cameraStream = null;
  let isCameraActive = false;
  let isScanningPaused = false;
  let cameraAnimationId = null;
  let lastCameraScanTime = 0;
  let scanPassCounter = 0;
  let torchState = false;
  const CAMERA_SCAN_INTERVAL_MS = 200; // ~5 scans per second: optimal balance of speed and low CPU

  // Offscreen Canvas for Frame Extraction
  const offscreenCanvas = document.createElement("canvas");
  const offscreenCtx = offscreenCanvas.getContext("2d", { willReadFrequently: true });

  // Focus utility: keep input active for keyboard-wedge scanner when manual tab is active
  function refocusInput() {
    if (activeTab === "manual" && barcodeInput) {
      setTimeout(() => {
        barcodeInput.focus();
        barcodeInput.select();
      }, 50);
    }
  }

  // Update Status Alert Banner
  function showAlert(type, title, message) {
    statusAlert.className = `alert alert-${type}`;
    if (type === "success") {
      alertIcon.textContent = "✅";
    } else if (type === "error") {
      alertIcon.textContent = "⚠️";
    } else if (type === "loading") {
      alertIcon.textContent = "⏳";
    } else {
      alertIcon.textContent = "ℹ️";
    }
    alertTitle.textContent = title;
    alertMessage.textContent = message;
  }

  // Play Acoustic Feedback (LDAM Tone: 1200Hz 80ms)
  function playSuccessBeep() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(1200, ctx.currentTime);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.08);
    } catch (e) {
      // Audio optional, ignore if user interaction policy blocks audio
    }
  }

  // Display Product Info in UI
  function displayProduct(product, source = "MANUAL") {
    productPlaceholder.classList.add("hidden");
    productDetails.classList.remove("hidden");

    productName.textContent = product.name;
    productCategoryName.textContent = product.category_name;
    productBarcode.textContent = product.barcode;
    productId.textContent = product.id;
    productCategoryId.textContent = `CAT #${product.category_id}`;
    productCategoryCode.textContent = product.category_code || "—";

    productStatusBadge.textContent = "Identified";
    productStatusBadge.className = "badge badge-system";
  }

  // Clear / Reset Product Info Display
  function resetProductDisplay(statusText = "Awaiting Scan") {
    productPlaceholder.classList.remove("hidden");
    productDetails.classList.add("hidden");

    productStatusBadge.textContent = statusText;
    productStatusBadge.className = "badge badge-mode";
  }

  // Add event to Recent Scan History
  function recordHistory(barcode, success, description, categoryName, source = "MANUAL") {
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const entry = {
      time: timeStr,
      barcode: barcode,
      success: success,
      desc: description,
      category: categoryName || (success ? "Categorized" : "Error"),
      source: source,
    };

    scanHistory.unshift(entry);
    renderHistory();
  }

  // Render Recent Scan History
  function renderHistory() {
    if (scanHistory.length === 0) {
      historyEmpty.classList.remove("hidden");
      historyList.classList.add("hidden");
      historyList.innerHTML = "";
      return;
    }

    historyEmpty.classList.add("hidden");
    historyList.classList.remove("hidden");
    historyList.innerHTML = "";

    scanHistory.slice(0, 10).forEach((item) => {
      const li = document.createElement("li");
      li.className = "history-item";

      const badgeClass = item.success ? "history-badge-success" : "history-badge-error";
      const badgeText = item.success ? "MATCH" : "FAILED";

      li.innerHTML = `
        <div class="history-item-main">
          <div class="history-header-line">
            <span class="history-code">${escapeHtml(item.barcode)}</span>
            <span class="history-source-badge">${escapeHtml(item.source)}</span>
            <span class="history-desc">&bull; ${item.time}</span>
          </div>
          <span class="history-desc">${escapeHtml(item.desc)}</span>
        </div>
        <span class="history-badge ${badgeClass}">${badgeText}</span>
      `;
      historyList.appendChild(li);
    });
  }

  // HTML Escape helper
  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, (m) => {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m];
    });
  }

  // Perform Scan Request to Backend
  async function performScan(rawBarcode, source = "MANUAL") {
    const barcode = (rawBarcode || "").trim();

    if (!barcode) {
      showAlert("error", "Validation Error", "Barcode cannot be empty. Please scan or enter a valid barcode.");
      resetProductDisplay("Invalid Input");
      recordHistory(rawBarcode || "(Empty)", false, "Empty barcode submitted", null, source);
      refocusInput();
      return;
    }

    // Set loading state on manual scan button
    if (source === "MANUAL") {
      scanBtn.disabled = true;
      scanBtn.textContent = "Scanning...";
    }

    try {
      const response = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ barcode }),
      });

      const data = await response.json();

      if (response.ok) {
        // Success: Product found and resolved
        displayProduct(data, source);
        showAlert(
          "success",
          "Product Identified & Categorized",
          `Matched '${data.barcode}' to '${data.name}' in category '${data.category_name}' [via ${source}].`
        );
        recordHistory(data.barcode, true, data.name, data.category_name, source);
      } else if (response.status === 404) {
        // Not Found
        resetProductDisplay("Not Found");
        showAlert(
          "error",
          "Barcode Not Found",
          data.detail || `No catalogue entry matches barcode '${barcode}'.`
        );
        recordHistory(barcode, false, "Unknown Barcode (404)", null, source);
      } else {
        // Bad Request or Validation Error
        resetProductDisplay("Error");
        showAlert(
          "error",
          "Scan Error",
          data.detail || `Server returned error (${response.status}).`
        );
        recordHistory(barcode, false, data.detail || `HTTP ${response.status}`, null, source);
      }
    } catch (err) {
      console.error("Scan fetch error:", err);
      resetProductDisplay("Network Error");
      showAlert("error", "Network / Server Error", "Could not connect to the BarcodeReader server.");
      recordHistory(barcode, false, "Network connection error", null, source);
    } finally {
      if (source === "MANUAL") {
        scanBtn.disabled = false;
        scanBtn.textContent = "Scan";
      }
      refocusInput();
    }
  }

  // ---------------------------------------------------------------------------
  // Phase 3: Live Mobile Camera Scanning
  // ---------------------------------------------------------------------------

  // Check if current browser context supports camera streaming
  function checkCameraSupport() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
      if (!isLocal && !window.isSecureContext) {
        return {
          supported: false,
          reason: "HTTPS Required",
          message: "Live camera access requires an HTTPS connection when accessed outside localhost (e.g., from a mobile device over Wi-Fi). Please use the 'Upload Image' tab or access via HTTPS.",
        };
      }
      return {
        supported: false,
        reason: "API Not Supported",
        message: "Your browser does not support mediaDevices.getUserMedia. Please update your browser or use the 'Upload Image' tab.",
      };
    }
    return { supported: true };
  }

  // Populate Camera Selector with Available Video Devices
  async function enumerateCameraDevices() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter((d) => d.kind === "videoinput");

      cameraDeviceSelect.innerHTML = "";

      if (videoDevices.length > 1) {
        videoDevices.forEach((dev, idx) => {
          const opt = document.createElement("option");
          opt.value = dev.deviceId;
          let label = dev.label;
          if (!label) {
            label = idx === 0 ? "Rear / Main Camera" : `Camera ${idx + 1}`;
          }
          opt.textContent = label;
          cameraDeviceSelect.appendChild(opt);
        });
        cameraDeviceSelect.classList.remove("hidden");
      } else {
        cameraDeviceSelect.classList.add("hidden");
      }
    } catch (e) {
      console.warn("Could not enumerate camera devices:", e);
    }
  }

  // Start Live Camera
  async function startCamera() {
    cameraFallbackCard.classList.add("hidden");
    const support = checkCameraSupport();

    if (!support.supported) {
      cameraFallbackTitle.textContent = support.reason;
      cameraFallbackMessage.textContent = support.message;
      cameraFallbackCard.classList.remove("hidden");
      showAlert("error", support.reason, support.message);
      return;
    }

    cameraStartBtn.disabled = true;
    showAlert("loading", "Starting Camera", "Requesting camera permissions...");

    const selectedDeviceId = cameraDeviceSelect.value;
    const constraints = {
      audio: false,
      video: selectedDeviceId
        ? { deviceId: { exact: selectedDeviceId } }
        : {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
    };

    try {
      cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
      cameraVideo.srcObject = cameraStream;

      cameraVideo.onloadedmetadata = () => {
        cameraVideo.play().catch((err) => {
          console.warn("Video play error:", err);
        });

        isCameraActive = true;
        isScanningPaused = false;
        viewfinderFrame.classList.remove("detected");
        cameraScanSuccessBar.classList.add("hidden");

        cameraPlaceholder.classList.add("hidden");
        cameraActiveView.classList.remove("hidden");

        cameraStartBtn.classList.add("hidden");
        cameraStopBtn.classList.remove("hidden");
        cameraStartBtn.disabled = false;

        cameraStatusText.textContent = "Scanning...";
        showAlert("success", "Camera Active", "Point camera at any product barcode. Hold steady to scan.");

        // Check flashlight capability
        checkTorchCapability(cameraStream);

        // Populate camera list if not already done
        enumerateCameraDevices();

        // Start decoding loop
        startDecodingLoop();
      };
    } catch (err) {
      console.error("Camera access error:", err);
      cameraStartBtn.disabled = false;
      cameraStartBtn.classList.remove("hidden");
      cameraStopBtn.classList.add("hidden");

      let title = "Camera Access Error";
      let msg = "Could not start camera.";

      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        title = "Permission Denied";
        msg = "Camera permission was denied. Please allow camera permissions in your browser bar, or switch to Upload Image mode.";
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        title = "No Camera Found";
        msg = "No suitable camera device was found on this device.";
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        title = "Camera In Use";
        msg = "The camera is currently in use by another application or tab.";
      }

      cameraFallbackTitle.textContent = title;
      cameraFallbackMessage.textContent = msg;
      cameraFallbackCard.classList.remove("hidden");
      showAlert("error", title, msg);
    }
  }

  // Stop Live Camera and Release Resources
  function stopCamera() {
    if (cameraAnimationId) {
      cancelAnimationFrame(cameraAnimationId);
      cameraAnimationId = null;
    }

    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => {
        track.stop();
      });
      cameraStream = null;
    }

    isCameraActive = false;
    isScanningPaused = false;
    torchState = false;

    cameraVideo.srcObject = null;
    cameraPlaceholder.classList.remove("hidden");
    cameraActiveView.classList.add("hidden");
    cameraScanSuccessBar.classList.add("hidden");
    viewfinderFrame.classList.remove("detected");

    cameraStartBtn.classList.remove("hidden");
    cameraStartBtn.disabled = false;
    cameraStopBtn.classList.add("hidden");
    cameraTorchBtn.classList.add("hidden");

    showAlert("idle", "Camera Stopped", "Live camera stopped. Click 'Start Camera' to resume.");
  }

  // Check Flashlight / Torch Support on Video Track
  function checkTorchCapability(stream) {
    try {
      const track = stream.getVideoTracks()[0];
      const capabilities = track.getCapabilities ? track.getCapabilities() : {};
      if (capabilities.torch) {
        cameraTorchBtn.classList.remove("hidden");
      } else {
        cameraTorchBtn.classList.add("hidden");
      }
    } catch (e) {
      cameraTorchBtn.classList.add("hidden");
    }
  }

  // Toggle Torch / Flashlight
  async function toggleTorch() {
    if (!cameraStream) return;
    try {
      const track = cameraStream.getVideoTracks()[0];
      torchState = !torchState;
      await track.applyConstraints({
        advanced: [{ torch: torchState }],
      });
      cameraTorchBtn.textContent = torchState ? "🔦" : "💡";
    } catch (e) {
      console.warn("Torch toggle failed:", e);
    }
  }

  // Decode Single Frame from Video Stream
  function decodeVideoFrame() {
    const videoW = cameraVideo.videoWidth;
    const videoH = cameraVideo.videoHeight;
    if (!videoW || !videoH) return null;

    // Region of Interest (ROI): Target central 70% width and 50% height
    // Every 3rd scan pass, test full video frame in case user held code near edge
    scanPassCounter++;
    let cropX, cropY, cropW, cropH;

    if (scanPassCounter % 3 === 0) {
      // Full frame pass
      cropX = 0;
      cropY = 0;
      cropW = videoW;
      cropH = videoH;
    } else {
      // Fast central ROI pass
      cropW = Math.round(videoW * 0.70);
      cropH = Math.round(videoH * 0.50);
      cropX = Math.round((videoW - cropW) / 2);
      cropY = Math.round((videoH - cropH) / 2);
    }

    const MAX_CANVAS_DIM = 800;
    const scale = Math.min(1.0, MAX_CANVAS_DIM / Math.max(cropW, cropH));
    const targetW = Math.round(cropW * scale);
    const targetH = Math.round(cropH * scale);

    offscreenCanvas.width = targetW;
    offscreenCanvas.height = targetH;
    offscreenCtx.drawImage(cameraVideo, cropX, cropY, cropW, cropH, 0, 0, targetW, targetH);

    // 1. Try Native BarcodeDetector if available
    if ("BarcodeDetector" in window) {
      // Native detector will be tested asynchronously in startDecodingLoop if active
    }

    // 2. Decode using vendored ZXing MultiFormatReader
    if (typeof ZXing !== "undefined") {
      try {
        const imgData = offscreenCtx.getImageData(0, 0, targetW, targetH);
        const luminances = new Uint8ClampedArray(targetW * targetH);
        const d = imgData.data;
        for (let i = 0, j = 0; i < d.length; i += 4, j++) {
          luminances[j] = (d[i] * 77 + d[i + 1] * 150 + d[i + 2] * 29) >> 8;
        }

        const hints = new Map();
        hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
        hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
          ZXing.BarcodeFormat.CODE_128,
          ZXing.BarcodeFormat.CODE_39,
          ZXing.BarcodeFormat.EAN_13,
          ZXing.BarcodeFormat.EAN_8,
          ZXing.BarcodeFormat.UPC_A,
          ZXing.BarcodeFormat.UPC_E,
          ZXing.BarcodeFormat.ITF,
          ZXing.BarcodeFormat.QR_CODE,
          ZXing.BarcodeFormat.DATA_MATRIX,
        ]);

        const lumSource = new ZXing.RGBLuminanceSource(luminances, targetW, targetH);
        const binarizer = new ZXing.HybridBinarizer(lumSource);
        const bitmap = new ZXing.BinaryBitmap(binarizer);
        const reader = new ZXing.MultiFormatReader();
        reader.setHints(hints);
        const result = reader.decode(bitmap);

        if (result && result.getText()) {
          return result.getText().trim();
        }
      } catch (e) {
        // Normal for frames without barcodes, return null
        return null;
      }
    }
    return null;
  }

  // Handle Detected Barcode from Live Camera
  async function handleCameraBarcodeDetected(barcodeText) {
    if (!barcodeText || isScanningPaused) return;

    // Pause scanning immediately to prevent duplicate requests
    isScanningPaused = true;

    // Visual feedback: emerald green border flash & success chip
    viewfinderFrame.classList.add("detected");
    cameraStatusText.textContent = `Matched: ${barcodeText}`;
    cameraScanSuccessBar.classList.remove("hidden");

    // Audio acoustic feedback
    playSuccessBeep();

    showAlert(
      "loading",
      "Barcode Detected",
      `Detected barcode '${barcodeText}' from camera. Querying catalogue...`
    );

    // Query backend catalogue
    await performScan(barcodeText, "CAMERA");
  }

  // Resume Camera Scanning (Allows scanning another product without refreshing)
  function resumeCameraScanning() {
    isScanningPaused = false;
    viewfinderFrame.classList.remove("detected");
    cameraScanSuccessBar.classList.add("hidden");
    cameraStatusText.textContent = "Scanning...";
    showAlert("success", "Scanning Resumed", "Align next barcode within the target frame.");
  }

  // Continuous Camera Decoding Loop (Throttled Animation Frame)
  function startDecodingLoop() {
    async function scanTick(timestamp) {
      if (!isCameraActive) return;

      if (!isScanningPaused && cameraVideo.readyState >= 2) {
        if (timestamp - lastCameraScanTime >= CAMERA_SCAN_INTERVAL_MS) {
          lastCameraScanTime = timestamp;

          // Check Native BarcodeDetector first if available
          let detected = null;
          if ("BarcodeDetector" in window) {
            try {
              if (!window._cachedBarcodeDetector) {
                const formats = await window.BarcodeDetector.getSupportedFormats();
                window._cachedBarcodeDetector = new window.BarcodeDetector({ formats });
              }
              const results = await window._cachedBarcodeDetector.detect(cameraVideo);
              if (results && results.length > 0 && results[0].rawValue) {
                detected = results[0].rawValue.trim();
              }
            } catch (err) {
              // fallback to ZXing
            }
          }

          // If native did not find, run ZXing
          if (!detected) {
            detected = decodeVideoFrame();
          }

          if (detected) {
            await handleCameraBarcodeDetected(detected);
          }
        }
      }

      if (isCameraActive) {
        cameraAnimationId = requestAnimationFrame(scanTick);
      }
    }

    cameraAnimationId = requestAnimationFrame(scanTick);
  }

  // ---------------------------------------------------------------------------
  // Phase 2: Client-Side Image Barcode Decoding
  // ---------------------------------------------------------------------------

  // Validate File Type
  function validateImageFile(file) {
    if (!file) return { valid: false, message: "No file selected." };

    const validMimes = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
    const validExtensions = /\.(jpe?g|png|webp)$/i;

    const hasValidMime = file.type && validMimes.includes(file.type.toLowerCase());
    const hasValidExt = validExtensions.test(file.name);

    if (!hasValidMime && !hasValidExt) {
      return {
        valid: false,
        message: `Unsupported file type (${file.type || "unknown"}). Only JPG, JPEG, PNG, and WEBP images are supported.`,
      };
    }

    return { valid: true };
  }

  // Load and Preview File
  function handleFileSelected(file) {
    multiBarcodeCard.classList.add("hidden");
    multiBarcodeOptions.innerHTML = "";

    const validation = validateImageFile(file);
    if (!validation.valid) {
      showAlert("error", "Invalid File Type", validation.message);
      resetProductDisplay("Unsupported File");
      resetImageState();
      return;
    }

    currentLoadedFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        currentLoadedImage = img;
        imagePreview.src = e.target.result;

        const sizeKb = (file.size / 1024).toFixed(1);
        previewFilename.textContent = file.name;
        previewDetails.textContent = `${img.naturalWidth} × ${img.naturalHeight} px &bull; ${sizeKb} KB`;

        dropZonePrompt.classList.add("hidden");
        previewWrapper.classList.remove("hidden");
        scanImageBtn.disabled = false;

        showAlert(
          "idle",
          "Image Loaded",
          `'${file.name}' is ready. Click 'Scan Image for Barcode' to decode.`
        );
      };
      img.onerror = () => {
        showAlert("error", "Image Read Error", "Failed to render selected image.");
        resetImageState();
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }

  // Reset Image state
  function resetImageState() {
    currentLoadedImage = null;
    currentLoadedFile = null;
    imageFileInput.value = "";
    previewWrapper.classList.add("hidden");
    dropZonePrompt.classList.remove("hidden");
    imagePreview.src = "";
    scanImageBtn.disabled = true;
    multiBarcodeCard.classList.add("hidden");
    multiBarcodeOptions.innerHTML = "";
  }

  // Preprocess Image onto Canvas (Downscale if large to ensure fast decoding)
  function prepareCanvasFromImage(img) {
    const canvas = document.createElement("canvas");
    let width = img.naturalWidth || img.width;
    let height = img.naturalHeight || img.height;

    const MAX_DIM = 1600;
    if (width > MAX_DIM || height > MAX_DIM) {
      const scale = MAX_DIM / Math.max(width, height);
      width = Math.round(width * scale);
      height = Math.round(height * scale);
    }

    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, 0, 0, width, height);

    return { canvas, ctx, width, height };
  }

  // Multi-Barcode Decoding Core
  async function decodeBarcodesFromImage(img) {
    const { canvas, ctx, width, height } = prepareCanvasFromImage(img);
    const detectedBarcodes = new Set();

    // 1. Check Native BarcodeDetector API if available
    if ("BarcodeDetector" in window) {
      try {
        const formats = await window.BarcodeDetector.getSupportedFormats();
        const detector = new window.BarcodeDetector({ formats });
        const results = await detector.detect(canvas);
        for (const r of results) {
          if (r.rawValue && r.rawValue.trim()) {
            detectedBarcodes.add(r.rawValue.trim());
          }
        }
      } catch (nativeErr) {
        console.warn("Native BarcodeDetector pass failed, relying on ZXing:", nativeErr);
      }
    }

    // 2. ZXing Browser Multi-Format Decoding
    if (typeof ZXing !== "undefined") {
      const imgData = ctx.getImageData(0, 0, width, height);
      const luminances = new Uint8ClampedArray(width * height);
      const d = imgData.data;
      for (let i = 0, j = 0; i < d.length; i += 4, j++) {
        luminances[j] = (d[i] * 77 + d[i + 1] * 150 + d[i + 2] * 29) >> 8;
      }

      function scanPass(lumArray) {
        try {
          const hints = new Map();
          hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
          hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
            ZXing.BarcodeFormat.CODE_128,
            ZXing.BarcodeFormat.CODE_39,
            ZXing.BarcodeFormat.EAN_13,
            ZXing.BarcodeFormat.EAN_8,
            ZXing.BarcodeFormat.UPC_A,
            ZXing.BarcodeFormat.UPC_E,
            ZXing.BarcodeFormat.ITF,
            ZXing.BarcodeFormat.QR_CODE,
            ZXing.BarcodeFormat.DATA_MATRIX,
          ]);

          const lumSource = new ZXing.RGBLuminanceSource(lumArray, width, height);
          const binarizer = new ZXing.HybridBinarizer(lumSource);
          const bitmap = new ZXing.BinaryBitmap(binarizer);
          const reader = new ZXing.MultiFormatReader();
          reader.setHints(hints);
          return reader.decode(bitmap);
        } catch (e) {
          return null;
        }
      }

      // First pass on full image
      const workingLum = new Uint8ClampedArray(luminances);
      let passCount = 0;
      const MAX_PASSES = 4;

      while (passCount < MAX_PASSES) {
        const res = scanPass(workingLum);
        if (!res) break;

        const text = res.getText() ? res.getText().trim() : "";
        if (text) {
          detectedBarcodes.add(text);
        }

        // Blank out detected area to reveal any secondary barcode
        const pts = res.getResultPoints();
        if (pts && pts.length > 0) {
          const xs = pts.map((p) => p.getX());
          const ys = pts.map((p) => p.getY());
          const minX = Math.max(0, Math.floor(Math.min(...xs)) - 15);
          const maxX = Math.min(width - 1, Math.ceil(Math.max(...xs)) + 15);
          const minY = Math.max(0, Math.floor(Math.min(...ys)) - 25);
          const maxY = Math.min(height - 1, Math.ceil(Math.max(...ys)) + 25);

          for (let y = minY; y <= maxY; y++) {
            for (let x = minX; x <= maxX; x++) {
              workingLum[y * width + x] = 255;
            }
          }
        } else {
          break;
        }
        passCount++;
      }
    } else {
      console.error("ZXing library is not loaded on window.");
    }

    return Array.from(detectedBarcodes);
  }

  // Scan Image Action Handler
  async function handleScanImage() {
    if (isImageScanning || !currentLoadedImage) return;

    isImageScanning = true;
    scanImageBtn.disabled = true;
    scanImageBtnText.textContent = "Decoding Barcode...";
    scanImageSpinner.classList.remove("hidden");
    multiBarcodeCard.classList.add("hidden");
    multiBarcodeOptions.innerHTML = "";

    showAlert("loading", "Decoding Image", "Analyzing image pixels for barcodes with client-side ZXing...");

    try {
      const barcodes = await decodeBarcodesFromImage(currentLoadedImage);

      if (barcodes.length === 0) {
        showAlert(
          "error",
          "No Barcode Detected",
          "Could not detect any valid barcode in the uploaded image. Please ensure the barcode is sharp, well-lit, and in focus."
        );
        resetProductDisplay("No Barcode Detected");
        recordHistory(
          currentLoadedFile ? currentLoadedFile.name : "Image",
          false,
          "No detectable barcode found in image",
          null,
          "IMAGE"
        );
      } else if (barcodes.length === 1) {
        const detected = barcodes[0];
        showAlert(
          "loading",
          "Barcode Decoded",
          `Decoded barcode '${detected}'. Fetching product details from catalogue...`
        );
        await performScan(detected, "IMAGE");
      } else {
        showAlert(
          "idle",
          "Multiple Barcodes Detected",
          `Found ${barcodes.length} distinct barcodes in image. Please choose one below to identify.`
        );
        resetProductDisplay("Multiple Barcodes");
        multiBarcodeCard.classList.remove("hidden");
        multiBarcodeOptions.innerHTML = "";

        barcodes.forEach((code) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn-choice";
          btn.textContent = code;
          btn.addEventListener("click", () => {
            multiBarcodeCard.classList.add("hidden");
            performScan(code, "IMAGE");
          });
          multiBarcodeOptions.appendChild(btn);
        });
      }
    } catch (err) {
      console.error("Image scan processing error:", err);
      showAlert("error", "Decoding Error", "An error occurred during image barcode decoding.");
      resetProductDisplay("Decoding Error");
    } finally {
      isImageScanning = false;
      scanImageBtn.disabled = false;
      scanImageBtnText.textContent = "Scan Image for Barcode";
      scanImageSpinner.classList.add("hidden");
    }
  }

  // Load sample demo image
  async function loadSampleImage(filename) {
    try {
      showAlert("loading", "Loading Sample", `Fetching demo sample '${filename}'...`);
      const res = await fetch(`/static/samples/${filename}`);
      if (!res.ok) throw new Error("Could not load sample image");
      const blob = await res.blob();
      const file = new File([blob], filename, { type: blob.type || "image/png" });
      handleFileSelected(file);
    } catch (err) {
      console.error("Sample load error:", err);
      showAlert("error", "Sample Load Error", `Could not load sample image '${filename}'.`);
    }
  }

  // ---------------------------------------------------------------------------
  // Category Summary Loader
  // ---------------------------------------------------------------------------
  async function loadCategoriesSummary() {
    try {
      const res = await fetch("/api/categories");
      if (!res.ok) throw new Error("Failed to load categories");
      const categories = await res.json();

      categorySummaryList.innerHTML = "";
      totalCategoriesCount.textContent = `${categories.length} Categories`;

      categories.forEach((cat) => {
        const item = document.createElement("div");
        item.className = "category-item";
        item.innerHTML = `
          <span class="category-item-name">${escapeHtml(cat.name)}</span>
          <span class="category-item-count">${cat.product_count} items</span>
        `;
        categorySummaryList.appendChild(item);
      });
    } catch (err) {
      console.error("Failed to load categories summary:", err);
      categorySummaryList.innerHTML = `<div class="loading-spinner">Unable to load categories.</div>`;
    }
  }

  // ---------------------------------------------------------------------------
  // Tab Switching Management (Stops camera stream on exit)
  // ---------------------------------------------------------------------------
  function switchTab(newTab) {
    if (activeTab === newTab) return;

    // Stop camera immediately if navigating away from camera tab
    if (activeTab === "camera" && isCameraActive) {
      stopCamera();
    }

    activeTab = newTab;

    // Reset button states
    [tabManualBtn, tabImageBtn, tabCameraBtn].forEach((btn) => {
      btn.classList.remove("active");
      btn.setAttribute("aria-selected", "false");
    });
    [panelManual, panelImage, panelCamera].forEach((panel) => {
      panel.classList.add("hidden");
    });

    if (newTab === "manual") {
      tabManualBtn.classList.add("active");
      tabManualBtn.setAttribute("aria-selected", "true");
      panelManual.classList.remove("hidden");
      refocusInput();
    } else if (newTab === "image") {
      tabImageBtn.classList.add("active");
      tabImageBtn.setAttribute("aria-selected", "true");
      panelImage.classList.remove("hidden");
    } else if (newTab === "camera") {
      tabCameraBtn.classList.add("active");
      tabCameraBtn.setAttribute("aria-selected", "true");
      panelCamera.classList.remove("hidden");
    }
  }

  // ---------------------------------------------------------------------------
  // Event Listeners
  // ---------------------------------------------------------------------------

  // Tab switching clicks
  tabManualBtn.addEventListener("click", () => switchTab("manual"));
  tabImageBtn.addEventListener("click", () => switchTab("image"));
  tabCameraBtn.addEventListener("click", () => switchTab("camera"));

  // Manual Scan form submit
  scanForm.addEventListener("submit", (e) => {
    e.preventDefault();
    performScan(barcodeInput.value, "MANUAL");
  });

  // Manual Demo chips click
  demoChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const code = chip.getAttribute("data-barcode");
      barcodeInput.value = code;
      performScan(code, "DEMO-CHIP");
    });
  });

  // Image Upload File Picker & Drag-and-Drop
  dropZone.addEventListener("click", (e) => {
    if (e.target.closest("button") || e.target.closest("a")) return;
    imageFileInput.click();
  });

  imageFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  removeImageBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    resetImageState();
    showAlert("idle", "Ready for Scanning", "Image removed. Upload a new image or switch to Manual scan.");
  });

  scanImageBtn.addEventListener("click", handleScanImage);

  sampleChips.forEach((chip) => {
    chip.addEventListener("click", (e) => {
      e.stopPropagation();
      const sampleFile = chip.getAttribute("data-sample");
      loadSampleImage(sampleFile);
    });
  });

  // Phase 3: Camera Controls
  cameraStartBtn.addEventListener("click", startCamera);
  cameraStopBtn.addEventListener("click", stopCamera);
  cameraResumeBtn.addEventListener("click", resumeCameraScanning);
  cameraTorchBtn.addEventListener("click", toggleTorch);

  cameraDeviceSelect.addEventListener("change", () => {
    if (isCameraActive) {
      stopCamera();
      startCamera();
    }
  });

  // Fallback buttons
  btnFallbackManual.addEventListener("click", () => switchTab("manual"));
  btnFallbackUpload.addEventListener("click", () => switchTab("image"));
  linkSwitchUpload.addEventListener("click", (e) => {
    e.preventDefault();
    switchTab("image");
  });

  // Clear scan history
  clearHistoryBtn.addEventListener("click", () => {
    scanHistory.length = 0;
    renderHistory();
    refocusInput();
  });

  // Keep manual input focused only when manual tab is active
  document.addEventListener("click", (e) => {
    if (activeTab !== "manual") return;
    if (e.target.closest("button") || e.target.closest("input") || e.target.closest("a") || e.target.closest("select")) return;
    barcodeInput.focus();
  });

  // Initial setup
  loadCategoriesSummary();
  refocusInput();
});
