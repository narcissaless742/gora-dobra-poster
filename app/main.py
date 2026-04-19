"""
Flask app for Gora Dobra patronage poster generator.
- Form UI for filling in one child's info
- Auto-translate UA -> DE (editable)
- 1-5 monthly items
- Age bucket + gender -> illustration picked automatically
- Live preview + PDF download
"""
from pathlib import Path
import json
import uuid

from flask import Flask, render_template, request, jsonify, send_file, abort, Response
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from deep_translator import GoogleTranslator


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "template"
ASSETS_DIR = TEMPLATE_DIR / "assets"
OUTPUT_DIR = ROOT / "output"
FUND_CONFIG = ROOT / "config" / "fund.json"


def load_fund():
    if FUND_CONFIG.exists():
        return json.loads(FUND_CONFIG.read_text(encoding="utf-8"))
    return {}

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

poster_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


# ---------- helpers ----------

def age_bucket(age: int) -> str:
    if age <= 6:   return "2_6"
    if age <= 10:  return "7_10"
    if age <= 14:  return "11_14"
    return "15_18"


def ukr_age_word(age: int) -> str:
    """1 рік, 2-4 роки, 5+ років (with 11-14 exception)."""
    if age % 100 in (11, 12, 13, 14):
        return "років"
    last = age % 10
    if last == 1: return "рік"
    if last in (2, 3, 4): return "роки"
    return "років"


def pick_illustration(bucket: str, gender: str) -> str:
    g = (gender or "m").strip().lower()[:1]
    for ext in ("png", "svg"):
        fname = f"child_{bucket}_{g}.{ext}"
        if (ASSETS_DIR / fname).exists():
            return f"assets/{fname}"
    return "assets/logo.svg"


def build_context(data: dict) -> dict:
    age = int(data.get("age") or 0)
    bucket = age_bucket(age)
    gender = data.get("gender", "m")
    return {
        "ref_id": (data.get("ref_id") or f"GD-{uuid.uuid4().hex[:6].upper()}"),
        "name_ua": data.get("name_ua", "").strip(),
        "name_de": data.get("name_de", "").strip(),
        "age": age,
        "age_word_ua": (data.get("age_word_ua") or ukr_age_word(age)).strip() if data.get("age_word_ua") else ukr_age_word(age),
        "age_word_de": (data.get("age_word_de") or "Jahre alt").strip() if data.get("age_word_de") else "Jahre alt",
        "city_ua": data.get("city_ua", "").strip(),
        "city_de": data.get("city_de", "").strip(),
        "story_ua": data.get("story_ua", "").strip(),
        "story_de": data.get("story_de", "").strip(),
        "items": [
            {
                "ua": i.get("ua", "").strip(),
                "de": i.get("de", "").strip(),
                "price": str(i.get("price", "")).strip(),
            }
            for i in (data.get("items") or [])
            if (i.get("ua") or i.get("de"))
        ],
        "amount": data.get("amount", "").strip() if isinstance(data.get("amount"), str) else data.get("amount", ""),
        "fund": load_fund(),
        "age_bucket": bucket,
        "illustration": pick_illustration(bucket, gender),
    }


PREVIEW_FIT_SNIPPET = """<base href="/template/">
<style>
@media screen {
  html { height: 100%; overflow: hidden; }
  body { margin: 0; height: 100%; overflow: hidden;
         display: flex; justify-content: center; align-items: center;
         background: #EEE; }
  .page { transform-origin: center center; flex-shrink: 0;
          box-shadow: 0 4px 24px rgba(0,0,0,0.12); }
}
</style>
<script>
(function() {
  function fit() {
    var page = document.querySelector('.page');
    if (!page) return;
    var w = window.innerWidth, h = window.innerHeight;
    var pw = page.offsetWidth, ph = page.offsetHeight;
    if (!pw || !ph) return;
    var s = Math.min(w / pw, h / ph) * 0.98;
    page.style.transform = 'scale(' + s + ')';
  }
  window.addEventListener('load', fit);
  window.addEventListener('resize', fit);
  setTimeout(fit, 50);
  setTimeout(fit, 300);
  setTimeout(fit, 800);
})();
</script>"""


def render_poster_html(ctx: dict, inject_base: bool = False) -> str:
    tmpl = poster_env.get_template("template.html")
    html = tmpl.render(**ctx)
    if inject_base:
        # For iframe preview: resolve relative paths + fit to viewport without scrolling
        html = html.replace("<head>", "<head>" + PREVIEW_FIT_SNIPPET, 1)
    return html


# ---------- routes ----------

@app.route("/")
def index():
    return render_template("editor.html")


@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"translated": ""})
    try:
        out = GoogleTranslator(source="uk", target="de").translate(text)
        return jsonify({"translated": out or ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/preview", methods=["POST"])
def api_preview():
    data = request.get_json() or {}
    ctx = build_context(data)
    html = render_poster_html(ctx, inject_base=True)
    return Response(html, mimetype="text/html")


@app.route("/template/<path:filename>")
def template_files(filename):
    file = TEMPLATE_DIR / filename
    if not file.exists() or not file.is_file():
        abort(404)
    return send_file(file)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json() or {}
    ctx = build_context(data)
    html = render_poster_html(ctx, inject_base=False)

    render_tmp = TEMPLATE_DIR / "_render.html"
    render_tmp.write_text(html, encoding="utf-8")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{ctx['ref_id']}.pdf"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(render_tmp.resolve().as_uri(), wait_until="networkidle")
            page.pdf(
                path=str(out_path),
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
    finally:
        render_tmp.unlink(missing_ok=True)

    return send_file(out_path, as_attachment=True, download_name=f"{ctx['ref_id']}.pdf")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
