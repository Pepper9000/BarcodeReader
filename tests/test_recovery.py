"""
Unit tests for safe damaged EAN-13 recovery module (app/recovery.py).
"""

from io import BytesIO
import random
from PIL import Image, ImageDraw
import pytest

from app.recovery import (
    calculate_ean13_check_digit,
    decode_single_scanline,
    decode_standard_zxing,
    estimate_and_correct_skew,
    normalize_contrast,
    recover_damaged_ean13,
    validate_ean13,
)

L_PATTERNS = {0:'0001101', 1:'0011001', 2:'0010011', 3:'0111101', 4:'0100011', 5:'0110001', 6:'0101111', 7:'0111011', 8:'0110111', 9:'0001011'}
G_PATTERNS = {0:'0100111', 1:'0110011', 2:'0011011', 3:'0100001', 4:'0011101', 5:'0111001', 6:'0000101', 7:'0010001', 8:'0001001', 9:'0010111'}
R_PATTERNS = {0:'1110010', 1:'1100110', 2:'1101100', 3:'1000010', 4:'1011100', 5:'1001110', 6:'1010000', 7:'1000100', 8:'1001000', 9:'1110100'}
PARITY_PATTERNS = {0:'LLLLLL', 1:'LLGLGG', 2:'LLGGLG', 3:'LLGGGL', 4:'LGLLGG', 5:'LGGLLG', 6:'LGGGLL', 7:'LGLGLG', 8:'LGLGGL', 9:'LGGLGL'}


def generate_ean13(code: str, module_width=3, height=120, quiet_zone=30) -> Image.Image:
    """Generate a clean EAN-13 barcode bitmap."""
    d1 = int(code[0])
    left_digits = [int(c) for c in code[1:7]]
    right_digits = [int(c) for c in code[7:13]]
    parity = PARITY_PATTERNS[d1]
    modules = '101'
    for d, p in zip(left_digits, parity):
        modules += L_PATTERNS[d] if p == 'L' else G_PATTERNS[d]
    modules += '01010'
    for d in right_digits:
        modules += R_PATTERNS[d]
    modules += '101'

    img_w = len(modules) * module_width + quiet_zone * 2
    img = Image.new('L', (img_w, height), color=255)
    draw = ImageDraw.Draw(img)
    for i, m in enumerate(modules):
        if m == '1':
            x0 = quiet_zone + i * module_width
            draw.rectangle([x0, 0, x0 + module_width - 1, height], fill=0)
    return img


def test_calculate_check_digit():
    """Verify check digit calculation on known EAN-13 codes."""
    assert calculate_ean13_check_digit("400638133393") == 1
    assert calculate_ean13_check_digit("590123412345") == 7
    assert calculate_ean13_check_digit("001234567890") == 5


def test_validate_ean13():
    """Verify format and check digit validation."""
    assert validate_ean13("4006381333931") is True
    assert validate_ean13("4006381333932") is False  # wrong check digit
    assert validate_ean13("12345") is False  # too short
    assert validate_ean13("400638133393A") is False  # non-numeric


def test_standard_decoder_on_clean_image():
    """Verify standard ZXing decodes clean barcode."""
    code = "4006381333931"
    clean = generate_ean13(code)
    decoded = decode_standard_zxing(clean)
    assert decoded == code


def test_recover_low_contrast_damage():
    """Verify recovery pipeline recovers low-contrast barcode where standard ZXing fails."""
    code = "4006381333931"
    clean = generate_ean13(code)
    # Compress intensity range: bars at 125, background at 140
    w, h = clean.size
    lc = Image.new("L", (w, h))
    for y in range(h):
        for x in range(w):
            p = clean.getpixel((x, y))
            val = int(125 + (p / 255.0) * 15)
            lc.putpixel((x, y), val)

    # Standard ZXing fails on this image
    std = decode_standard_zxing(lc)
    assert std is None

    # Recovery pipeline succeeds
    res = recover_damaged_ean13(lc, try_standard_first=True)
    assert res["status"] == "recovered_from_damaged_image"
    assert res["barcode"] == code
    assert res["standard_decoder_success"] is False
    assert res["consensus_count"] >= 5


def test_recover_fading_damage():
    """Verify recovery pipeline recovers faded barcode with weak contrast."""
    code = "5901234123457"
    clean = generate_ean13(code)
    w, h = clean.size
    faded = Image.new("L", (w, h))
    # Fade bars so they are light gray (190-210) against white (255)
    for y in range(h):
        for x in range(w):
            p = clean.getpixel((x, y))
            val = int(200 + (p / 255.0) * 55)
            faded.putpixel((x, y), val)

    res = recover_damaged_ean13(faded, try_standard_first=True)
    assert res["status"] in ("recovered_from_damaged_image", "decoded_normally")
    assert res["barcode"] == code


def test_recover_skew_damage():
    """Verify recovery pipeline aligns and decodes skewed barcode."""
    code = "4006381333931"
    clean = generate_ean13(code)
    skewed = clean.rotate(25, expand=True, fillcolor=255)

    # Standard ZXing fails on 25-degree skew
    assert decode_standard_zxing(skewed) is None

    # Recovery pipeline succeeds
    res = recover_damaged_ean13(skewed, try_standard_first=True)
    assert res["status"] == "recovered_from_damaged_image"
    assert res["barcode"] == code
    assert abs(res["skew_angle_deg"]) > 10.0


def test_recover_scratched_damage():
    """Verify recovery pipeline recovers barcode with multiple scratch lines."""
    code = "4006381333931"
    clean = generate_ean13(code)
    scratched = clean.copy()
    draw = ImageDraw.Draw(scratched)
    # Cut scratch lines through 60% of scanlines
    for y in range(10, 75, 10):
        draw.line([0, y, clean.width, y + 3], fill=255, width=4)

    res = recover_damaged_ean13(scratched, try_standard_first=False)
    assert res["status"] == "recovered_from_damaged_image"
    assert res["barcode"] == code
    assert res["consensus_count"] >= 5


def test_recover_smudged_damage():
    """Verify recovery pipeline handles localized smudge blotches."""
    code = "4006381333931"
    clean = generate_ean13(code)
    smudged = clean.copy()
    draw = ImageDraw.Draw(smudged)
    # Smudge across lines 15..55 on left half
    draw.ellipse([50, 15, 130, 55], fill=0)

    res = recover_damaged_ean13(smudged, try_standard_first=False)
    assert res["status"] == "recovered_from_damaged_image"
    assert res["barcode"] == code
    assert res["consensus_count"] >= 5


def test_abstention_on_unrecoverable_blank():
    """Verify recovery pipeline safely abstains on blank image without guessing."""
    blank = Image.new("L", (300, 100), color=255)
    res = recover_damaged_ean13(blank, try_standard_first=True)
    assert res["status"] == "abstained"
    assert res["barcode"] is None
    assert "Abstained" in res["detail"]


def test_abstention_on_random_noise():
    """Verify recovery pipeline safely abstains on pure noise."""
    random.seed(42)
    w, h = 300, 120
    noise_im = Image.new("L", (w, h))
    for y in range(h):
        for x in range(w):
            noise_im.putpixel((x, y), random.randint(0, 255))
    res = recover_damaged_ean13(noise_im, try_standard_first=True)
    assert res["status"] == "abstained"
    assert res["barcode"] is None


def test_recover_skewed_code128_catalog_image():
    """Verify recovery pipeline recovers tilted Code 128 catalog image."""
    im = Image.open("tests/test_images/valid_demo_br01.png")
    skewed = im.rotate(20, expand=True, fillcolor=255)

    # Raw unaligned image cannot be decoded by standard ZXing
    assert decode_standard_zxing(skewed) is None

    # Pipeline deskews and recovers cleanly
    res = recover_damaged_ean13(skewed, try_standard_first=True)
    assert res["status"] == "recovered_from_damaged_image"
    assert res["barcode"] == "BR000001"
    assert abs(res["skew_angle_deg"]) >= 10.0
    assert res["original_crop"].startswith("data:image/png;base64,")
    assert res["enhanced_crop"].startswith("data:image/png;base64,")
    assert res["original_crop_base64"] is not None
    assert res["enhanced_crop_base64"] is not None
    assert res["scanline_consensus"] == res["consensus_count"]


def test_recover_response_fields_consistency():
    """Verify all expected frontend contract fields exist on abstained and recovered responses."""
    blank = Image.new("L", (200, 80), color=255)
    res = recover_damaged_ean13(blank, try_standard_first=True)
    assert "scanline_consensus" in res
    assert "consensus_count" in res
    assert "skew_angle" in res
    assert "skew_angle_deg" in res
    assert "original_crop" in res
    assert "original_crop_base64" in res
    assert "enhanced_crop" in res
    assert "enhanced_crop_base64" in res
    assert "detail" in res
    assert "abstention_reason" in res
