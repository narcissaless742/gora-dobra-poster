"""
Normalize all child illustrations to identical canvas + identical character height.
- Find content bbox (non-transparent pixels) in each PNG
- Crop to bbox, resize to target character height
- Paste onto a standard transparent canvas with consistent bottom padding
"""
from pathlib import Path
from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "template" / "assets"
CANVAS = 1024           # output square canvas (px)
CHAR_HEIGHT = 900       # character occupies this height
BOTTOM_PAD = 40         # pixels of transparent space at bottom
ALPHA_THRESHOLD = 20    # consider pixel "content" if alpha > this

TARGETS = [
    "child_2_6_m.png", "child_2_6_f.png",
    "child_7_10_m.png", "child_7_10_f.png",
    "child_11_14_m.png", "child_11_14_f.png",
    "child_15_18_m.png", "child_15_18_f.png",
]


def content_bbox(im: Image.Image):
    """Return bbox (l, t, r, b) of non-transparent pixels."""
    assert im.mode == "RGBA"
    alpha = im.split()[-1]
    # Binarize alpha above threshold
    mask = alpha.point(lambda p: 255 if p > ALPHA_THRESHOLD else 0)
    return mask.getbbox()


def normalize(path: Path):
    im = Image.open(path).convert("RGBA")

    # If this image has a near-opaque rectangular background (e.g., cream background),
    # the whole frame is "content". We detect that by seeing if almost every pixel is opaque.
    # In such cases we can't auto-crop meaningfully; skip (user should regenerate with transparency).
    alpha = im.split()[-1]
    # Count pixels with alpha > threshold
    opaque_ratio = sum(1 for p in alpha.getdata() if p > ALPHA_THRESHOLD) / (im.width * im.height)
    if opaque_ratio > 0.95:
        print(f"  [skip] {path.name}: looks like full-bg (opaque={opaque_ratio:.2%})")
        return

    bbox = content_bbox(im)
    if not bbox:
        print(f"  [skip] {path.name}: no content")
        return
    l, t, r, b = bbox
    cropped = im.crop(bbox)
    cw, ch = cropped.size

    # Scale so character height == CHAR_HEIGHT
    scale = CHAR_HEIGHT / ch
    new_w = max(1, int(round(cw * scale)))
    new_h = CHAR_HEIGHT
    resized = cropped.resize((new_w, new_h), Image.LANCZOS)

    # Create new canvas
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    x = (CANVAS - new_w) // 2
    y = CANVAS - new_h - BOTTOM_PAD
    canvas.paste(resized, (x, y), resized)

    canvas.save(path, "PNG", optimize=True)
    print(f"  [ok]   {path.name}: bbox {cw}x{ch} -> {new_w}x{new_h} (opaque ratio was {opaque_ratio:.1%})")


def main():
    print(f"Normalizing {len(TARGETS)} illustrations to {CANVAS}x{CANVAS}, char height {CHAR_HEIGHT}px")
    for name in TARGETS:
        p = ASSETS / name
        if not p.exists():
            print(f"  [missing] {name}")
            continue
        normalize(p)
    print("\nDone.")


if __name__ == "__main__":
    main()
