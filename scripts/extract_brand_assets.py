"""
One-off: crop logo + partners + sample colors from the original brand JPGs.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "template" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

BRAND = Path(r"C:\Users\Admin\Downloads\10775a92-6f3c-475e-9e87-22a8226515b8.jpg")
FLYER = Path(r"C:\Users\Admin\Downloads\a9bb9275-0352-4447-a9be-9b3ba25cfab4.jpg")

# ---------- BRAND BOARD ----------
if BRAND.exists():
    im = Image.open(BRAND).convert("RGB")
    W, H = im.size
    print(f"Brand board: {W}x{H}")

    # Full logo + wordmark (wider + taller to capture all of "ГОРА ДОБРА")
    logo_crop = im.crop((30, 0, 450, 390))
    logo_crop.save(ASSETS / "brand_logo_full.png")
    print(f"saved brand_logo_full.png  ({logo_crop.size})")

    # Just the heart mark (no text) for use as a small icon
    heart_crop = im.crop((50, 0, 365, 270))
    heart_crop.save(ASSETS / "brand_logo_mark.png")
    print(f"saved brand_logo_mark.png  ({heart_crop.size})")

    # Sample palette from the 6 circles
    samples = {
        "gray":       (540, 90),
        "yellow":     (735, 90),
        "blue_light": (900, 90),
        "navy":       (540, 230),
        "blue_mid":   (735, 230),
        "cream":      (900, 230),
    }
    palette = {}
    for name, (x, y) in samples.items():
        r, g, b = im.getpixel((x, y))[:3]
        palette[name] = f"#{r:02X}{g:02X}{b:02X}"
        print(f"  {name}: {palette[name]}  @({x},{y})")

    pal_file = ROOT / "config" / "palette_sampled.json"
    pal_file.parent.mkdir(exist_ok=True)
    pal_file.write_text(
        "{\n" + ",\n".join(f'  "{k}": "{v}"' for k, v in palette.items()) + "\n}\n",
        encoding="utf-8",
    )
    print(f"saved palette to {pal_file}")

# ---------- FLYER (for partner logos strip) ----------
if FLYER.exists():
    im2 = Image.open(FLYER).convert("RGB")
    W2, H2 = im2.size
    print(f"\nFlyer: {W2}x{H2}")

    # Partners LOGOS ROW only (without "Дякуємо партнерам..." label — we localize that)
    # Estimate: the label is at ~y*0.83-0.88 of height, logos row at ~y*0.89-0.98
    logos_top = int(H2 * 0.88)
    logos_bot = int(H2 * 0.99)
    logos_row = im2.crop((0, logos_top, W2, logos_bot))
    logos_row.save(ASSETS / "partners_logos.png")
    print(f"saved partners_logos.png  ({logos_row.size})")

    # Full strip with label (fallback, if useful)
    top = int(H2 * 0.82)
    partners_strip = im2.crop((0, top, W2, H2))
    partners_strip.save(ASSETS / "partners_strip.png")
    print(f"saved partners_strip.png  ({partners_strip.size})")
