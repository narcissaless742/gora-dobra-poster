"""
Flask app for Gora Dobra patronage poster generator.
- Form UI for filling in one child's info
- Auto-translate UA -> DE (editable)
- 1-5 monthly items
- Age bucket + gender -> illustration picked automatically
- Live preview + PDF download
- Social media PNG exports (Story 1080x1920, Post1/Post2 1080x1080)
"""
import io
import json
import platform
import re
import uuid
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, abort, Response
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from deep_translator import GoogleTranslator


_LAUNCH_KWARGS_CACHE: dict | None = None


def _playwright_launch_kwargs() -> dict:
    """Workaround: on some Windows installs Playwright reports its default
    chromium binary as missing even though chrome-headless-shell.exe is on disk
    and runnable. We resolve the version Playwright itself expects (via its
    default executable_path) and point launch() at the matching headless-shell.
    On Linux (Render) this returns {} -> default."""
    global _LAUNCH_KWARGS_CACHE
    if _LAUNCH_KWARGS_CACHE is not None:
        return _LAUNCH_KWARGS_CACHE
    if platform.system() != "Windows":
        _LAUNCH_KWARGS_CACHE = {}
        return _LAUNCH_KWARGS_CACHE

    import re
    try:
        with sync_playwright() as p:
            default_exe = p.chromium.executable_path
        m = re.search(r"chromium-(\d+)", default_exe)
        if m:
            version = m.group(1)
            base = Path.home() / "AppData" / "Local" / "ms-playwright"
            exe = base / f"chromium_headless_shell-{version}" / "chrome-headless-shell-win64" / "chrome-headless-shell.exe"
            if exe.is_file():
                _LAUNCH_KWARGS_CACHE = {"executable_path": str(exe)}
                return _LAUNCH_KWARGS_CACHE
    except Exception:
        pass

    _LAUNCH_KWARGS_CACHE = {}
    return _LAUNCH_KWARGS_CACHE


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "template"
ASSETS_DIR = TEMPLATE_DIR / "assets"
OUTPUT_DIR = ROOT / "output"
FUND_CONFIG = ROOT / "config" / "fund.json"
PRESETS_CONFIG = ROOT / "config" / "presets.json"
LOCATIONS_CONFIG = ROOT / "config" / "locations.json"
COUNTER_FILE = ROOT / "data" / "counter.json"

FUND_DEFAULTS = {
    "cta_ua":      "Станьте патроном цієї дитини",
    "cta_de":      "Werden Sie Pate für dieses Kind",
    "partners_ua": "Дякуємо партнерам за підтримку",
    "partners_de": "Mit Dankbarkeit an unsere Partner",
}

SOCIAL_FORMATS = {
    "story": ("social_story.html", 1080, 1920),
    "post1": ("social_post1.html", 1080, 1080),
    "post2": ("social_post2.html", 1080, 1080),
}


def load_fund():
    data = {}
    if FUND_CONFIG.exists():
        data = json.loads(FUND_CONFIG.read_text(encoding="utf-8"))
    for k, v in FUND_DEFAULTS.items():
        data.setdefault(k, v)
    return data


def load_presets():
    if PRESETS_CONFIG.exists():
        try:
            return json.loads(PRESETS_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"groups": []}


def load_locations():
    if LOCATIONS_CONFIG.exists():
        try:
            return json.loads(LOCATIONS_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"regions": [], "cities": []}


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


def get_partner_logos() -> list | None:
    logos = []
    for i in range(1, 4):
        for ext in ("png", "jpg", "jpeg", "svg", "webp"):
            f = ASSETS_DIR / f"partner_{i}.{ext}"
            if f.exists():
                logos.append(f"assets/partner_{i}.{ext}")
                break
    return logos if logos else None


def _format_id_n(n: int) -> str:
    """Convert a 1-based counter value into a 4-char ID: <letter><3 digits>.
    n=1 -> A001, n=999 -> A999, n=1000 -> B001, ..., n=25974 -> Z999."""
    if n < 1:
        n = 1
    n0 = n - 1
    letter_idx = n0 // 999
    digit = (n0 % 999) + 1
    if letter_idx > 25:
        # Counter overflow past Z999 — clamp to Z999 (warn elsewhere if needed).
        letter_idx = 25
        digit = 999
    return f"{chr(ord('A') + letter_idx)}{digit:03d}"


_REF_ID_RE = re.compile(r"^[A-Z]\d{3}$")


def _fmt_id(raw) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        return _format_id_n(1)
    if _REF_ID_RE.match(s):
        return s
    if s.isdigit():
        return _format_id_n(int(s))
    return s


_UA_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g",
    "д": "d", "е": "e", "є": "ie", "ж": "zh", "з": "z",
    "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ь": "", "ю": "iu", "я": "ia", "'": "", "ʼ": "", "’": "",
}


def _translit_ua(text: str) -> str:
    out = []
    for ch in text:
        lo = ch.lower()
        if lo in _UA_TRANSLIT:
            t = _UA_TRANSLIT[lo]
            out.append(t.title() if ch.isupper() else t)
        else:
            out.append(ch)
    return "".join(out)


def _file_basename(name_de: str, name_ua: str, ref_id: str) -> str:
    """Build a filesystem-safe file basename: '<Name>_<ID>'.
    Prefers name_de (already latinized via translation); falls back to a
    transliteration of name_ua; then to 'poster'."""
    raw = (name_de or "").strip() or _translit_ua((name_ua or "").strip())
    cleaned = re.sub(r'[\\/:*?"<>|]+', "", raw)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("_")
    cleaned = cleaned[:40] or "poster"
    return f"{cleaned}_{ref_id}"


def _read_counter() -> int:
    try:
        if COUNTER_FILE.exists():
            data = json.loads(COUNTER_FILE.read_text(encoding="utf-8"))
            n = int(data.get("next_id", 1))
            return n if n >= 1 else 1
    except (json.JSONDecodeError, ValueError, OSError):
        pass
    return 1


def _write_counter(n: int) -> None:
    COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    COUNTER_FILE.write_text(
        json.dumps({"next_id": n}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def reserve_next_id() -> str:
    n = _read_counter()
    _write_counter(n + 1)
    return _format_id_n(n)


def peek_next_id() -> str:
    return _format_id_n(_read_counter())


def resolve_ref_id(data: dict, *, allow_reserve: bool) -> str:
    raw = (data.get("ref_id") or "").strip()
    if raw:
        return _fmt_id(raw)
    return reserve_next_id() if allow_reserve else peek_next_id()


def build_context(data: dict, *, allow_reserve: bool = False) -> dict:
    age = int(data.get("age") or 0)
    bucket = age_bucket(age)
    gender = data.get("gender", "m")
    return {
        "ref_id":      resolve_ref_id(data, allow_reserve=allow_reserve),
        "name_ua":     data.get("name_ua", "").strip(),
        "name_de":     data.get("name_de", "").strip(),
        "age":         age,
        "age_word_ua": (data.get("age_word_ua") or ukr_age_word(age)).strip() if data.get("age_word_ua") else ukr_age_word(age),
        "age_word_de": (data.get("age_word_de") or "Jahre alt").strip() if data.get("age_word_de") else "Jahre alt",
        "city_ua":     data.get("city_ua", "").strip(),
        "city_de":     data.get("city_de", "").strip(),
        "region_ua":   data.get("region_ua", "").strip(),
        "region_de":   data.get("region_de", "").strip(),
        "story_ua":    data.get("story_ua", "").strip(),
        "story_de":    data.get("story_de", "").strip(),
        "items": [
            {
                "ua":    i.get("ua", "").strip(),
                "de":    i.get("de", "").strip(),
                "count": str(i.get("count", "")).strip(),
                "price": str(i.get("price", "")).strip(),
            }
            for i in (data.get("items") or [])
            if (i.get("ua") or i.get("de"))
        ],
        "amount":      data.get("amount", "").strip() if isinstance(data.get("amount"), str) else data.get("amount", ""),
        "fund":        load_fund(),
        "age_bucket":  bucket,
        "illustration": pick_illustration(bucket, gender),
        "partners":    get_partner_logos(),
    }


SOCIAL_FIT_SNIPPET = """<base href="/template/">
<style>
@media screen {
  html { height: 100%; overflow: hidden; }
  body { margin: 0; height: 100%; overflow: hidden;
         display: flex; justify-content: center; align-items: flex-start;
         background: #EEE; }
  .s-page { transform-origin: top center; flex-shrink: 0; }
}
</style>
<script>
(function() {
  function fit() {
    var page = document.querySelector('.s-page');
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
        html = html.replace("<head>", "<head>" + PREVIEW_FIT_SNIPPET, 1)
    return html


def render_social_html(template_name: str, ctx: dict) -> str:
    return poster_env.get_template(template_name).render(**ctx)


def _screenshot_page(browser, html: str, tmp_path: Path, width: int, height: int) -> bytes:
    tmp_path.write_text(html, encoding="utf-8")
    try:
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(tmp_path.resolve().as_uri(), wait_until="networkidle")
        png = page.screenshot(full_page=False)
        page.close()
        return png
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------- routes ----------

@app.route("/")
def index():
    return render_template(
        "editor.html",
        presets=load_presets(),
        locations=load_locations(),
    )


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
    ctx = build_context(data, allow_reserve=True)
    html = render_poster_html(ctx, inject_base=False)

    render_tmp = TEMPLATE_DIR / "_render.html"
    render_tmp.write_text(html, encoding="utf-8")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = _file_basename(ctx["name_de"], ctx["name_ua"], ctx["ref_id"])
    out_path = OUTPUT_DIR / f"{base}.pdf"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**_playwright_launch_kwargs())
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

    resp = send_file(out_path, as_attachment=True, download_name=f"{base}.pdf")
    resp.headers["X-Ref-Id"] = ctx["ref_id"]
    resp.headers["Access-Control-Expose-Headers"] = "X-Ref-Id, Content-Disposition"
    return resp


@app.route("/api/preview/social/<fmt>", methods=["POST"])
def api_preview_social(fmt):
    if fmt not in SOCIAL_FORMATS:
        abort(404)
    template_name, _, _ = SOCIAL_FORMATS[fmt]
    data = request.get_json() or {}
    ctx = build_context(data)
    html = render_social_html(template_name, ctx)
    html = html.replace("<head>", "<head>" + SOCIAL_FIT_SNIPPET, 1)
    return Response(html, mimetype="text/html")


@app.route("/api/generate/social/<fmt>", methods=["POST"])
def api_generate_social(fmt):
    if fmt not in SOCIAL_FORMATS:
        abort(404)
    template_name, width, height = SOCIAL_FORMATS[fmt]
    data = request.get_json() or {}
    ctx = build_context(data)
    html = render_social_html(template_name, ctx)
    tmp = TEMPLATE_DIR / f"_render_{fmt}.html"

    with sync_playwright() as p:
        browser = p.chromium.launch(**_playwright_launch_kwargs())
        png_bytes = _screenshot_page(browser, html, tmp, width, height)
        browser.close()

    base = _file_basename(ctx["name_de"], ctx["name_ua"], ctx["ref_id"])
    fname = f"{base}_{fmt}.png"
    return send_file(io.BytesIO(png_bytes), mimetype="image/png",
                     as_attachment=True, download_name=fname)


@app.route("/api/generate/all", methods=["POST"])
def api_generate_all():
    data = request.get_json() or {}
    ctx = build_context(data, allow_reserve=True)
    ref = ctx["ref_id"]
    base = _file_basename(ctx["name_de"], ctx["name_ua"], ref)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_DIR / f"{base}.pdf"

    zip_buf = io.BytesIO()

    with sync_playwright() as p:
        browser = p.chromium.launch(**_playwright_launch_kwargs())

        # A4 PDF
        pdf_html = render_poster_html(ctx, inject_base=False)
        pdf_tmp = TEMPLATE_DIR / "_render_pdf.html"
        pdf_tmp.write_text(pdf_html, encoding="utf-8")
        try:
            page = browser.new_page()
            page.goto(pdf_tmp.resolve().as_uri(), wait_until="networkidle")
            page.pdf(path=str(pdf_path), format="A4", print_background=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            page.close()
        finally:
            pdf_tmp.unlink(missing_ok=True)

        # Social PNGs
        pngs = {}
        for fmt, (tmpl_name, w, h) in SOCIAL_FORMATS.items():
            html = render_social_html(tmpl_name, ctx)
            tmp = TEMPLATE_DIR / f"_render_{fmt}.html"
            pngs[fmt] = _screenshot_page(browser, html, tmp, w, h)

        browser.close()

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(pdf_path), f"{base}_A4.pdf")
        for fmt, png_bytes in pngs.items():
            zf.writestr(f"{base}_{fmt}.png", png_bytes)

    zip_buf.seek(0)
    resp = send_file(zip_buf, mimetype="application/zip",
                     as_attachment=True, download_name=f"{base}_all.zip")
    resp.headers["X-Ref-Id"] = ref
    resp.headers["Access-Control-Expose-Headers"] = "X-Ref-Id, Content-Disposition"
    return resp


# ---------- brand settings ----------

@app.route("/api/brand", methods=["GET"])
def api_brand_get():
    return jsonify(load_fund())


@app.route("/api/brand", methods=["PUT"])
def api_brand_put():
    ALLOWED = {"website", "phone", "email", "cta_ua", "cta_de", "partners_ua", "partners_de"}
    incoming = request.get_json() or {}
    fund = load_fund()
    for k in ALLOWED:
        if k in incoming:
            fund[k] = str(incoming[k]).strip()
    FUND_CONFIG.write_text(json.dumps(fund, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify(fund)


@app.route("/api/upload/partner/<int:slot>", methods=["POST"])
def api_upload_partner(slot):
    if slot < 1 or slot > 3:
        abort(400)
    if "file" not in request.files:
        abort(400)
    f = request.files["file"]
    if not f.filename:
        abort(400)
    ext = Path(f.filename).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
        abort(400, "Допустимі формати: PNG, JPG, SVG, WEBP")
    # Remove old file for this slot (any extension)
    for old_ext in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
        old = ASSETS_DIR / f"partner_{slot}{old_ext}"
        if old.exists():
            old.unlink()
    dest = ASSETS_DIR / f"partner_{slot}{ext}"
    f.save(str(dest))
    return jsonify({"ok": True, "path": f"assets/partner_{slot}{ext}", "slot": slot})


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
