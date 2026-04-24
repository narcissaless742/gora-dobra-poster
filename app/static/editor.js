/* ================================
   Gora Dobra — Editor (wizard UI)
   ================================ */

const $ = (s, p = document) => p.querySelector(s);
const $$ = (s, p = document) => Array.from(p.querySelectorAll(s));

const AGE_BUCKETS = [
  { max: 6,  id: '2_6',   label: '2–6' },
  { max: 10, id: '7_10',  label: '7–10' },
  { max: 14, id: '11_14', label: '11–14' },
  { max: 99, id: '15_18', label: '15–18' },
];

/* ================================
   STATE — all DE fields held in memory, not in DOM (except story)
   ================================ */
const state = {
  name_ua: '',  name_de: '',
  city_ua: '',  city_de: '',
  story_ua: '', story_de: '',
  items: [],       // [{ua, de, price}]
  age: 8,
  gender: 'f',
  amount: 0,
  amountManual: false,
  brand: {},
};

/* ================================
   TRANSLATE HELPER
   ================================ */
async function translate(text) {
  const s = (text || '').trim();
  if (!s) return '';
  try {
    const res = await fetch('/api/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: s }),
    });
    const data = await res.json();
    if (data.error) { console.warn('Translate error:', data.error); return ''; }
    return data.translated || '';
  } catch (e) {
    console.error(e);
    return '';
  }
}

/* Debounce helper */
function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(null, args), ms);
  };
}

/* Toast */
const toastEl = $('#toast');
function toast(msg, ms = 2200) {
  toastEl.textContent = msg;
  toastEl.classList.add('visible');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => toastEl.classList.remove('visible'), ms);
}

/* ================================
   STEP 1 — name, age, gender, city
   ================================ */
const nameInput = $('#name_ua');
const cityInput = $('#city_ua');
const hintName = $('#hint-name');
const hintCity = $('#hint-city');
const ageInput = $('#age');
const genderImgM = $('#gender-img-m');
const genderImgF = $('#gender-img-f');

function currentBucket(age) {
  return AGE_BUCKETS.find(b => age <= b.max) || AGE_BUCKETS[AGE_BUCKETS.length - 1];
}

function updateGenderPreviews() {
  const bucket = currentBucket(state.age);
  genderImgM.src = `/template/assets/child_${bucket.id}_m.png`;
  genderImgF.src = `/template/assets/child_${bucket.id}_f.png`;
}

function setHint(el, translated) {
  if (!translated) { el.innerHTML = ''; return; }
  el.innerHTML = `<span>🌐 Німецькою: <b>${translated}</b></span>`;
}

nameInput.addEventListener('input', (e) => { state.name_ua = e.target.value; });
nameInput.addEventListener('blur', async () => {
  if (!state.name_ua.trim()) { setHint(hintName, ''); state.name_de = ''; return; }
  setHint(hintName, '…');
  const t = await translate(state.name_ua);
  state.name_de = t;
  setHint(hintName, t);
});

cityInput.addEventListener('input', (e) => { state.city_ua = e.target.value; });
cityInput.addEventListener('blur', async () => {
  if (!state.city_ua.trim()) { setHint(hintCity, ''); state.city_de = ''; return; }
  setHint(hintCity, '…');
  const t = await translate(state.city_ua);
  state.city_de = t;
  setHint(hintCity, t);
});

ageInput.addEventListener('input', (e) => {
  let v = parseInt(e.target.value, 10);
  if (isNaN(v)) v = 1;
  v = Math.max(1, Math.min(18, v));
  state.age = v;
  updateGenderPreviews();
});

$$('.age-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const delta = parseInt(btn.dataset.delta, 10);
    let v = state.age + delta;
    v = Math.max(1, Math.min(18, v));
    state.age = v;
    ageInput.value = v;
    updateGenderPreviews();
  });
});

$$('input[name="gender"]').forEach(r => {
  r.addEventListener('change', (e) => {
    state.gender = e.target.value;
    // Visual: toggle "checked" class on card
    $$('.gender-card').forEach(c => c.classList.remove('checked'));
    e.target.closest('.gender-card').classList.add('checked');
  });
});
// Initial check-state for default
$('.gender-card[data-gender="f"]').classList.add('checked');

/* ================================
   STEP 2 — story (with visible DE edit)
   ================================ */
const storyUa = $('#story_ua');
const storyDe = $('#story_de');
const storyStatus = $('#story-status');
const btnRetranslateStory = $('#btn-retranslate-story');

async function autotranslateStory() {
  if (!state.story_ua.trim()) { storyDe.value = ''; state.story_de = ''; storyStatus.textContent = ''; return; }
  storyStatus.textContent = 'Перекладаємо…';
  const t = await translate(state.story_ua);
  storyStatus.textContent = t ? '✓ готово' : '';
  if (t) {
    storyDe.value = t;
    state.story_de = t;
  }
}

const autotranslateStoryDebounced = debounce(autotranslateStory, 800);

const storyUaCounter = $('#story-ua-counter');
const storyDeCounter = $('#story-de-counter');
const STORY_LIMIT = 350;

function updateCounter(counter, len) {
  counter.textContent = len + ' / ' + STORY_LIMIT;
  counter.classList.toggle('warn', len >= Math.floor(STORY_LIMIT * 0.9));
}

storyUa.addEventListener('input', (e) => {
  state.story_ua = e.target.value;
  updateCounter(storyUaCounter, e.target.value.length);
  autotranslateStoryDebounced();
});
storyDe.addEventListener('input', (e) => {
  state.story_de = e.target.value;
  updateCounter(storyDeCounter, e.target.value.length);
  storyStatus.textContent = '✎ ви редагуєте';
});
btnRetranslateStory.addEventListener('click', () => {
  autotranslateStory();
});

/* ================================
   STEP 3 — items, amount, contact
   ================================ */
const itemsList = $('#items-list');
const itemRowTemplate = $('#item-row-template');
const btnAddItem = $('#btn-add-item');
const amountInput = $('#amount');

function renderItems() {
  itemsList.innerHTML = '';
  state.items.forEach((it, idx) => {
    const node = itemRowTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector('.item-num').textContent = String(idx + 1);

    const ua = node.querySelector('.item-ua');
    ua.value = it.ua;
    ua.addEventListener('input', (e) => { state.items[idx].ua = e.target.value; });
    ua.addEventListener('blur', async () => {
      const src = (state.items[idx].ua || '').trim();
      if (!src) { state.items[idx].de = ''; return; }
      const t = await translate(src);
      if (t) state.items[idx].de = t;
    });

    const pr = node.querySelector('.item-price');
    pr.value = it.price !== undefined && it.price !== '' ? it.price : '';
    pr.addEventListener('input', (e) => {
      state.items[idx].price = e.target.value;
      recomputeTotal();
    });

    node.querySelector('.item-remove').addEventListener('click', () => {
      state.items.splice(idx, 1);
      renderItems();
      recomputeTotal();
    });
    itemsList.appendChild(node);
  });
  btnAddItem.disabled = state.items.length >= 3;
}

btnAddItem.addEventListener('click', () => {
  if (state.items.length >= 3) return;
  state.items.push({ ua: '', de: '', price: '' });
  renderItems();
  const rows = itemsList.querySelectorAll('.item-ua');
  if (rows.length) rows[rows.length - 1].focus();
});

/* ===== amount: auto-sum with manual override ===== */
const btnResetAmount = $('#btn-reset-amount');
const amountModeLabel = $('#amount-mode');

function recomputeTotal() {
  if (state.amountManual) return;
  const sum = state.items.reduce((s, it) => s + (parseFloat(it.price) || 0), 0);
  state.amount = sum;
  amountInput.value = sum;
}

function setAmountMode(manual) {
  state.amountManual = manual;
  amountModeLabel.textContent = manual ? 'ви ввели вручну' : 'рахуємо автоматично з пунктів';
  amountModeLabel.classList.toggle('manual', manual);
  btnResetAmount.classList.toggle('hidden', !manual);
}

const AMOUNT_MAX = 150;

amountInput.addEventListener('input', (e) => {
  let v = parseFloat(e.target.value) || 0;
  if (v > AMOUNT_MAX) { v = AMOUNT_MAX; e.target.value = AMOUNT_MAX; }
  state.amount = v;
  setAmountMode(true);
});

btnResetAmount.addEventListener('click', () => {
  setAmountMode(false);
  recomputeTotal();
});

/* ================================
   STEP NAVIGATION
   ================================ */
const steps = $$('.page');
const dots = $$('.step-dot');

function goTo(step) {
  step = Math.max(1, Math.min(4, step));
  steps.forEach(p => p.classList.toggle('active', parseInt(p.dataset.step, 10) === step));
  dots.forEach(d => {
    const s = parseInt(d.dataset.step, 10);
    d.classList.toggle('active', s === step);
    d.classList.toggle('done', s < step);
  });
  // When reaching step 4, render preview + social thumbnails
  if (step === 4) { runPreview(); loadSocialPreviews(); }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

$$('.btn-next').forEach(b => b.addEventListener('click', () => goTo(parseInt(b.dataset.target, 10))));
$$('.btn-back').forEach(b => b.addEventListener('click', () => goTo(parseInt(b.dataset.target, 10))));

/* Step-dot direct navigation (only for steps already reached/active) */
dots.forEach(d => {
  d.addEventListener('click', () => {
    if (d.classList.contains('active') || d.classList.contains('done')) {
      goTo(parseInt(d.dataset.step, 10));
    }
  });
  d.style.cursor = 'pointer';
});

/* ================================
   PREVIEW
   ================================ */
const previewFrame = $('#preview-frame');
const btnPdf = $('#btn-pdf');
const btnNew = $('#btn-new');

function collectPayload() {
  return {
    name_ua: state.name_ua,
    name_de: state.name_de,
    city_ua: state.city_ua,
    city_de: state.city_de,
    story_ua: state.story_ua,
    story_de: state.story_de,
    items: state.items
      .filter(i => (i.ua || '').trim())
      .map(i => ({ ua: i.ua, de: i.de, price: i.price })),
    age: state.age,
    gender: state.gender,
    amount: state.amount,
  };
}

async function runPreview() {
  try {
    const res = await fetch('/api/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(collectPayload()),
    });
    const html = await res.text();
    const doc = previewFrame.contentDocument || previewFrame.contentWindow.document;
    doc.open(); doc.write(html); doc.close();
  } catch (e) {
    console.error(e);
    toast('Не вдалось оновити preview');
  }
}

/* ================================
   PDF
   ================================ */
btnPdf.addEventListener('click', async () => {
  const originalText = btnPdf.textContent;
  btnPdf.disabled = true;
  btnPdf.textContent = 'Готуємо PDF…';
  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(collectPayload()),
    });
    if (!res.ok) throw new Error('Generate failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const cd = res.headers.get('Content-Disposition') || '';
    const m = /filename="?([^"]+)"?/.exec(cd);
    a.download = m ? m[1] : 'poster.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast('✓ PDF завантажено');
  } catch (e) {
    toast('Помилка: ' + e.message);
  } finally {
    btnPdf.disabled = false;
    btnPdf.textContent = originalText;
  }
});

btnNew.addEventListener('click', () => {
  if (!confirm('Створити постер для іншої дитини? Поточні дані зникнуть.')) return;
  state.name_ua = ''; state.name_de = '';
  state.city_ua = ''; state.city_de = '';
  state.story_ua = ''; state.story_de = '';
  state.items = [];
  state.age = 8; state.gender = 'f';
  state.amount = 0; state.amountManual = false;
  nameInput.value = ''; cityInput.value = '';
  storyUa.value = ''; storyDe.value = '';
  ageInput.value = '8';
  $$('input[name="gender"]').forEach(r => { r.checked = (r.value === 'f'); });
  hintName.innerHTML = ''; hintCity.innerHTML = ''; storyStatus.textContent = '';
  seedDefaultItems();
  renderItems();
  updateGenderPreviews();
  setAmountMode(false);
  recomputeTotal();
  goTo(1);
});

/* ================================
   BRAND SETTINGS
   ================================ */
const bsCTAua   = $('#bs-cta-ua');
const bsCTAde   = $('#bs-cta-de');
const bsWebsite = $('#bs-website');
const bsPhone   = $('#bs-phone');
const bsEmail   = $('#bs-email');
const btnSaveBrand = $('#btn-save-brand');

async function loadBrandSettings() {
  try {
    const res = await fetch('/api/brand');
    if (!res.ok) return;
    const data = await res.json();
    state.brand = data;
    if (data.cta_ua)  bsCTAua.value   = data.cta_ua;
    if (data.cta_de)  bsCTAde.value   = data.cta_de;
    if (data.website) bsWebsite.value = data.website;
    if (data.phone)   bsPhone.value   = data.phone;
    if (data.email)   bsEmail.value   = data.email;
  } catch (e) {
    console.warn('Could not load brand settings:', e);
  }
}

btnSaveBrand.addEventListener('click', async () => {
  const payload = {
    cta_ua:  bsCTAua.value.trim(),
    cta_de:  bsCTAde.value.trim(),
    website: bsWebsite.value.trim(),
    phone:   bsPhone.value.trim(),
    email:   bsEmail.value.trim(),
  };
  const orig = btnSaveBrand.textContent;
  btnSaveBrand.disabled = true;
  btnSaveBrand.textContent = 'Зберігаємо…';
  try {
    const res = await fetch('/api/brand', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Save failed');
    state.brand = await res.json();
    toast('✓ Налаштування збережено');
  } catch (e) {
    toast('Помилка: ' + e.message);
  } finally {
    btnSaveBrand.disabled = false;
    btnSaveBrand.textContent = orig;
  }
});

$$('.partner-upload').forEach(input => {
  input.addEventListener('change', async (e) => {
    const slot = e.target.dataset.slot;
    const file = e.target.files[0];
    if (!file) return;
    const statusEl = $(`#partner-status-${slot}`);
    statusEl.textContent = 'Завантажуємо…';
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch(`/api/upload/partner/${slot}`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error((await res.text()) || 'Upload failed');
      statusEl.textContent = '✓ ' + file.name;
      toast(`✓ Логотип ${slot} завантажено`);
    } catch (e) {
      statusEl.textContent = 'Помилка!';
      toast('Помилка завантаження: ' + e.message);
    }
  });
});

/* ================================
   SOCIAL PREVIEWS
   ================================ */
async function loadSocialPreviews() {
  const payload = collectPayload();
  for (const fmt of ['story', 'post1', 'post2']) {
    const frame = document.querySelector(`.social-preview-frame[data-fmt="${fmt}"]`);
    const wrap  = frame && frame.closest('.social-preview-wrap');
    if (!frame) continue;
    wrap && wrap.classList.add('loading');
    try {
      const res = await fetch(`/api/preview/social/${fmt}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const html = await res.text();
      const doc = frame.contentDocument || frame.contentWindow.document;
      doc.open(); doc.write(html); doc.close();
    } catch (e) {
      console.warn('Social preview failed:', fmt, e);
    } finally {
      wrap && wrap.classList.remove('loading');
    }
  }
}

/* ================================
   SOCIAL / ZIP DOWNLOADS
   ================================ */
async function downloadBlob(url, payload, defaultName, btnEl) {
  const orig = btnEl.textContent;
  btnEl.disabled = true;
  btnEl.textContent = 'Готуємо…';
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Помилка сервера');
    const blob = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objUrl;
    const cd = res.headers.get('Content-Disposition') || '';
    const m = /filename="?([^";\s]+)"?/.exec(cd);
    a.download = m ? m[1] : defaultName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objUrl);
    toast('✓ Завантажено: ' + a.download);
  } catch (e) {
    toast('Помилка: ' + e.message);
  } finally {
    btnEl.disabled = false;
    btnEl.textContent = orig;
  }
}

$('#btn-story').addEventListener('click', () =>
  downloadBlob('/api/generate/social/story', collectPayload(), 'poster_story.png', $('#btn-story')));
$('#btn-post1').addEventListener('click', () =>
  downloadBlob('/api/generate/social/post1', collectPayload(), 'poster_post1.png', $('#btn-post1')));
$('#btn-post2').addEventListener('click', () =>
  downloadBlob('/api/generate/social/post2', collectPayload(), 'poster_post2.png', $('#btn-post2')));
$('#btn-all').addEventListener('click', () =>
  downloadBlob('/api/generate/all', collectPayload(), 'poster_all.zip', $('#btn-all')));

/* ================================
   INITIAL
   ================================ */
function seedDefaultItems() {
  state.items = [
    { ua: 'FreeStyle Libre 3 — сенсори, 2 шт', de: 'FreeStyle Libre 3 Sensoren, 2 Stk.', price: 65 },
    { ua: 'Пластирі-фіксатори', de: 'Fixierpflaster', price: 20 },
  ];
}

seedDefaultItems();
renderItems();
updateGenderPreviews();
setAmountMode(false);
recomputeTotal();
loadBrandSettings();
