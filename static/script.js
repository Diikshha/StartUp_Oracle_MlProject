/* ═══════════════════════════════════════════════
   StartupOracle · script.js
   ═══════════════════════════════════════════════ */

/* ── Plotly config ────────────────────────────── */
const PLOTLY_CONFIG = {
  displayModeBar: false,
  responsive: true,
};

const DARK_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  'rgba(0,0,0,0)',
  font: { family: "'Syne', sans-serif", color: '#e2e8f0', size: 12 },
  margin: { l: 40, r: 20, t: 20, b: 40 },
};

/* ── Gauge Chart ──────────────────────────────── */
function renderGauge(prob, prediction) {
  const el = document.getElementById('gaugeChart');
  if (!el || !window.Plotly) return;

  const color = prediction === 'Success' ? '#10b981' : '#ef4444';

  const data = [{
    type: 'indicator',
    mode: 'gauge+number',
    value: Math.round(prob * 100),
    number: { suffix: '%', font: { size: 28, color: '#e2e8f0', family: "'Orbitron', monospace" } },
    gauge: {
      axis: { range: [0, 100], tickwidth: 1, tickcolor: '#334155', tickfont: { size: 10, color: '#64748b' } },
      bar: { color, thickness: 0.3 },
      bgcolor: 'rgba(0,0,0,0)',
      borderwidth: 0,
      steps: [
        { range: [0, 30],  color: 'rgba(239,68,68,0.1)' },
        { range: [30, 60], color: 'rgba(245,158,11,0.1)' },
        { range: [60, 100],color: 'rgba(16,185,129,0.1)' },
      ],
      threshold: {
        line: { color: color, width: 3 },
        thickness: 0.8,
        value: Math.round(prob * 100),
      },
    },
  }];

  const layout = {
    ...DARK_LAYOUT,
    height: 180,
    margin: { l: 30, r: 30, t: 20, b: 10 },
  };

  Plotly.newPlot(el, data, layout, PLOTLY_CONFIG);
}

/* ── Bar Chart ────────────────────────────────── */
function renderBarChart(funding, rounds, age) {
  const el = document.getElementById('barChart');
  if (!el || !window.Plotly) return;

  // Normalise for display
  const normFunding = Math.min(funding / 10_000_000, 1);
  const normRounds  = Math.min(rounds / 10, 1);
  const normAge     = Math.min(age / 10, 1);

  const data = [{
    type: 'bar',
    x: ['Funding', 'Rounds', 'Age'],
    y: [normFunding, normRounds, normAge],
    text: [
      `$${(funding/1e6).toFixed(1)}M`,
      `${rounds} rounds`,
      `${age} yrs`,
    ],
    textposition: 'outside',
    textfont: { color: '#e2e8f0', size: 11 },
    marker: {
      color: ['rgba(124,58,237,0.7)', 'rgba(6,182,212,0.7)', 'rgba(16,185,129,0.7)'],
      line: {
        color: ['#7c3aed', '#06b6d4', '#10b981'],
        width: 2,
      },
    },
  }];

  const layout = {
    ...DARK_LAYOUT,
    height: 200,
    yaxis: { range: [0, 1.3], showgrid: true, gridcolor: 'rgba(255,255,255,0.05)', zeroline: false, tickformat: '.0%' },
    xaxis: { showgrid: false },
    bargap: 0.35,
  };

  Plotly.newPlot(el, data, layout, PLOTLY_CONFIG);
}

/* ── History Trend ────────────────────────────── */
function renderHistory(history) {
  const el = document.getElementById('historyChart');
  if (!el || !history || history.length < 2 || !window.Plotly) return;

  const sorted = [...history].reverse();
  const labels = sorted.map((r, i) => `#${i + 1}`);
  const probs  = sorted.map(r => Math.round(r.probability * 100));
  const colors = sorted.map(r => r.prediction === 'Success' ? '#10b981' : '#ef4444');

  const data = [
    {
      type: 'scatter',
      mode: 'lines',
      x: labels,
      y: probs,
      line: { color: 'rgba(167,139,250,0.3)', width: 2 },
      showlegend: false,
      hoverinfo: 'skip',
    },
    {
      type: 'scatter',
      mode: 'markers+lines',
      x: labels,
      y: probs,
      marker: { color: colors, size: 9, line: { color: '#fff', width: 1 } },
      line: { color: 'transparent' },
      text: sorted.map(r => `${r.prediction}: ${Math.round(r.probability * 100)}%`),
      hovertemplate: '%{text}<extra></extra>',
      showlegend: false,
    },
  ];

  // Fill area
  data.unshift({
    type: 'scatter',
    mode: 'none',
    x: labels,
    y: probs,
    fill: 'tozeroy',
    fillcolor: 'rgba(124,58,237,0.08)',
    showlegend: false,
    hoverinfo: 'skip',
  });

  const layout = {
    ...DARK_LAYOUT,
    height: 200,
    yaxis: { range: [0, 105], showgrid: true, gridcolor: 'rgba(255,255,255,0.05)', zeroline: false, ticksuffix: '%' },
    xaxis: { showgrid: false },
    hovermode: 'closest',
  };

  Plotly.newPlot(el, data, layout, PLOTLY_CONFIG);
}

/* ── Leaderboard ──────────────────────────────── */
async function loadLeaderboard() {
  const el = document.getElementById('leaderboardContent');
  if (!el) return;
  try {
    const res  = await fetch('/leaderboard');
    const data = await res.json();

    if (!data.length) {
      el.innerHTML = '<div class="loading-pulse">No successful predictions yet. Be the first!</div>';
      return;
    }

    const medals = ['🥇', '🥈', '🥉'];
    el.innerHTML = data.map((item, i) => `
      <div class="leaderboard-item" style="animation-delay: ${i * 0.06}s">
        <span class="lb-rank ${i < 3 ? `lb-rank-${i+1}` : ''}">
          ${medals[i] || `#${i+1}`}
        </span>
        <span class="lb-user">${item.user || 'anon'}</span>
        <span style="font-size:0.75rem; color:#64748b;">
          $${Number(item.funding_total_usd || 0).toLocaleString()}
        </span>
        <span class="lb-score">${Math.round(item.probability * 100)}%</span>
      </div>
    `).join('');
  } catch {
    el.innerHTML = '<div class="loading-pulse">Unable to load leaderboard.</div>';
  }
}

/* ── Slider ↔ Input sync ──────────────────────── */
function syncSliders() {
  const fundingInput  = document.querySelector('[name=funding_total_usd]');
  const fundingSlider = document.getElementById('fundingSlider');
  const ageInput      = document.querySelector('[name=startup_age]');
  const ageSlider     = document.getElementById('ageSlider');

  if (fundingInput && fundingSlider) {
    fundingSlider.addEventListener('input', () => {
      fundingInput.value = fundingSlider.value;
    });
    fundingInput.addEventListener('input', () => {
      fundingSlider.value = fundingInput.value;
    });
  }

  if (ageInput && ageSlider) {
    ageSlider.addEventListener('input', () => {
      ageInput.value = ageSlider.value;
    });
    ageInput.addEventListener('input', () => {
      ageSlider.value = ageInput.value;
    });
  }
}

/* ── Round Pills ──────────────────────────────── */
function setupRoundPills() {
  const pills  = document.querySelectorAll('.round-pill');
  const input  = document.querySelector('[name=funding_rounds]');
  if (!pills.length || !input) return;

  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      input.value = pill.dataset.val;
    });
  });

  input.addEventListener('input', () => {
    pills.forEach(p => {
      p.classList.toggle('active', p.dataset.val === input.value);
    });
  });
}

/* ── CSV Upload Zone ──────────────────────────── */
function setupUploadZone() {
  const zone   = document.getElementById('uploadZone');
  const fileIn = document.getElementById('csvFile');
  const label  = document.getElementById('uploadText');
  if (!zone || !fileIn) return;

  zone.addEventListener('click', () => fileIn.click());

  fileIn.addEventListener('change', () => {
    const f = fileIn.files[0];
    if (f && label) label.textContent = `📄 ${f.name}`;
  });

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f) {
      const dt = new DataTransfer();
      dt.items.add(f);
      fileIn.files = dt.files;
      if (label) label.textContent = `📄 ${f.name}`;
    }
  });
}

/* ── Form Loading State ───────────────────────── */
function setupFormLoading() {
  const form = document.getElementById('predictForm');
  const btn  = document.getElementById('predictBtn');
  if (!form || !btn) return;

  form.addEventListener('submit', () => {
    const content = btn.querySelector('.btn-content');
    const loader  = btn.querySelector('.btn-loader');
    if (content) content.style.display = 'none';
    if (loader)  loader.style.display  = 'inline';
    btn.disabled = true;
  });
}

/* ── Init ─────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  syncSliders();
  setupRoundPills();
  setupUploadZone();
  setupFormLoading();
  loadLeaderboard();

  // Render charts if prediction data exists
  if (typeof PREDICTION_DATA !== 'undefined' && PREDICTION_DATA.hasPrediction) {
    const { prediction, probability, inputVals, history } = PREDICTION_DATA;

    // Small delay so Plotly renders after layout paint
    requestAnimationFrame(() => {
      renderGauge(probability, prediction);
      renderBarChart(inputVals.funding, inputVals.rounds, inputVals.age);
      renderHistory(history);
    });
  } else if (typeof PREDICTION_DATA !== 'undefined' && PREDICTION_DATA.history.length > 1) {
    requestAnimationFrame(() => {
      renderHistory(PREDICTION_DATA.history);
    });
  }

  // Animate insight cards on load
  document.querySelectorAll('.insight-card').forEach((card, i) => {
    card.style.animationDelay = `${i * 0.1}s`;
  });

  // Animate table rows
  document.querySelectorAll('.table-row-anim').forEach((row, i) => {
    row.style.animationDelay = `${i * 0.04}s`;
  });
});