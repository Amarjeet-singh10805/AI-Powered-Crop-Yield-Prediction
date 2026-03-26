/* ═══════════════════════════════════════════════════
   CropSage AI · Frontend Logic
═══════════════════════════════════════════════════ */

const API = '';   // same-origin Flask

/* ── Selectors ── */
const cropSel       = document.getElementById('cropSelect');
const seasonSel     = document.getElementById('seasonSelect');
const stateSel      = document.getElementById('stateSelect');
const areaInp       = document.getElementById('areaInput');
const rainfallInp   = document.getElementById('rainfallInput');
const fertilizerInp = document.getElementById('fertilizerInput');
const pesticideInp  = document.getElementById('pesticideInput');
const predictBtn    = document.getElementById('predictBtn');
const btnText       = predictBtn.querySelector('.btn-text');
const btnIcon       = predictBtn.querySelector('.btn-icon');
const btnLoader     = predictBtn.querySelector('.btn-loader');
const errorMsg      = document.getElementById('errorMsg');
const resultCard    = document.getElementById('resultCard');
const yieldValue    = document.getElementById('yieldValue');
const yieldBar      = document.getElementById('yieldBar');
const yieldHint     = document.getElementById('yieldHint');
const resultMeta    = document.getElementById('resultMeta');
const trendChart    = document.getElementById('trendChart');
const compareChart  = document.getElementById('compareChart');
const chartsWrap    = document.getElementById('chartsWrap');
const dbBadge       = document.getElementById('dbBadge');
const dbDot         = dbBadge.querySelector('.db-dot');
const dbLabel       = document.getElementById('dbLabel');
const historyBody   = document.getElementById('historyBody');
const refreshBtn    = document.getElementById('refreshBtn');

/* ── Nav ── */
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const target = btn.dataset.panel;
    document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
    document.getElementById('panel-' + target).classList.remove('hidden');
    if (target === 'history') loadHistory();
  });
});

/* ── Load metadata ── */
async function loadMetadata() {
  try {
    const res  = await fetch(API + '/api/metadata');
    const data = await res.json();

    populateSelect(cropSel,   data.crops,   'Select crop…');
    populateSelect(seasonSel, data.seasons, 'Select season…');
    populateSelect(stateSel,  data.states,  'Select state…');

    dbDot.classList.add('online');
    dbLabel.textContent = 'Model ready';
  } catch (e) {
    dbDot.classList.add('offline');
    dbLabel.textContent = 'Server offline';
    console.error('Metadata fetch failed:', e);
  }
}

function populateSelect(sel, items, placeholder) {
  sel.innerHTML = `<option value="">${placeholder}</option>`;
  items.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item;
    opt.textContent = item;
    sel.appendChild(opt);
  });
}

/* ── Predict ── */
predictBtn.addEventListener('click', async () => {
  hideError();

  const crop       = cropSel.value;
  const season     = seasonSel.value;
  const state      = stateSel.value;
  const area       = areaInp.value;
  const rainfall   = rainfallInp.value;
  const fertilizer = fertilizerInp.value;
  const pesticide  = pesticideInp.value;

  if (!crop || !season || !state || !area || !rainfall || !fertilizer || !pesticide) {
    showError('Please fill in all fields before predicting.');
    return;
  }

  setLoading(true);

  try {
    const res  = await fetch(API + '/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ crop, season, state, area, rainfall, fertilizer, pesticide }),
    });
    const data = await res.json();

    if (!data.success) throw new Error(data.error || 'Prediction failed');

    showResult(data, crop, season, state);
  } catch (e) {
    showError(e.message || 'An unexpected error occurred.');
  } finally {
    setLoading(false);
  }
});

function showResult(data, crop, season, state) {
  const y = data.predicted_yield;
  yieldValue.textContent = y.toFixed(3);
  resultMeta.textContent = `${crop} · ${season} · ${state}`;

  // Bar: scale 0–15 t/ha as 100%
  const pct = Math.min(100, (y / 15) * 100);
  yieldBar.style.width = pct + '%';

  // Hint
  let hint = '';
  if (y < 0.5)      hint = '⚠️ Very low yield — consider soil/input improvements';
  else if (y < 1.5) hint = '📊 Below average yield for this crop';
  else if (y < 4)   hint = '✅ Average to good yield';
  else if (y < 10)  hint = '🌟 High yield — excellent conditions';
  else               hint = '🏆 Exceptional yield predicted';
  yieldHint.textContent = hint;

  resultCard.classList.remove('hidden');

  // Charts
  if (data.trend_chart) {
    trendChart.src = 'data:image/png;base64,' + data.trend_chart;
    compareChart.src = 'data:image/png;base64,' + data.compare_chart;
    chartsWrap.classList.remove('hidden');
  }

  // Scroll result into view on mobile
  if (window.innerWidth < 900) {
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

/* ── History ── */
async function loadHistory() {
  historyBody.innerHTML = '<tr><td colspan="8" class="empty-row">Loading…</td></tr>';
  try {
    const res  = await fetch(API + '/api/history');
    const data = await res.json();

    if (!data.success || !data.history.length) {
      historyBody.innerHTML = '<tr><td colspan="8" class="empty-row">No records yet. Make a prediction first.</td></tr>';
      return;
    }

    const source = data.source === 'mysql' ? '🗄️ MySQL' : '💾 In-memory';
    historyBody.innerHTML = data.history.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${r.created_at || '—'}</td>
        <td>${r.crop}</td>
        <td>${r.season}</td>
        <td>${r.state}</td>
        <td>${Number(r.area).toLocaleString()}</td>
        <td>${Number(r.rainfall).toFixed(1)}</td>
        <td>${Number(r.predicted_yield).toFixed(3)}</td>
      </tr>
    `).join('');

    dbLabel.textContent = source;
  } catch (e) {
    historyBody.innerHTML = '<tr><td colspan="8" class="empty-row">Failed to load history.</td></tr>';
  }
}

refreshBtn.addEventListener('click', loadHistory);

/* ── Helpers ── */
function setLoading(on) {
  predictBtn.classList.toggle('loading', on);
  btnText.classList.toggle('hidden', on);
  btnIcon.classList.toggle('hidden', on);
  btnLoader.classList.toggle('hidden', !on);
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove('hidden');
}
function hideError() { errorMsg.classList.add('hidden'); }

/* ── Init ── */
loadMetadata();
