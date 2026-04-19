"""
Generate patronage poster PDFs from a CSV of children.
CSV -> Jinja2 HTML -> Playwright-rendered PDF (one PDF per child).
"""
import asyncio
import csv
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "template"
ASSETS_DIR = TEMPLATE_DIR / "assets"
DATA_CSV = ROOT / "data" / "children.csv"
OUTPUT_DIR = ROOT / "output"
RENDER_TMP = TEMPLATE_DIR / "_render.html"


def age_bucket(age: int) -> str:
    """Map age to one of 4 buckets used for illustration selection."""
    if age <= 6:   return "2_6"
    if age <= 10:  return "7_10"
    if age <= 14:  return "11_14"
    return "15_18"


def pick_illustration(bucket: str, gender: str) -> str:
    """Prefer PNG (real art), fallback to SVG (stub). Returns relative path."""
    gender = (gender or "m").strip().lower()[:1]  # 'm' or 'f'
    for ext in ("png", "svg"):
        fname = f"child_{bucket}_{gender}.{ext}"
        if (ASSETS_DIR / fname).exists():
            return f"assets/{fname}"
    return "assets/logo.svg"  # safe fallback


def parse_items(raw: str):
    items = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "|" in chunk:
            ua, de = chunk.split("|", 1)
        else:
            ua = de = chunk
        items.append({"ua": ua.strip(), "de": de.strip()})
    return items


def load_children(csv_path: Path):
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["items"] = parse_items(row.get("items", ""))
            age = int(row.get("age", "0"))
            bucket = age_bucket(age)
            row["age_bucket"] = bucket
            row["illustration"] = pick_illustration(bucket, row.get("gender", "m"))
            yield row


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    tmpl = env.get_template("template.html")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        for row in load_children(DATA_CSV):
            html = tmpl.render(**row)
            RENDER_TMP.write_text(html, encoding="utf-8")
            file_url = RENDER_TMP.resolve().as_uri()

            await page.goto(file_url, wait_until="networkidle")
            out_path = OUTPUT_DIR / f"{row['ref_id']}.pdf"
            print(f"[render] {out_path.name}  ({row['name_ua']}, {row['age']} y, {row['illustration']})")

            await page.pdf(
                path=str(out_path),
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )

        await browser.close()

    if RENDER_TMP.exists():
        RENDER_TMP.unlink()

    print(f"\nDone. PDFs in: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
