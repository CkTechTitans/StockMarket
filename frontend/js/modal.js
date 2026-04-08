// modal.js — stock detail modal, chart, AI analysis

let activeStock   = null;
let chartInstance = null;
let chartCache    = {};
let aiCache       = {};
let currentPeriod = 7;

function openModal(i) {
  const s = stockData[i]; if (!s || s.error) return;
  activeStock = s; currentPeriod = 7; aiCache[s.symbol] = null;
  const up = s.change_pct >= 0, sign = up ? "+" : "";

  const badge = document.getElementById("mBadge");
  badge.textContent = s.symbol;
  badge.className = "modal-sym-badge" + (up ? "" : " down-badge");
  document.getElementById("mCompany").textContent = s.name;
  document.getElementById("mPrice").textContent = "₹ " + fmt(s.price);

  const cb = document.getElementById("mChangeBadge");
  cb.textContent = `${up?"▲":"▼"} ${sign}${s.change} (${sign}${s.change_pct}%)`;
  cb.className = "modal-change-badge " + (up ? "up" : "down");

  document.getElementById("dOpen").textContent = "₹ " + fmt(s.open);
  document.getElementById("dHigh").textContent = "₹ " + fmt(s.high);
  document.getElementById("dLow").textContent  = "₹ " + fmt(s.low);
  document.getElementById("dPrev").textContent = "₹ " + fmt(s.prev_close);
  document.getElementById("dVol").textContent  = fmtV(s.volume);
  document.getElementById("dDate").textContent = s.date;

  document.getElementById("aiContent").innerHTML = `<div class="ai-loading"><div class="ai-spinner"></div>Analysing with Gemini AI…</div>`;
  switchTab("chart", document.querySelector(".tab-btn"));
  document.getElementById("modalOverlay").classList.add("open");
  loadChart(s.symbol, currentPeriod);
}

function closeModal(e) { if (e.target === document.getElementById("modalOverlay")) closeModalDirect(); }
function closeModalDirect() {
  document.getElementById("modalOverlay").classList.remove("open");
  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
}

function switchTab(name, btn) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById("tab-" + name).classList.add("active");
  if (name === "ai" && activeStock && !aiCache[activeStock.symbol]) loadAI();
}

// ── Chart ──────────────────────────────────────────────────────────────────
async function loadChart(symbol, period) {
  const loading = document.getElementById("chartLoading");
  loading.style.display = "flex";
  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
  try {
    const key = `${symbol}-${period}`;
    let data = chartCache[key];
    if (!data) {
      const res = await fetch(`${API}/api/stock/${symbol}/chart?period=${period}`);
      if (!res.ok) throw new Error("Chart fetch failed");
      const json = await res.json();
      if (json.error) throw new Error(json.error);
      data = json.chart;
      chartCache[key] = data;
    }
    loading.style.display = "none";
    renderChart(data, symbol);
  } catch(e) { loading.textContent = "Chart unavailable: " + e.message; }
}

function renderChart(data, symbol) {
  const up    = activeStock && activeStock.change_pct >= 0;
  const color = up ? "#00d09c" : "#eb5757";
  const labels = data.map(d => d.date.slice(5));
  const closes = data.map(d => d.close);
  const ctx = document.getElementById("priceChart").getContext("2d");
  chartInstance = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{
      label: symbol, data: closes,
      borderColor: color, borderWidth: 2,
      pointRadius: 0, pointHoverRadius: 5, pointHoverBackgroundColor: color,
      tension: 0.3, fill: true,
      backgroundColor: (ctx2) => {
        const g = ctx2.chart.ctx.createLinearGradient(0, 0, 0, ctx2.chart.height);
        g.addColorStop(0, up ? "rgba(0,208,156,0.18)" : "rgba(235,87,87,0.18)");
        g.addColorStop(1, "rgba(0,0,0,0)");
        return g;
      }
    }]},
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1e2333", borderColor: "#252a38", borderWidth: 1,
          titleColor: "#6b7280", bodyColor: "#e8eaf0",
          bodyFont: { family: "'JetBrains Mono',monospace", size: 13 },
          callbacks: { label: c => " ₹ " + c.parsed.y.toLocaleString("en-IN", {minimumFractionDigits:2}) }
        }
      },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#6b7280", font: { size: 10, family: "'JetBrains Mono'" }, maxTicksLimit: 8 } },
        y: { position: "right", grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#6b7280", font: { size: 10, family: "'JetBrains Mono'" }, callback: v => "₹" + v.toLocaleString("en-IN") } }
      }
    }
  });
}

function changePeriod(period, btn) {
  document.querySelectorAll(".period-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  currentPeriod = period;
  if (activeStock) loadChart(activeStock.symbol, period);
}

// ── AI Analysis ────────────────────────────────────────────────────────────
async function loadAI() {
  if (!activeStock) return;
  const sym = activeStock.symbol;
  const el  = document.getElementById("aiContent");
  el.innerHTML = `<div class="ai-loading"><div class="ai-spinner"></div>Analysing with Gemini AI…</div>`;
  try {
    let chart = [];
    const key = `${sym}-30`;
    if (chartCache[key]) {
      chart = chartCache[key];
    } else {
      try {
        const cr = await fetch(`${API}/api/stock/${sym}/chart?period=30`);
        const cj = await cr.json();
        chart = cj.chart || [];
        chartCache[key] = chart;
      } catch(_) {}
    }
    const res = await fetch(`${API}/api/stock/${sym}/analyze`, {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({stock: activeStock, chart})
    });
    const ai = await res.json();
    aiCache[sym] = ai;
    renderAI(ai);
  } catch(e) {
    el.innerHTML = `<div style="padding:24px;color:var(--red);font-size:.85rem">AI analysis failed: ${e.message}</div>`;
  }
}

function renderAI(ai) {
  const rec     = ai.recommendation || "N/A";
  const reasons = (ai.reasons || []).map(r => `<div class="ai-list-item"><div class="dot"></div><div>${r}</div></div>`).join("");
  const risks   = (ai.risks   || []).map(r => `<div class="ai-list-item"><div class="dot risk"></div><div>${r}</div></div>`).join("");
  document.getElementById("aiContent").innerHTML = `
    <div class="ai-rec-banner ${rec}">
      <div class="ai-rec-left">
        <div><div class="ai-rec-label">Recommendation</div><div class="ai-rec-value ${rec}">${rec}</div></div>
        <div><div class="ai-rec-label">Confidence</div><div style="font-size:.95rem;font-weight:600">${ai.confidence||"N/A"}</div></div>
        <div><div class="ai-rec-label">Sentiment</div><div style="font-size:.95rem;font-weight:600">${ai.sentiment||"N/A"}</div></div>
      </div>
      <div class="ai-score-ring ${rec}">${ai.score||0}/10</div>
    </div>
    <div class="ai-summary">${ai.summary||""}</div>
    <div class="ai-section-title">✅ Reasons</div>
    <div class="ai-list">${reasons || "<div style='color:var(--muted);font-size:.85rem'>No reasons available</div>"}</div>
    <div class="ai-section-title">⚠️ Risks</div>
    <div class="ai-list">${risks || "<div style='color:var(--muted);font-size:.85rem'>No risks identified</div>"}</div>
    <div class="ai-two-col">
      <div class="ai-info-box"><div class="ai-info-label">Price Target</div><div class="ai-info-value">${ai.price_target||"N/A"}</div></div>
      <div class="ai-info-box"><div class="ai-info-label">Time Horizon</div><div class="ai-info-value">3 Months</div></div>
    </div>
    <div class="ai-section-title">🔭 Outlook</div>
    <div class="ai-outlook">${ai.outlook||"N/A"}</div>`;
}