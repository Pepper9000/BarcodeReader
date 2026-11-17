"""
Generate multi-format, multi-resolution favicons and app icons for BarcodeReader.

Processes the source image by centering to a square, antialiasing the squircle
corners to clean transparency (removing external screenshot/canvas gray margins),
and exporting standard sizes:
  - favicon.ico (16x16, 32x32, 48x48)
  - favicon-16x16.png
  - favicon-32x32.png
  - favicon.png
  - apple-touch-icon.png (180x180)
  - icon-192.png
  - icon-512.png
"""

from collections import deque
from pathlib import Path
import shutil
from PIL import Image, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"

DEFAULT_SOURCE = Path(
    r"C:\Users\admin\.gemini\antigravity\brain\8b231be3-c117-4a12-9aad-87c0efb70b30\.user_uploaded\media_1794942964788_0a70e31a.jpg"
)


def generate_favicons(source_path: Path | None = None) -> None:
    src = source_path or DEFAULT_SOURCE
    if not src.exists():
        fallback_src = STATIC_DIR / "favicon_source.jpg"
        if fallback_src.exists():
            src = fallback_src
        else:
            raise FileNotFoundError(f"Source favicon image not found at: {src}")

    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Preserve original source image in static directory
    dest_source = STATIC_DIR / "favicon_source.jpg"
    if src != dest_source:
        shutil.copy2(src, dest_source)

    # Open image
    im = Image.open(src).convert("RGBA")
    w, h = im.size

    # Symmetrically crop to square centered on reticle
    size = min(w, h)
    left = (w - size) // 2
    top = (h - size) // 2
    im_sq = im.crop((left, top, left + size, top + size))
    sw, sh = im_sq.size

    pixels = im_sq.load()
    visited = set()
    q = deque([(0, 0), (sw - 1, 0), (0, sh - 1), (sw - 1, sh - 1)])
    for pt in q:
        visited.add(pt)

    # Identify outer canvas gray background: medium brightness, low saturation
    def is_outer_bg(r: int, g: int, b: int) -> bool:
        brightness = (r + g + b) / 3
        saturation = max(r, g, b) - min(r, g, b)
        return brightness > 65 and saturation < 25

    mask = Image.new("L", (sw, sh), 255)
    mask_pixels = mask.load()

    while q:
        x, y = q.popleft()
        r, g, b, _ = pixels[x, y]
        if is_outer_bg(r, g, b):
            mask_pixels[x, y] = 0
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < sw and 0 <= ny < sh and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    q.append((nx, ny))

    # Antialias corner boundary
    mask_smooth = mask.filter(ImageFilter.GaussianBlur(radius=1.0))
    mask_smooth_pixels = mask_smooth.load()

    # Dark navy squircle background color for edge defringing
    bg_r, bg_g, bg_b = (16, 24, 43)

    master = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    master_pixels = master.load()

    for y in range(sh):
        for x in range(sw):
            a = mask_smooth_pixels[x, y]
            if a > 0:
                r, g, b, _ = pixels[x, y]
                # Defringe gray border towards navy background
                if a < 250 and is_outer_bg(r, g, b):
                    r, g, b = bg_r, bg_g, bg_b
                master_pixels[x, y] = (r, g, b, a)

    # 1. High-resolution master 512x512
    im_512 = master.resize((512, 512), Image.Resampling.LANCZOS)
    im_512.save(STATIC_DIR / "icon-512.png", format="PNG")

    # 2. PWA icon 192x192
    im_192 = master.resize((192, 192), Image.Resampling.LANCZOS)
    im_192.save(STATIC_DIR / "icon-192.png", format="PNG")

    # 3. Apple Touch Icon 180x180
    im_180 = master.resize((180, 180), Image.Resampling.LANCZOS)
    im_180.save(STATIC_DIR / "apple-touch-icon.png", format="PNG")

    # 4. Retina Favicon 32x32
    im_32 = master.resize((32, 32), Image.Resampling.LANCZOS)
    im_32.save(STATIC_DIR / "favicon-32x32.png", format="PNG")
    im_32.save(STATIC_DIR / "favicon.png", format="PNG")

    # 5. Standard Favicon 16x16
    im_16 = master.resize((16, 16), Image.Resampling.LANCZOS)
    im_16.save(STATIC_DIR / "favicon-16x16.png", format="PNG")

    # 6. Multi-resolution favicon.ico (16, 32, 48)
    master.save(
        STATIC_DIR / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )

    print(f"Favicons successfully generated in {STATIC_DIR}:")
    for fname in [
        "favicon.ico",
        "favicon.png",
        "favicon-32x32.png",
        "favicon-16x16.png",
        "apple-touch-icon.png",
        "icon-192.png",
        "icon-512.png",
        "favicon_source.jpg",
    ]:
        p = STATIC_DIR / fname
        print(f"  - {fname} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    generate_favicons()
