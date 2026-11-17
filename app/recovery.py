"""
Structure-aware EAN-13 barcode recovery module for BarcodeReader.

Provides deterministic image preprocessing, skew correction, multi-scanline
horizontal slicing, guard and digit pattern demodulation, and consensus-based
recovery for damaged EAN-13 barcodes.

Safety Principles:
1. Try the standard decoder (vendored ZXing) first.
2. Accept a recovered value only when multi-line consensus is strong and unambiguous.
3. Reject/abstain if evidence is weak or contradictory.
4. EAN-13 check digit is used strictly for candidate validation, never for error correction.
5. The recovery module is strictly isolated from product catalogue lookups.
"""

from __future__ import annotations

import base64
from io import BytesIO
import math
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageOps

# Repository paths
BASE_DIR = Path(__file__).resolve().parent.parent
ZXING_PATH = BASE_DIR / "app" / "static" / "vendor" / "zxing.min.js"

# EAN-13 encoding tables (7 modules per digit, 2 bars and 2 spaces)
L_PATTERNS: Dict[int, str] = {
    0: "0001101",
    1: "0011001",
    2: "0010011",
    3: "0111101",
    4: "0100011",
    5: "0110001",
    6: "0101111",
    7: "0111011",
    8: "0110111",
    9: "0001011",
}

G_PATTERNS: Dict[int, str] = {
    0: "0100111",
    1: "0110011",
    2: "0011011",
    3: "0100001",
    4: "0011101",
    5: "0111001",
    6: "0000101",
    7: "0010001",
    8: "0001001",
    9: "0010111",
}

R_PATTERNS: Dict[int, str] = {
    0: "1110010",
    1: "1100110",
    2: "1101100",
    3: "1000010",
    4: "1011100",
    5: "1001110",
    6: "1010000",
    7: "1000100",
    8: "1001000",
    9: "1110100",
}

PARITY_PATTERNS: Dict[int, str] = {
    0: "LLLLLL",
    1: "LLGLGG",
    2: "LLGGLG",
    3: "LLGGGL",
    4: "LGLLGG",
    5: "LGGLLG",
    6: "LGGGLL",
    7: "LGLGLG",
    8: "LGLGGL",
    9: "LGGLGL",
}

L_LOOKUP = {v: k for k, v in L_PATTERNS.items()}
G_LOOKUP = {v: k for k, v in G_PATTERNS.items()}
R_LOOKUP = {v: k for k, v in R_PATTERNS.items()}
PARITY_LOOKUP = {v: k for k, v in PARITY_PATTERNS.items()}

# Consensus & Safety thresholds
MIN_CONSENSUS_LINES = 5
MIN_LINE_PROPORTION = 0.20
MIN_VICTORY_MARGIN_RATIO = 3.0


def calculate_ean13_check_digit(d12: str) -> int:
    """
    Calculate the official EAN-13 check digit for a 12-digit string.

    Weights: alternating 1 and 3 for odd/even digit positions (1-indexed).
    Formula: (10 - sum(weights * digits) % 10) % 10.
    """
    if len(d12) != 12 or not d12.isdigit():
        raise ValueError("Check digit calculation requires exactly 12 numeric digits.")
    digits = [int(c) for c in d12]
    total = sum(d if i % 2 == 0 else d * 3 for i, d in enumerate(digits))
    return (10 - (total % 10)) % 10


def validate_ean13(code: str) -> bool:
    """Validate format and mathematical check digit of a 13-digit EAN string."""
    if not isinstance(code, str) or len(code) != 13 or not code.isdigit():
        return False
    return calculate_ean13_check_digit(code[:12]) == int(code[12])


def decode_standard_zxing(im: Image.Image) -> Optional[str]:
    """
    Invoke the repository's standard vendored ZXing library via Node.js.

    Passes raw 8-bit luminance buffer via standard input to ensure format
    independence and avoid codec distortions.
    """
    try:
        gray = im.convert("L")
        w, h = gray.size
        raw_bytes = gray.tobytes()

        node_script = """
const fs = require('fs');
const zx = require('./app/static/vendor/zxing.min.js');

const w = parseInt(process.argv[1]);
const h = parseInt(process.argv[2]);
const buf = fs.readFileSync(0);

const hints = new Map();
hints.set(zx.DecodeHintType.TRY_HARDER, true);
hints.set(zx.DecodeHintType.POSSIBLE_FORMATS, [
  zx.BarcodeFormat.EAN_13,
  zx.BarcodeFormat.CODE_128,
  zx.BarcodeFormat.CODE_39,
  zx.BarcodeFormat.EAN_8,
  zx.BarcodeFormat.UPC_A
]);

const lumArray = new Uint8ClampedArray(buf.buffer, buf.byteOffset, w * h);
const src = new zx.RGBLuminanceSource(lumArray, w, h);
const bm = new zx.BinaryBitmap(new zx.HybridBinarizer(src));
const reader = new zx.MultiFormatReader();
reader.setHints(hints);

try {
  const res = reader.decode(bm);
  console.log(res.getText().trim());
} catch(e) {
  console.log('NOT_FOUND');
}
"""
        proc = subprocess.run(
            ["node", "-e", node_script, str(w), str(h)],
            cwd=BASE_DIR,
            input=raw_bytes,
            capture_output=True,
            timeout=8,
            check=True,
        )
        out = proc.stdout.decode("utf-8").strip()
        return out if out and out != "NOT_FOUND" else None
    except Exception:
        return None


def image_to_base64_png(im: Image.Image) -> str:
    """Convert a PIL Image to a base64 PNG data URL."""
    buffered = BytesIO()
    im.save(buffered, format="PNG")
    b64_str = base64.b64encode(buffered.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64_str}"


def normalize_contrast(im: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Normalize image contrast and expand dynamic range.

    Uses PIL ImageOps.autocontrast to expand dynamic range across [0, 255].
    """
    gray = im.convert("L")
    extrema = gray.getextrema()
    p_min, p_max = (0, 255) if not extrema else extrema
    range_val = p_max - p_min

    damage_flags = []
    if range_val < 60:
        damage_flags.append("low_contrast")
    if p_min > 80:
        damage_flags.append("fading")

    try:
        normalized_im = ImageOps.autocontrast(gray, cutoff=2)
    except Exception:
        normalized_im = gray

    return normalized_im, {
        "p_min": p_min,
        "p_max": p_max,
        "dynamic_range": range_val,
        "detected_damage": damage_flags,
    }


def estimate_and_correct_skew(im: Image.Image, max_angle: int = 30) -> Tuple[Image.Image, float]:
    """
    Estimate barcode skew angle and correct orientation.

    Measures variance of the 1D horizontal projection derivative:
    since barcode bars are vertical, a rotated barcode has lower projection variance.
    Rotating by the true skew angle maximizes the projection gradient energy.
    """
    best_angle = 0
    max_var = -1.0

    def compute_projection_variance(rot_img: Image.Image) -> float:
        w, h = rot_img.size
        # Sample rows across vertical center
        step_y = max(1, h // 40)
        row_count = 0
        col_sums = [0.0] * w
        for y in range(h // 6, h * 5 // 6, step_y):
            row_count += 1
            for x in range(w):
                col_sums[x] += rot_img.getpixel((x, y))
        if row_count == 0 or w < 2:
            return 0.0
        # Compute derivative differences between adjacent columns
        diffs = [col_sums[x + 1] - col_sums[x] for x in range(w - 1)]
        mean_diff = sum(diffs) / len(diffs)
        var = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
        return var

    # Coarse search (-max_angle to +max_angle in 2-degree steps)
    for ang in range(-max_angle, max_angle + 1, 2):
        rot = im.rotate(ang, expand=True, fillcolor=255)
        var = compute_projection_variance(rot)
        if var > max_var:
            max_var = var
            best_angle = ang

    # Fine search (1-degree steps around coarse peak)
    fine_range = range(max(-max_angle, best_angle - 2), min(max_angle, best_angle + 2) + 1)
    for ang in fine_range:
        rot = im.rotate(ang, expand=True, fillcolor=255)
        var = compute_projection_variance(rot)
        if var > max_var:
            max_var = var
            best_angle = ang

    corrected_im = im.rotate(best_angle, expand=True, fillcolor=255) if abs(best_angle) >= 1 else im
    return corrected_im, float(best_angle)


def decode_single_scanline(binary: List[int]) -> Optional[str]:
    """
    Decode a 1D horizontal binary row into an EAN-13 candidate.

    Detects start guard (101), center guard (01010), and stop guard (101),
    calibrates module widths for left and right halves independently,
    and checks mathematical EAN-13 check digit.
    """
    runs: List[Tuple[int, int, int]] = []
    curr_c = binary[0]
    curr_len = 1
    curr_start = 0

    for i in range(1, len(binary)):
        val = binary[i]
        if val == curr_c:
            curr_len += 1
        else:
            runs.append((curr_c, curr_len, curr_start))
            curr_c = val
            curr_len = 1
            curr_start = i
    runs.append((curr_c, curr_len, curr_start))

    # Search for start guard: bar, space, bar (runs i, i+1, i+2)
    for i in range(len(runs) - 10):
        if runs[i][0] == 1 and runs[i + 1][0] == 0 and runs[i + 2][0] == 1:
            w1, w2, w3 = runs[i][1], runs[i + 1][1], runs[i + 2][1]
            u = (w1 + w2 + w3) / 3.0
            if u < 1.0:
                continue
            if max(abs(w1 - u), abs(w2 - u), abs(w3 - u)) > u * 0.45:
                continue

            start_end = runs[i + 2][2] + w3

            # Search for center guard: space, bar, space, bar, space
            for j in range(i + 3, len(runs) - 5):
                if (
                    runs[j][0] == 0
                    and runs[j + 1][0] == 1
                    and runs[j + 2][0] == 0
                    and runs[j + 3][0] == 1
                    and runs[j + 4][0] == 0
                ):
                    center_start = runs[j][2]
                    dist = center_start - start_end
                    ratio = dist / (42.0 * u)

                    if 0.90 <= ratio <= 1.10:
                        u_c = (runs[j + 1][1] + runs[j + 3][1]) / 2.0
                        if abs(u_c - u) > u * 0.45:
                            continue
                        center_end = runs[j + 4][2] + runs[j + 4][1]

                        # Search for stop guard: bar, space, bar
                        for k in range(j + 5, len(runs) - 2):
                            if runs[k][0] == 1 and runs[k + 1][0] == 0 and runs[k + 2][0] == 1:
                                stop_start = runs[k][2]
                                dist_r = stop_start - center_end
                                ratio_r = dist_r / (42.0 * u)

                                if 0.90 <= ratio_r <= 1.10:
                                    u_s = (runs[k][1] + runs[k + 1][1] + runs[k + 2][1]) / 3.0
                                    if abs(u_s - u) > u * 0.45:
                                        continue

                                    # Calibrated module widths for left and right halves
                                    w_L = (center_start - start_end) / 42.0
                                    w_R = (stop_start - center_end) / 42.0

                                    # Decode 6 left digits (L or G pattern)
                                    left_digits = []
                                    parity_str = ""
                                    left_ok = True
                                    for d_idx in range(6):
                                        slot_start = start_end + d_idx * 7.0 * w_L
                                        bits = ""
                                        for m_idx in range(7):
                                            pos = int(round(slot_start + (m_idx + 0.5) * w_L))
                                            bits += str(binary[pos]) if 0 <= pos < len(binary) else "0"

                                        if bits in L_LOOKUP:
                                            left_digits.append(L_LOOKUP[bits])
                                            parity_str += "L"
                                        elif bits in G_LOOKUP:
                                            left_digits.append(G_LOOKUP[bits])
                                            parity_str += "G"
                                        else:
                                            left_ok = False
                                            break

                                    if not left_ok or parity_str not in PARITY_LOOKUP:
                                        continue
                                    d1 = PARITY_LOOKUP[parity_str]

                                    # Decode 6 right digits (R pattern)
                                    right_digits = []
                                    right_ok = True
                                    for d_idx in range(6):
                                        slot_start = center_end + d_idx * 7.0 * w_R
                                        bits = ""
                                        for m_idx in range(7):
                                            pos = int(round(slot_start + (m_idx + 0.5) * w_R))
                                            bits += str(binary[pos]) if 0 <= pos < len(binary) else "0"

                                        if bits in R_LOOKUP:
                                            right_digits.append(R_LOOKUP[bits])
                                        else:
                                            right_ok = False
                                            break

                                    if not right_ok:
                                        continue

                                    cand = "".join(str(x) for x in [d1] + left_digits + right_digits)
                                    if validate_ean13(cand):
                                        return cand
    return None


def recover_damaged_ean13(
    image: Image.Image,
    num_scanlines: int = 40,
    try_standard_first: bool = True,
) -> Dict[str, Any]:
    """
    Main entrypoint for safe damaged EAN-13 barcode recovery.

    Safety contract:
    - Runs standard ZXing first. If standard decoder succeeds, returns
      'decoded_normally'.
    - If standard decoder fails, runs contrast normalization, skew alignment,
      and multi-scanline decoding.
    - Evaluates candidate consensus across independent scanlines.
    - Requires at least MIN_CONSENSUS_LINES (5) agreeing lines and unambiguous margin.
    - If ambiguous, weak, or invalid, returns 'abstained'.
    """
    # 1. Standard Decoder Pass
    if try_standard_first:
        std_result = decode_standard_zxing(image)
        if std_result:
            return {
                "status": "decoded_normally",
                "barcode": std_result,
                "standard_decoder_success": True,
                "confidence": 1.0,
                "detail": "Decoded cleanly by standard ZXing engine.",
                "original_crop": image_to_base64_png(image),
                "enhanced_crop": None,
                "skew_angle_deg": 0.0,
            }

    original_crop_b64 = image_to_base64_png(image)

    # 2. Preprocessing & Normalization
    normalized_im, norm_meta = normalize_contrast(image)
    detected_damage = list(norm_meta["detected_damage"])

    # 3. Skew Detection & Correction
    aligned_im, skew_angle = estimate_and_correct_skew(normalized_im)
    if abs(skew_angle) >= 2.0:
        detected_damage.append(f"skew_{skew_angle:.1f}deg")

    enhanced_crop_b64 = image_to_base64_png(aligned_im)

    # 4. Multi-Scanline Demodulation
    w, h = aligned_im.size
    y_step = max(1, int(h * 0.70 / max(1, num_scanlines)))
    y_coords = list(range(int(h * 0.15), int(h * 0.85), y_step))[:num_scanlines]

    votes: Dict[str, int] = {}
    valid_lines = 0

    for y in y_coords:
        row = [aligned_im.getpixel((x, y)) for x in range(w)]
        l_min, l_max = min(row), max(row)
        if l_max - l_min < 8:
            continue
        thresh = (l_min + l_max) / 2.0
        binary_row = [1 if p < thresh else 0 for p in row]
        code = decode_single_scanline(binary_row)
        if code:
            votes[code] = votes.get(code, 0) + 1
            valid_lines += 1

    # 5. Abstention Evaluation
    if not votes:
        return {
            "status": "abstained",
            "barcode": None,
            "standard_decoder_success": False,
            "detail": "Abstained: No scanlines exhibited valid EAN-13 guards and digit patterns.",
            "consensus_count": 0,
            "total_valid_scanlines": 0,
            "detected_damage": detected_damage,
            "skew_angle_deg": skew_angle,
            "original_crop": original_crop_b64,
            "enhanced_crop": enhanced_crop_b64,
        }

    sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
    top_code, top_count = sorted_votes[0]
    runner_up_count = sorted_votes[1][1] if len(sorted_votes) > 1 else 0

    # Rule 1: Minimum consensus support
    if top_count < MIN_CONSENSUS_LINES:
        return {
            "status": "abstained",
            "barcode": None,
            "standard_decoder_success": False,
            "detail": (
                f"Abstained: Insufficient scanline consensus ({top_count} lines agreed; "
                f"minimum required is {MIN_CONSENSUS_LINES})."
            ),
            "consensus_count": top_count,
            "total_valid_scanlines": valid_lines,
            "detected_damage": detected_damage,
            "skew_angle_deg": skew_angle,
            "original_crop": original_crop_b64,
            "enhanced_crop": enhanced_crop_b64,
        }

    # Rule 2: Unambiguous margin of victory
    if runner_up_count > 0 and top_count < runner_up_count * MIN_VICTORY_MARGIN_RATIO:
        return {
            "status": "abstained",
            "barcode": None,
            "standard_decoder_success": False,
            "detail": (
                f"Abstained: Ambiguous candidate readings (top candidate had {top_count} lines, "
                f"competing candidate had {runner_up_count} lines)."
            ),
            "consensus_count": top_count,
            "total_valid_scanlines": valid_lines,
            "detected_damage": detected_damage,
            "skew_angle_deg": skew_angle,
            "original_crop": original_crop_b64,
            "enhanced_crop": enhanced_crop_b64,
        }

    # Rule 3: Validated candidate accepted
    confidence = round(top_count / max(valid_lines, 1), 3)
    return {
        "status": "recovered_from_damaged_image",
        "barcode": top_code,
        "standard_decoder_success": False,
        "confidence": confidence,
        "consensus_count": top_count,
        "total_valid_scanlines": valid_lines,
        "runner_up_count": runner_up_count,
        "skew_angle_deg": skew_angle,
        "detected_damage": detected_damage,
        "detail": (
            f"Recovered safely via structure-aware pipeline ({top_count}/{len(y_coords)} scanline consensus, "
            f"skew correction: {skew_angle:.1f}°)."
        ),
        "original_crop": original_crop_b64,
        "enhanced_crop": enhanced_crop_b64,
    }
