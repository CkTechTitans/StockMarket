// stocks.js — watchlist management + card rendering

const API = "http://localhost:5000";
let stockData = [];
let watchlist = [];

const fmt  = n => isNaN(+n) ? "N/A" : (+n).toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtV = n => { const v=parseInt(n); if(isNaN(v)) return "N/A"; if(v>=1e7) return (v/1e7).toFixed(2)+" Cr"; if(v>=1e5) return (v/1e5).toFixed(2)+" L"; return v.toLocaleString("en-IN"); };

async function loadWatchlist() {
  const res = await fetch(`${API}/api/watchlist`);
  watchlist = await res.json();
}

function showSkeletons(n) {
  document.getElementById("stockGrid").innerHTML = Array(n||3).fill(0).map(() => `
    <div class="skel-card">
      <div class="skeleton skel-line" style="width:40%;margin-bottom:18px"></div>
      <div class="skeleton skel-line" style="width:65%"></div>
      <div class="skeleton skel-line" style="width:50%;height:28px;margin-bottom:16px"></div>
      <div class="skeleton skel-line" style="width:100%;height:60px"></div>
    </div>`).join("");
}

function showEmpty() {
  document.getElementById("stockGrid").innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">📭</div>
      <div class="empty-title">Your watchlist is empty</div>
      <div class="empty-sub">Click <strong>+ Add Stock</strong> to start tracking NSE/BSE stocks.</div>
    </div>`;
  document.getElementById("totalCount").textContent = "0";
  document.getElementById("gainersCount").textContent = "—";
  document.getElementById("losersCount").textContent = "—";
  document.getElementById("avgChange").textContent = "—";
  document.getElementById("stockCount").textContent = "0";
}

function renderCards(data) {
  const maxVol = Math.max(...data.filter(x => !x.error).map(x => parseInt(x.volume)||0));
  document.getElementById("stockGrid").innerHTML = data.map((s, i) => {
    if (s.error) return `
      <div style="background:rgba(235,87,87,.08);border:1px solid rgba(235,87,87,.25);border-radius:16px;padding:20px;display:flex;align-items:center;gap:12px">
        <span style="font-size:1.4rem">⚠️</span>
        <div style="flex:1">
          <div style="font-weight:700;font-family:var(--mono)">${s.symbol}</div>
          <div style="font-size:.82rem;color:var(--red);margin-top:4px">${s.error}</div>
        </div>
        <button class="remove-btn" onclick="event.stopPropagation();removeStock('${s.symbol}')">✕</button>
      </div>`;
    const up = s.change_pct >= 0, cls = up ? "up" : "down", sign = up ? "+" : "";
    const volPct = maxVol ? Math.round((parseInt(s.volume)||0) / maxVol * 100) : 0;
    return `
      <div class="stock-card ${cls}" style="animation-delay:${i*.05}s" onclick="openModal(${i})">
        <div class="card-top">
          <div class="card-top-left">
            <div class="stock-symbol">${s.symbol}</div>
            <div class="stock-name">${s.name}</div>
          </div>
          <div class="card-top-right">
            <div class="badge ${cls}">${up?"▲":"▼"} ${sign}${Math.abs(s.change_pct).toFixed(2)}%</div>
            <button class="remove-btn" onclick="event.stopPropagation();removeStock('${s.symbol}')">✕</button>
          </div>
        </div>
        <div class="price-row"><span class="currency">₹</span><span class="price">${fmt(s.price)}</span></div>
        <div class="stats-grid">
          <div class="stat"><div class="stat-label">Open</div><div class="stat-value">₹${fmt(s.open)}</div></div>
          <div class="stat"><div class="stat-label">Prev Close</div><div class="stat-value">₹${fmt(s.prev_close)}</div></div>
          <div class="stat"><div class="stat-label">High</div><div class="stat-value high-val">₹${fmt(s.high)}</div></div>
          <div class="stat"><div class="stat-label">Low</div><div class="stat-value low-val">₹${fmt(s.low)}</div></div>
        </div>
        <div class="volume-bar-wrap">
          <div class="volume-label">Vol</div>
          <div class="volume-track"><div class="volume-fill" style="width:${volPct}%"></div></div>
          <div class="volume-num">${fmtV(s.volume)}</div>
        </div>
      </div>`;
  }).join("");
}

function updateSummary(data) {
  const valid = data.filter(s => !s.error);
  const gainers = valid.filter(s => s.change_pct >= 0).length;
  const avg = valid.reduce((a, s) => a + s.change_pct, 0) / (valid.length || 1);
  document.getElementById("totalCount").textContent = valid.length;
  document.getElementById("gainersCount").textContent = gainers;
  document.getElementById("losersCount").textContent = valid.length - gainers;
  document.getElementById("stockCount").textContent = watchlist.length;
  const el = document.getElementById("avgChange");
  el.textContent = (avg >= 0 ? "+" : "") + avg.toFixed(2) + "%";
  el.style.color = avg >= 0 ? "var(--green)" : "var(--red)";
}

async function loadStocks() {
  const btn = document.getElementById("refreshBtn");
  btn.classList.add("loading");
  await loadWatchlist();
  if (!watchlist.length) { showEmpty(); btn.classList.remove("loading"); return; }
  showSkeletons(watchlist.length);
  try {
    const res = await fetch(`${API}/api/stocks`);
    if (!res.ok) throw new Error("Server error " + res.status);
    stockData = await res.json();
    renderCards(stockData);
    updateSummary(stockData);
    document.getElementById("lastUpdated").textContent = "Updated " + new Date().toLocaleTimeString("en-IN");
  } catch(e) {
    document.getElementById("stockGrid").innerHTML = `
      <div style="grid-column:1/-1;background:rgba(235,87,87,.08);border:1px solid rgba(235,87,87,.25);border-radius:16px;padding:24px;display:flex;align-items:center;gap:14px">
        <span style="font-size:1.6rem">🔌</span>
        <div><div style="font-weight:700">Connection Failed</div>
        <div style="font-size:.85rem;color:var(--red);margin-top:6px">${e.message}</div></div>
      </div>`;
  } finally { btn.classList.remove("loading"); }
}

// ── Add stock ──────────────────────────────────────────────────────────────
function openAddModal() {
  document.getElementById("symbolInput").value = "";
  document.getElementById("nameInput").value = "";
  document.getElementById("addError").className = "add-error";
  document.getElementById("addSuccess").className = "add-success";
  document.getElementById("addOverlay").classList.add("open");
  setTimeout(() => document.getElementById("symbolInput").focus(), 200);
}
function closeAddModal(e) { if (e.target === document.getElementById("addOverlay")) closeAddModalDirect(); }
function closeAddModalDirect() { document.getElementById("addOverlay").classList.remove("open"); }

function quickAdd(sym, name) {
  document.getElementById("symbolInput").value = sym;
  document.getElementById("nameInput").value = name;
  submitAdd();
}

async function submitAdd() {
  const sym  = document.getElementById("symbolInput").value.trim().toUpperCase();
  const name = document.getElementById("nameInput").value.trim();
  const errEl = document.getElementById("addError");
  const okEl  = document.getElementById("addSuccess");
  const btn   = document.getElementById("addBtn");
  if (!sym) { errEl.textContent = "Please enter a stock symbol."; errEl.className = "add-error show"; return; }
  errEl.className = "add-error"; okEl.className = "add-success";
  btn.textContent = "Adding…"; btn.disabled = true;
  try {
    const res = await fetch(`${API}/api/watchlist`, {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({symbol: sym, name: name || sym})
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.error || "Failed to add."; errEl.className = "add-error show"; return; }
    okEl.textContent = `✓ ${sym} added!`; okEl.className = "add-success show";
    document.getElementById("symbolInput").value = "";
    document.getElementById("nameInput").value = "";
    setTimeout(() => { closeAddModalDirect(); loadStocks(); }, 1000);
  } catch(e) {
    errEl.textContent = "Network error: " + e.message; errEl.className = "add-error show";
  } finally {
    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> Add to Watchlist';
    btn.disabled = false;
  }
}

async function removeStock(symbol) {
  if (!confirm(`Remove ${symbol} from watchlist?`)) return;
  try { await fetch(`${API}/api/watchlist/${symbol}`, {method:"DELETE"}); loadStocks(); }
  catch(e) { alert("Failed to remove: " + e.message); }
}

// Global escape key handler
document.addEventListener("keydown", e => {
  if (e.key === "Escape") { closeModalDirect(); closeAddModalDirect(); closeChatWindow(); }
});
// Auto refresh every 60 seconds
setInterval(() => {
  loadStocks();
}, 60 * 1000);