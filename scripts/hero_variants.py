"""Render 3 hero variants as PNG for visual comparison."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ASSETS = (ROOT / "template" / "assets").as_uri()
TMP = ROOT / "output" / "_hero_variants.html"
OUT_DIR = ROOT / "output"

HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700;900&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --yellow: #FCF859;
  --yellow-soft: #FFFED7;
  --blue-light: #B0D9EF;
  --blue-mid: #88C8F4;
  --navy: #141625;
  --muted: #717171;
  --cream: #FFFED7;
  --paper: #FFFFFF;
  --f-display: 'Unbounded', sans-serif;
  --f-body: 'Manrope', sans-serif;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--f-body); background: #F4F4F6; padding: 20px 0; }

.variant-wrap {
  width: 794px;
  margin: 0 auto 28px;
}
.label {
  font-family: var(--f-display);
  font-weight: 700;
  font-size: 12px;
  color: var(--navy);
  background: var(--yellow);
  padding: 8px 16px;
  letter-spacing: 0.08em;
  border: 1.5px solid var(--navy);
  border-radius: 4px 4px 0 0;
  display: inline-block;
}
.hero {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 16px;
  align-items: center;
  padding: 28px 32px;
  overflow: hidden;
  border: 1.5px solid var(--navy);
  border-radius: 0 4px 4px 4px;
}
.hero-text { min-width: 0; position: relative; z-index: 2; }
.kicker {
  font-family: var(--f-body);
  font-weight: 600;
  font-size: 9pt;
  color: var(--navy);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 5mm;
}
.name {
  font-family: var(--f-display);
  font-weight: 900;
  font-size: 54pt;
  line-height: 1.0;
  color: var(--navy);
  letter-spacing: -0.02em;
}
.meta {
  margin-top: 4mm;
  font-family: var(--f-display);
  font-weight: 700;
  font-size: 16pt;
  color: var(--navy);
}
.alt {
  margin-top: 3mm;
  font-weight: 500;
  font-size: 11pt;
  color: var(--muted);
  font-style: italic;
}
.illustration { position: relative; z-index: 2; }
.illustration img { display: block; }

/* === A === */
.hero-a { background: var(--paper); }
.hero-a .illustration img { width: 280px; height: auto; }

/* === B === */
.hero-b { background: var(--cream); }
.hero-b .illustration img { width: 320px; height: auto; margin: -30px 0 -30px 0; }

/* === E === (B розмір на білому) */
.hero-e { background: var(--paper); }
.hero-e .illustration img { width: 320px; height: auto; margin: -30px 0 -30px 0; }

/* === C === */
.hero-c { background: var(--paper); padding-bottom: 0; padding-right: 0; }
.hero-c::before {
  content: ""; position: absolute; right: 0; top: 0;
  width: 46%; height: 100%;
  background: var(--yellow);
  z-index: 0;
}
.hero-c .illustration {
  align-self: end;
  margin-bottom: 0;
  margin-right: 8px;
}
.hero-c .illustration img { width: 300px; height: auto; }

/* === D === (head & torso crop, large frame) === */
.hero-d { background: var(--yellow-soft); padding-right: 0; }
.hero-d .illustration {
  width: 220px; height: 100%;
  overflow: hidden;
  display: flex; align-items: flex-end;
  align-self: stretch;
}
.hero-d .illustration img {
  width: 340px; height: auto;
  margin-bottom: -40px;
  margin-right: -20px;
}
</style>
</head><body>

<div class="variant-wrap">
  <div class="label">ВАРІАНТ A · чистий білий</div>
  <div class="hero hero-a">
    <div class="hero-text">
      <div class="kicker">ДОПОМОЖИ ДИТИНІ З ДІАБЕТОМ · HILF EINEM KIND MIT DIABETES</div>
      <h1 class="name">Софія</h1>
      <div class="meta">8 років · Львів, Україна</div>
      <div class="alt">Sofia · 8 Jahre alt · Lviv, Ukraine</div>
    </div>
    <div class="illustration"><img src="__ASSETS__/child_7_10_f.png"></div>
  </div>
</div>

<div class="variant-wrap">
  <div class="label">ВАРІАНТ B · крем-жовтий фон, ілюстрація виривається</div>
  <div class="hero hero-b">
    <div class="hero-text">
      <div class="kicker">ДОПОМОЖИ ДИТИНІ З ДІАБЕТОМ · HILF EINEM KIND MIT DIABETES</div>
      <h1 class="name">Софія</h1>
      <div class="meta">8 років · Львів, Україна</div>
      <div class="alt">Sofia · 8 Jahre alt · Lviv, Ukraine</div>
    </div>
    <div class="illustration"><img src="__ASSETS__/child_7_10_f.png"></div>
  </div>
</div>

<div class="variant-wrap">
  <div class="label">ВАРІАНТ C · жовтий блок за ілюстрацією</div>
  <div class="hero hero-c">
    <div class="hero-text">
      <div class="kicker">ДОПОМОЖИ ДИТИНІ З ДІАБЕТОМ · HILF EINEM KIND MIT DIABETES</div>
      <h1 class="name">Софія</h1>
      <div class="meta">8 років · Львів, Україна</div>
      <div class="alt">Sofia · 8 Jahre alt · Lviv, Ukraine</div>
    </div>
    <div class="illustration"><img src="__ASSETS__/child_7_10_f.png"></div>
  </div>
</div>

<div class="variant-wrap">
  <div class="label">ВАРІАНТ E · розмір B на білому</div>
  <div class="hero hero-e">
    <div class="hero-text">
      <div class="kicker">ДОПОМОЖИ ДИТИНІ З ДІАБЕТОМ · HILF EINEM KIND MIT DIABETES</div>
      <h1 class="name">Софія</h1>
      <div class="meta">8 років · Львів, Україна</div>
      <div class="alt">Sofia · 8 Jahre alt · Lviv, Ukraine</div>
    </div>
    <div class="illustration"><img src="__ASSETS__/child_7_10_f.png"></div>
  </div>
</div>

<div class="variant-wrap">
  <div class="label">ВАРІАНТ D · кроп до пояса (крупний план)</div>
  <div class="hero hero-d">
    <div class="hero-text">
      <div class="kicker">ДОПОМОЖИ ДИТИНІ З ДІАБЕТОМ · HILF EINEM KIND MIT DIABETES</div>
      <h1 class="name">Софія</h1>
      <div class="meta">8 років · Львів, Україна</div>
      <div class="alt">Sofia · 8 Jahre alt · Lviv, Ukraine</div>
    </div>
    <div class="illustration"><img src="__ASSETS__/child_7_10_f.png"></div>
  </div>
</div>

</body></html>
""".replace("__ASSETS__", ASSETS)


def main():
    TMP.write_text(HTML, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 850, "height": 2000})
        page.goto(TMP.resolve().as_uri(), wait_until="networkidle")

        # Screenshot each variant separately
        for i, name in enumerate(["A", "B", "C", "E", "D"]):
            el = page.locator(".variant-wrap").nth(i)
            out = OUT_DIR / f"hero_variant_{name}.png"
            el.screenshot(path=str(out))
            print(f"saved {out.name}")

        browser.close()

    TMP.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
