"""
Barcode Label Generator for BarcodeReader (LDAM Academic Project).

Generates:
1. Individual high-resolution PNG labels for all 16 demo products.
2. A single-page A4 printable PDF containing all 16 labels in a 2x8 grid (100% scale).
3. A large-format 2-page A4 printable PDF (2x4 grid per page) for product mockups.
4. A catalog summary markdown manifest in generated/barcodes/MANIFEST.md.

Uses app/catalogue.py as the single source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.catalogue import default_catalogue

OUTPUT_DIR = BASE_DIR / "generated" / "barcodes"
PNG_DIR = OUTPUT_DIR / "labels_png"

# Code 128 Symbol Patterns (Subset B)
CODE128_PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112"
]


def encode_code128_modules(text: str) -> List[int]:
    """
    Encode an ASCII string into Code 128 (Subset B) binary modules.
    Returns list of 1s (bars) and 0s (spaces).
    """
    values = [104]  # Start B
    for ch in text:
        values.append(ord(ch) - 32)
    checksum = (values[0] + sum(i * v for i, v in enumerate(values[1:], 1))) % 103
    values.append(checksum)
    values.append(106)  # Stop

    modules: List[int] = []
    for val in values:
        pat = CODE128_PATTERNS[val]
        is_bar = True
        for digit in pat:
            w = int(digit)
            modules.extend([1 if is_bar else 0] * w)
            is_bar = not is_bar
    return modules


def get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont:
    """Load system font with graceful fallback for Windows and Linux."""
    candidates = []
    if sys.platform == "win32":
        if mono:
            candidates = ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"]
        elif bold:
            candidates = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
        else:
            candidates = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
    else:
        # Linux / Unix candidates (e.g. Debian/Ubuntu on Render, Railway, Fly.io)
        if mono:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            ]
        elif bold:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ]

    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_label_image(
    product: Dict[str, Any],
    width: int = 1100,
    height: int = 380,
    module_scale: int = 5,
    bar_height: int = 160,
    draw_cut_border: bool = True,
) -> Image.Image:
    """
    Render a single barcode label containing:
    - Category badge
    - Product ID
    - Product name
    - Code 128 barcode with ample quiet zones
    - Human-readable barcode string below
    - Dashed cut outline
    """
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 1. Dashed cut boundary
    if draw_cut_border:
        dash_len = 8
        gap_len = 6
        border_color = (180, 195, 215)
        # Top and Bottom
        for x in range(4, width - 4, dash_len + gap_len):
            draw.line([(x, 4), (min(x + dash_len, width - 4), 4)], fill=border_color, width=1)
            draw.line([(x, height - 5), (min(x + dash_len, width - 5), height - 5)], fill=border_color, width=1)
        # Left and Right
        for y in range(4, height - 4, dash_len + gap_len):
            draw.line([(4, y), (4, min(y + dash_len, height - 4))], fill=border_color, width=1)
            draw.line([(width - 5, y), (width - 5, min(y + dash_len, height - 4))], fill=border_color, width=1)

    # 2. Typography
    font_cat = get_font(20, bold=True)
    font_id = get_font(20, bold=True)
    font_name = get_font(25, bold=True)
    font_code = get_font(30, bold=True, mono=True)

    # 3. Category Badge (Top Left)
    cat_name = product.get("category_name", "UNKNOWN CATEGORY").upper()
    cat_bbox = draw.textbbox((0, 0), cat_name, font=font_cat)
    badge_w = cat_bbox[2] - cat_bbox[0] + 24
    badge_h = cat_bbox[3] - cat_bbox[1] + 12
    badge_x, badge_y = 28, 22
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
        radius=5,
        fill=(37, 99, 235),  # Cobalt Blue
    )
    draw.text((badge_x + 12, badge_y + 4), cat_name, font=font_cat, fill=(255, 255, 255))

    # 4. Product ID (Top Right)
    prod_id_text = f"ID: {product.get('id', '—')}"
    id_bbox = draw.textbbox((0, 0), prod_id_text, font=font_id)
    id_w = id_bbox[2] - id_bbox[0]
    draw.text((width - 28 - id_w, 26), prod_id_text, font=font_id, fill=(71, 85, 105))

    # 5. Product Name
    prod_name = product.get("name", "Product Name")
    draw.text((28, 70), prod_name, font=font_name, fill=(15, 23, 42))

    # 6. Code 128 Barcode Bars
    barcode_str = product.get("barcode", "BR000000")
    modules = encode_code128_modules(barcode_str)
    total_bar_width = len(modules) * module_scale
    start_x = (width - total_bar_width) // 2
    barcode_y = 125

    for i, bit in enumerate(modules):
        if bit == 1:
            x_pos = start_x + (i * module_scale)
            draw.rectangle(
                [(x_pos, barcode_y), (x_pos + module_scale - 1, barcode_y + bar_height)],
                fill=(0, 0, 0),
            )

    # 7. Human-readable Barcode Text
    code_bbox = draw.textbbox((0, 0), barcode_str, font=font_code)
    code_w = code_bbox[2] - code_bbox[0]
    code_x = (width - code_w) // 2
    code_y = barcode_y + bar_height + 12
    draw.text((code_x, code_y), barcode_str, font=font_code, fill=(0, 0, 0))

    return img


def generate_single_page_a4_pdf(
    products: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    """
    Generate a single A4 PDF page (2480x3508 @ 300 DPI) containing all 16 labels in a 2x8 grid.
    Suitable for 100% scale printing.
    """
    page_w, page_h = 2480, 3508  # A4 @ 300 DPI
    page = Image.new("RGB", (page_w, page_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(page)

    # Page Header
    font_page_title = get_font(38, bold=True)
    font_page_sub = get_font(22, bold=False)
    font_footer = get_font(18, bold=False)

    draw.text((100, 50), "BarcodeReader — Demo Product Barcode Labels Sheet", font=font_page_title, fill=(15, 23, 42))
    draw.text(
        (100, 105),
        "Logic Design and Microprocessor (LDAM) Academic Project • 16 Demo Labels • Code 128 • Print at 100% Scale",
        font=font_page_sub,
        fill=(71, 85, 105),
    )
    draw.line([(100, 145), (page_w - 100, 145)], fill=(226, 232, 240), width=2)

    # Grid Specifications (2 columns x 8 rows)
    label_w = 1110
    label_h = 380
    col_spacing = 60
    row_spacing = 22
    start_x = 100
    start_y = 175

    for idx, prod in enumerate(products):
        row = idx // 2
        col = idx % 2
        x = start_x + col * (label_w + col_spacing)
        y = start_y + row * (label_h + row_spacing)

        label_img = render_label_image(
            prod,
            width=label_w,
            height=label_h,
            module_scale=5,
            bar_height=160,
            draw_cut_border=True,
        )
        page.paste(label_img, (x, y))

    # Page Footer
    footer_text = "Instructions: Cut along dashed borders. Compatible with USB scanners, webcam, and mobile camera scanning."
    draw.line([(100, page_h - 75), (page_w - 100, page_h - 75)], fill=(226, 232, 240), width=1)
    draw.text((100, page_h - 55), footer_text, font=font_footer, fill=(100, 116, 139))
    draw.text((page_w - 360, page_h - 55), "A4 Standard (210 × 297 mm)", font=font_footer, fill=(100, 116, 139))

    # Save PDF
    page.save(output_path, "PDF", resolution=300.0)


def generate_large_format_a4_pdf(
    products: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    """
    Generate a 2-page A4 PDF (2x4 grid per page, 8 labels each) for larger physical mockups.
    """
    page_w, page_h = 2480, 3508
    label_w = 1110
    label_h = 720
    col_spacing = 60
    row_spacing = 40
    start_x = 100
    start_y = 180

    font_page_title = get_font(38, bold=True)
    font_page_sub = get_font(22, bold=False)
    font_footer = get_font(18, bold=False)

    pages: List[Image.Image] = []

    for page_idx in range(2):
        page = Image.new("RGB", (page_w, page_h), color=(255, 255, 255))
        draw = ImageDraw.Draw(page)

        page_products = products[page_idx * 8 : (page_idx + 1) * 8]

        # Header
        draw.text(
            (100, 50),
            f"BarcodeReader — Large Product Labels (Sheet {page_idx + 1} of 2)",
            font=font_page_title,
            fill=(15, 23, 42),
        )
        draw.text(
            (100, 105),
            f"Products {page_idx * 8 + 1} to {(page_idx + 1) * 8} of 16 • Large Format for Product Boxes & Garment Tags",
            font=font_page_sub,
            fill=(71, 85, 105),
        )
        draw.line([(100, 145), (page_w - 100, 145)], fill=(226, 232, 240), width=2)

        for idx, prod in enumerate(page_products):
            row = idx // 2
            col = idx % 2
            x = start_x + col * (label_w + col_spacing)
            y = start_y + row * (label_h + row_spacing)

            # Larger label image with taller barcode
            lbl = render_label_image(
                prod,
                width=label_w,
                height=label_h,
                module_scale=5,
                bar_height=420,  # extra tall barcode for long distance camera scanning
                draw_cut_border=True,
            )
            page.paste(lbl, (x, y))

        draw.line([(100, page_h - 75), (page_w - 100, page_h - 75)], fill=(226, 232, 240), width=1)
        draw.text((100, page_h - 55), f"Page {page_idx + 1} of 2 • A4 Standard (100% Scale)", font=font_footer, fill=(100, 116, 139))
        pages.append(page)

    pages[0].save(output_path, "PDF", resolution=300.0, save_all=True, append_images=pages[1:])


def generate_all_labels() -> Dict[str, Any]:
    """Generate all individual PNG labels, PDF sheets, and markdown manifest."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)

    products = default_catalogue.get_products(resolve_categories=True)
    if len(products) != 16:
        raise ValueError(f"Expected 16 demo products from catalogue, found {len(products)}")

    generated_pngs: List[Path] = []

    # 1. Individual High-Resolution PNGs
    for prod in products:
        filename = f"{prod['barcode']}_{prod['id']}.png"
        filepath = PNG_DIR / filename
        label_img = render_label_image(
            prod,
            width=1200,
            height=420,
            module_scale=6,
            bar_height=180,
            draw_cut_border=True,
        )
        label_img.save(filepath, "PNG", dpi=(300, 300))
        generated_pngs.append(filepath)

    # 2. Single-Page A4 Grid PDF (Primary Sheet)
    primary_pdf_path = OUTPUT_DIR / "demo_labels_a4.pdf"
    generate_single_page_a4_pdf(products, primary_pdf_path)

    # 3. Large-Format 2-Page A4 PDF
    large_pdf_path = OUTPUT_DIR / "demo_labels_large_a4.pdf"
    generate_large_format_a4_pdf(products, large_pdf_path)

    # 4. Generate Markdown Manifest
    manifest_path = OUTPUT_DIR / "MANIFEST.md"
    manifest_lines = [
        "# Demo Barcode Labels Manifest",
        "",
        "This directory contains high-resolution printable barcode labels generated from `app/data/products.json` and `app/data/categories.json` for the **LDAM BarcodeReader** project.",
        "",
        "## Printable PDF Files",
        "",
        f"- **Primary A4 Sheet (16-in-1):** [`demo_labels_a4.pdf`](file:///{primary_pdf_path.as_posix()})",
        "  - Contains all 16 demo labels on a single A4 page in a 2×8 grid (100% scale).",
        f"- **Large Format A4 Sheet (8-in-1 × 2 Pages):** [`demo_labels_large_a4.pdf`](file:///{large_pdf_path.as_posix()})",
        "  - Contains all 16 labels across 2 pages in a 2×4 grid with extra-tall barcodes for product boxes.",
        "",
        "## Individual High-Resolution PNG Labels",
        "",
        "| Barcode | Product ID | Category ID | Category Name | Product Name | Label File |",
        "| :--- | :--- | :---: | :--- | :--- | :--- |",
    ]

    for prod in products:
        fn = f"{prod['barcode']}_{prod['id']}.png"
        manifest_lines.append(
            f"| `{prod['barcode']}` | `{prod['id']}` | {prod['category_id']} | {prod['category_name']} | {prod['name']} | [`{fn}`](file:///{(PNG_DIR / fn).as_posix()}) |"
        )

    manifest_lines.extend([
        "",
        "## Printing & Scanning Instructions",
        "",
        "1. Open `demo_labels_a4.pdf` in any PDF viewer or browser.",
        "2. In the print dialog, select **Page Scaling: None** (or **Actual Size / 100%**). Do NOT choose 'Fit to Page'.",
        "3. Print on plain A4 paper (or adhesive label paper).",
        "4. Cut along the dashed guidelines using scissors or a paper cutter.",
        "5. Test using the web application's **Upload Image** tab or phone camera scanning.",
    ])

    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")

    return {
        "status": "success",
        "products_count": len(products),
        "primary_pdf": str(primary_pdf_path),
        "large_pdf": str(large_pdf_path),
        "pngs_count": len(generated_pngs),
        "manifest": str(manifest_path),
    }


if __name__ == "__main__":
    result = generate_all_labels()
    print("Label generation complete:")
    print(f"  Products: {result['products_count']}")
    print(f"  Primary PDF: {result['primary_pdf']}")
    print(f"  Large PDF: {result['large_pdf']}")
    print(f"  Individual PNGs: {result['pngs_count']}")
    print(f"  Manifest: {result['manifest']}")
