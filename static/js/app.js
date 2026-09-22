const state = { data: null, charts: {}, sourcesLoaded: false };

const CHART_SPECS = [
  { id: "btc", title: "Bitcoin (BTC)" },
  { id: "eth", title: "Ethereum (ETH)" },
  { id: "sol", title: "Solana (SOL)" },
  { id: "xrp", title: "XRP" },
  { id: "bnb", title: "BNB" },
  { id: "nifty", title: "NIFTY 50" },
  { id: "banknifty", title: "BANK NIFTY" },
  { id: "finnifty", title: "FINNIFTY" },
  { id: "sensex", title: "SENSEX" },
  { id: "bankex", title: "BANKEX" },
  { id: "vix", title: "INDIA VIX" },
  { id: "gold", title: "AU Gold (MCX)" },
  { id: "silver", title: "AG Silver (MCX)" },
  { id: "crude", title: "Crude Oil" },
  { id: "natgas", title: "Natural Gas" },
  { id: "copper", title: "Copper" },
  { id: "aluminium", title: "Aluminium" },
  { id: "zinc", title: "Zinc" },
];
const CHART_GROUPS = [
  { id: "crypto", title: "Crypto", sub: "Top 5 coins · Binance live", ids: ["btc", "eth", "sol", "xrp", "bnb"] },
  { id: "nse", title: "NSE", sub: "Nifty, Bank Nifty, FinNifty, Sensex, Bankex, India VIX", ids: ["nifty", "banknifty", "finnifty", "sensex", "bankex", "vix"] },
  { id: "mcx", title: "MCX", sub: "Gold, silver, crude, natural gas, copper, aluminium, zinc", ids: ["gold", "silver", "crude", "natgas", "copper", "aluminium", "zinc"] },
];
const HOME_CHART_IDS = ["btc", "nifty", "gold", "eth", "sensex", "silver"];
const TIMEFRAMES = ["1d", "1w", "1m", "1y"];

function artClass(key) {
  const s = String(key || "").toUpperCase();
  if (s.includes("BTC") || s.includes("BITCOIN")) return "art-btc";
  if (s.includes("ETHEREUM") || /(^|[^A-Z])ETH([^A-Z]|$)/.test(s)) return "art-eth";
  if (s.includes("SOL")) return "art-sol";
  if (s.includes("XRP")) return "art-xrp";
  if (s.includes("BNB")) return "art-bnb";
  if (s.includes("GOLD")) return "art-gold";
  if (s.includes("SILVER")) return "art-silver";
  if (s.includes("ALUMINIUM") || s.includes("ALUMINUM")) return "art-alu";
  if (s.includes("COPPER")) return "art-copper";
  if (s.includes("ZINC")) return "art-zinc";
  if (s.includes("CRUDE") || s.includes("OIL") || s.includes("NATGAS") || s.includes("NATURAL")) return "art-crude";
  if (s.includes("VIX")) return "art-vix";
  if (s.includes("BANK") || s.includes("FINNIFTY") || s.includes("HDFC") || s.includes("ICICI") || s.includes("SBIN")) return "art-bank";
  if (s.includes("SENSEX") || s.includes("NIFTY") || s.includes("NSE")) return "art-nifty";
  if (s.includes("DXY") || s.includes("USD") || s.includes("FX")) return "art-fx";
  if (s.includes("10Y") || s.includes("RATE")) return "art-rates";
  if (s.includes("RELIANCE") || s.includes("TCS") || s.includes("INFY")) return "art-stock";
  if (s.includes("SPX") || s.includes("NASDAQ") || s.includes("DOW") || s.includes("DAX") || s.includes("NIKKEI") || s.includes("HANG") || s.includes("FTSE")) return "art-global";
  return "art-global";
}

function artGlyph(key) {
  const s = String(key || "").toUpperCase();
  if (s.includes("BTC")) return "₿";
  if (s.includes("ETHEREUM") || /(^|[^A-Z])ETH([^A-Z]|$)/.test(s)) return "Ξ";
  if (s.includes("GOLD")) return "Au";
  if (s.includes("SILVER")) return "Ag";
  if (s.includes("ALUMINIUM") || s.includes("ALUMINUM")) return "Al";
  if (s.includes("COPPER")) return "Cu";
  if (s.includes("ZINC")) return "Zn";
  if (s.includes("CRUDE") || s.includes("OIL") || s.includes("NATGAS") || s.includes("NATURAL")) return "🛢";
  if (s.includes("VIX")) return "⚡";
  if (s.includes("NIFTY") || s.includes("SENSEX") || s.includes("BANKEX")) return "🇮🇳";
  return (s.replace(/[^A-Z]/g, "").slice(0, 2) || "•");
}

function badge(key, cls) {
  return `<span class="${cls || "dot"} ${artClass(key)}"><span class="glyph">${artGlyph(key)}</span></span>`;
}

function newsArt(n) {
  const m = (n.market || "").toLowerCase();
  const t = (n.title || "").toLowerCase();
  if (m.includes("crypto") || /bitcoin|ethereum|crypto|token/.test(t)) return "art-news-crypto";
  if (m.includes("geo") || /war|china|ukraine|israel|gaza|nato|russia/.test(t)) return "art-news-geo";
  return "art-news-biz";
}

function newsHeroFile(n) {
  const cls = newsArt(n);
  if (cls.includes("crypto")) return "/static/img/news-crypto.svg";
  if (cls.includes("geo")) return "/static/img/news-geo.svg";
  return "/static/img/news-global.svg";
}

function newsThumb(n) {
  const cls = newsArt(n);
  const src = n.image || newsHeroFile(n);
  return `<div class="thumb ${cls}"><img src="${src}" alt="" referrerpolicy="no-referrer" /></div>`;
}

function escHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function usdCap(v) {
  if (v === null || v === undefined || v === "") return "—";
  return "$" + fmt(v);
}

function newsCard(n, i) {
  const hero = n.image || newsHeroFile(n);
  return `<button type="button" class="news-card" data-news="${i}">
    <div class="news-hero ${newsArt(n)}">
      <img src="${hero}" alt="" referrerpolicy="no-referrer" />
      <span class="news-kicker">${escHtml(n.market || "Global")}</span>
    </div>
    <div class="news-card-body">
      <b>${escHtml(n.title)}</b>
      <p>${escHtml((n.summary || "").slice(0, 160))}</p>
      <div class="text-secondary">${escHtml(n.source)} · ${escHtml(n.age)}</div>
    </div>
  </button>`;
}

function openNews(n) {
  if (!n) return;
  const hero = n.image || newsHeroFile(n);
  const dlg = document.querySelector(".why-dialog");
  if (dlg) dlg.classList.add("wide");
  document.getElementById("modalTitle").textContent = n.market || "News";
  document.getElementById("modalBody").innerHTML = `
    <div class="news-modal-hero ${newsArt(n)}"><img src="${hero}" alt="" referrerpolicy="no-referrer" /></div>
    <p class="mb-1 mt-3"><b>${escHtml(n.title)}</b></p>
    <p class="text-secondary">${escHtml(n.source)} · ${escHtml(n.age)}</p>
    <p class="why-plain">${escHtml(n.summary || "Full story is on the publisher page.")}</p>
    ${impactBox(n.impact_card)}
    ${n.url ? `<p class="mb-0"><a class="btn btn-sm btn-primary" href="${escHtml(n.url)}" target="_blank" rel="noopener">Open full article</a></p>` : ""}
  `;
  document.getElementById("modal").classList.add("show");
}

function freshness(q) {
  const tape = (q.extra && q.extra.tape) || "";
  const label = tape === "live" ? "Live" : tape === "closed" ? "Session closed" : tape === "delayed" ? "Delayed" : q.source_type;
  return `<span class="tape-${tape || "live"}">${label}</span>`;
}

const fmt = (n, d = 2) => {
  if (n === null || n === undefined) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e12) return (n / 1e12).toFixed(2) + "T";
  if (abs >= 1e7 && d === "inr") return (n / 1e7).toFixed(2) + " Cr";
  if (abs >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (abs >= 1000) return n.toLocaleString("en-US", { maximumFractionDigits: d });
  return Number(n).toLocaleString("en-US", { maximumFractionDigits: d });
};

const money = (q) => {
  if (q.currency === "%") return q.ltp.toFixed(2) + "%";
  if (q.currency === "INR") return "₹" + fmt(q.ltp, q.ltp < 100 ? 2 : 0);
  if (q.currency === "USD" && q.ltp < 10) return "$" + q.ltp.toFixed(3);
  if (q.currency === "USD") return "$" + fmt(q.ltp, q.ltp < 1000 ? 2 : 0);
  return fmt(q.ltp, 2);
};

const chg = (pct) => {
  const cls = pct >= 0 ? "up" : "down";
  const sign = pct >= 0 ? "+" : "";
  return `<span class="${cls}">${sign}${pct.toFixed(2)}%</span>`;
};

const dir = (pct) => (pct > 0.05 ? "↑" : pct < -0.05 ? "↓" : "→");

function clock() {
  const now = new Date();
  const opts = { weekday: "short", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" };
  document.getElementById("clock").textContent = now.toLocaleString("en-IN", opts) + " IST";
}

function showPage(id) {
  document.querySelectorAll(".page").forEach((p) => {
    const on = p.id === "page-" + id;
    p.classList.toggle("active", on);
    p.hidden = !on;
  });
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === id));
  if (id === "settings") loadSettings();
  if (id === "sources") loadSources();
  if (id === "charts") mountChartsPage();
  if (id === "fo") loadFO();
  requestAnimationFrame(() => {
    Object.values(state.charts).forEach((rec) => {
      if (rec && rec.chart) rec.chart.timeScale().fitContent();
    });
  });
}

async function loadSettings() {
  const res = await fetch("/api/settings");
  const data = await res.json();
  const root = document.getElementById("settingsRoot");
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
  const isSecret = (f) => f.includes("secret") || f.includes("token") || f.endsWith("jkey") || f.endsWith("_key");
  root.innerHTML = `<form id="settingsForm">` + data.portals.map((p) => {
    const st = data.status[p.id] || {};
    const on = st.ok === true || st === true;
    const label = st.label || (on ? "Connected" : "Not connected");
    const fields = (p.fields || []).map((f) => {
      const kept = data.filled && data.filled[f];
      const shown = isSecret(f) ? "" : (data.values[f] || "");
      const ph = isSecret(f) && kept ? "Saved on this PC — leave blank to keep" : "";
      return `<label class="d-block mb-2">${esc(data.labels[f] || f)}
        <input name="${esc(f)}" value="${esc(shown)}" placeholder="${esc(ph)}" autocomplete="off" ${isSecret(f) ? "type='password'" : "type='text'"} />
      </label>`;
    }).join("");
    return `<div class="portal" data-portal="${p.id}">
      <div class="d-flex justify-content-between gap-2">
        <h3 class="mb-1">${esc(p.name)}</h3>
        <span class="${on ? "ok-dot" : "no-dot"}">${esc(label)}</span>
      </div>
      <div class="text-secondary">${esc(p.role)}</div>
      <p class="mt-2 mb-2">${esc(p.how)}</p>
      <div><a href="${esc(p.url)}" target="_blank" rel="noopener">Open portal</a>${p.docs ? ` · <a href="${esc(p.docs)}" target="_blank" rel="noopener">Docs</a>` : ""}</div>
      <div class="mt-3">${fields}</div>
      ${p.id === "dhan" ? dhanTools() : ""}
    </div>`;
  }).join("") + `<div class="card">
      <div class="d-flex gap-2 flex-wrap">
        <button type="submit" class="tf-btn on" id="saveKeys">Save all keys</button>
        <button type="button" class="tf-btn" id="verifyKeys">Test connections</button>
      </div>
      <p class="text-secondary mt-2 mb-0">Keys stay on this computer in data/secrets.json. Blank secret fields are not wiped. Dhan needs Client ID + Access Token (not only API key).</p>
      <div id="saveMsg" class="mt-2"></div>
    </div></form>`;
  const form = document.getElementById("settingsForm");
  const saveMsg = document.getElementById("saveMsg");
  const collect = () => {
    const keys = {};
    form.querySelectorAll("input[name]").forEach((el) => { keys[el.name] = el.value; });
    return keys;
  };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    saveMsg.textContent = "Saving…";
    saveMsg.className = "text-secondary mt-2";
    try {
      const data = await (await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keys: collect() }),
      })).json();
      saveMsg.textContent = data.ok ? (data.message || "Saved.") : (data.error || "Save failed.");
      saveMsg.className = data.ok ? "ok-dot mt-2" : "no-dot mt-2";
      if (data.ok) loadSettings();
    } catch (err) {
      saveMsg.textContent = "Save failed: " + err;
      saveMsg.className = "no-dot mt-2";
    }
  });
  document.getElementById("verifyKeys").onclick = async () => {
    saveMsg.textContent = "Testing…";
    const data = await (await fetch("/api/settings/verify", { method: "POST" })).json();
    const lines = Object.entries(data.accounts || {}).map(([id, v]) => `${id}: ${v.ok ? "OK" : "FAIL"} — ${v.message || v.error || ""}`);
    saveMsg.innerHTML = lines.map((t) => `<div>${t.replace(/</g, "")}</div>`).join("");
    saveMsg.className = data.ok ? "ok-dot mt-2" : "no-dot mt-2";
  };
  const dhanMsg = document.getElementById("dhanMsg");
  const dhanVal = (name) => form.querySelector(`input[name="${name}"]`)?.value || "";
  const showDhan = (payload) => {
    if (!dhanMsg) return;
    dhanMsg.textContent = payload.message || payload.error || JSON.stringify(payload);
    dhanMsg.className = payload.ok ? "ok-dot mt-2" : "no-dot mt-2";
  };
  const dhanConnect = document.getElementById("dhanConnect");
  if (dhanConnect) dhanConnect.onclick = async () => {
    const payload = await (await fetch("/api/dhan/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dhan_client_id: dhanVal("dhan_client_id"), dhan_access_token: dhanVal("dhan_access_token") }),
    })).json();
    showDhan(payload);
    if (payload.ok) loadSettings();
  };
  const dhanRenew = document.getElementById("dhanRenew");
  if (dhanRenew) dhanRenew.onclick = async () => {
    const payload = await (await fetch("/api/dhan/renew", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dhan_client_id: dhanVal("dhan_client_id"), dhan_access_token: dhanVal("dhan_access_token") }),
    })).json();
    showDhan(payload);
    if (payload.ok) loadSettings();
  };
  const dhanTotp = document.getElementById("dhanTotp");
  if (dhanTotp) dhanTotp.onclick = async () => {
    const payload = await (await fetch("/api/dhan/totp-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dhan_client_id: dhanVal("dhan_client_id"),
        pin: document.getElementById("dhanPin")?.value || "",
        totp: document.getElementById("dhanTotpCode")?.value || "",
      }),
    })).json();
    showDhan(payload);
    if (payload.ok) loadSettings();
  };
}

function dhanTools() {
  return `<div class="dhan-tools mt-3">
    <button type="button" class="tf-btn on" id="dhanConnect">Connect with Client ID + Access Token</button>
    <button type="button" class="tf-btn" id="dhanRenew">Renew 24h token</button>
    <a class="tf-btn" href="https://web.dhan.co" target="_blank" rel="noopener">Open Dhan Web for API Key</a>
    <p class="text-secondary mt-2 mb-1">API Key / Secret cannot be created from a token. Dhan only shows them after you toggle <b>API Key</b> on My Profile → Access DhanHQ APIs. Quotes on this board work without them.</p>
    <p class="text-secondary mb-1">If TOTP is enabled on Dhan, mint a fresh <b>access token</b> (not API key):</p>
    <div class="d-flex gap-2 flex-wrap">
      <input id="dhanPin" type="password" placeholder="Dhan PIN" style="max-width:140px" />
      <input id="dhanTotpCode" type="text" inputmode="numeric" placeholder="TOTP" style="max-width:140px" />
      <button type="button" class="tf-btn" id="dhanTotp">Get access token</button>
    </div>
    <div id="dhanMsg" class="mt-2"></div>
  </div>`;
}

function sparkSvg(values, up) {
  if (!values || values.length < 2) return "";
  const w = 54, h = 22;
  const min = Math.min(...values), max = Math.max(...values);
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / (max - min || 1)) * (h - 2) - 1;
    return `${x},${y}`;
  }).join(" ");
  const color = up ? "#137333" : "#d93025";
  return `<svg class="spark" viewBox="0 0 ${w} ${h}"><polyline fill="none" stroke="${color}" stroke-width="1.6" points="${pts}"/></svg>`;
}

function alertClass(symbol, alerts) {
  const hit = alerts.find((a) => a.highlight_symbol === symbol || a.asset === symbol || (a.related_assets || []).includes(symbol));
  return hit ? "alert-" + hit.tone : "";
}

function asof(q) {
  if (!q || !q.as_of) return "";
  return new Date(q.as_of).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Asia/Kolkata" });
}

function renderPulse(data) {
  const el = document.getElementById("pulse");
  el.innerHTML = data.pulse.map((q) => `
    <div class="pulse ${alertClass(q.symbol, data.alerts)}">
      <div class="pulse-art ${artClass(q.canonical || q.symbol)}"></div>
      <div class="k"><span>${badge(q.canonical || q.symbol, "chart-mark")}${q.symbol}</span>${sparkSvg(q.sparkline, q.change_pct >= 0)}</div>
      <div class="px">${money(q)}</div>
      <div class="chg">${chg(q.change_pct)}</div>
      <div class="asof">${asof(q)} IST · ${freshness(q)}</div>
    </div>`).join("");
}

function renderAlerts(list, mount) {
  mount.innerHTML = list.map((a) => `
    <div class="alert-item tone-${a.tone}" data-alert="${a.id}">
      <div>
        <b>${a.title}</b>
        <span>${a.detail} · ${new Date(a.detected_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" })} IST</span>
        ${impactBox(a.impact)}
      </div>
      <button type="button" class="why-btn" data-why="${a.id}">WHY?</button>
    </div>`).join("");
}

function rowBlock(rows, extra) {
  return rows.map((q) => `
    <div class="rowline">
      <div class="sym">${badge(q.canonical || q.symbol)}<span>${q.symbol}</span></div>
      <div>${extra ? extra(q) : money(q)}</div>
      <div class="pill ${q.change_pct >= 0 ? "up" : "down"}">${chg(q.change_pct)}</div>
    </div>`).join("");
}

function bindFolds() {
  document.querySelectorAll(".fold").forEach((fold) => {
    const key = "fold-" + fold.dataset.fold;
    if (localStorage.getItem(key) === "1") fold.classList.add("collapsed");
    const head = fold.querySelector(".fold-head");
    if (!head || head.dataset.bound) return;
    head.dataset.bound = "1";
    head.addEventListener("click", () => {
      fold.classList.toggle("collapsed");
      localStorage.setItem(key, fold.classList.contains("collapsed") ? "1" : "0");
    });
  });
}

function mountChartGrid(gridId, specs, prefix) {
  const grid = document.getElementById(gridId);
  if (!grid || grid.dataset.ready) return;
  grid.dataset.ready = "1";
  grid.innerHTML = specs.map((c) => {
    const key = `${prefix}-${c.id}`;
    return `
    <div class="card chart-card" data-chart="${c.id}" data-key="${key}">
      <div class="chart-wash ${artClass(c.id + " " + c.title)}"></div>
      <div class="chart-meta">
        <div>
          <div class="text-secondary small">${badge(c.id + " " + c.title, "chart-mark")}${c.title}</div>
          <div class="h4 mb-0" id="head-${key}">—</div>
        </div>
        <div class="tabs">
          ${TIMEFRAMES.map((tf) => `<button type="button" class="tf-btn${tf === "1d" ? " on" : ""}" data-tf="${tf}">${tf.toUpperCase()}</button>`).join("")}
        </div>
      </div>
      <div class="chart-box" id="pane-${key}"></div>
      <div class="stats" id="stats-${key}"></div>
      <div class="text-secondary small mt-2" id="src-${key}"></div>
    </div>`;
  }).join("");
  grid.querySelectorAll(".tf-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".chart-card");
      card.querySelectorAll(".tf-btn").forEach((b) => b.classList.toggle("on", b === btn));
      loadCandle(card.dataset.chart, btn.dataset.tf, card.dataset.key);
    });
  });
  specs.forEach((c, i) => setTimeout(() => loadCandle(c.id, "1d", `${prefix}-${c.id}`), i * 90));
}

function mountChartsPage() {
  const root = document.getElementById("chartsPageRoot");
  if (!root || root.dataset.ready) return;
  root.dataset.ready = "1";
  root.innerHTML = CHART_GROUPS.map((g) => `
    <section class="chart-cat">
      <div class="chart-cat-head">
        <h3>${g.title} <span class="sub">${g.sub}</span></h3>
      </div>
      <div class="charts-grid" id="grid-${g.id}"></div>
    </section>`).join("");
  CHART_GROUPS.forEach((g) => {
    const specs = g.ids.map((id) => CHART_SPECS.find((c) => c.id === id)).filter(Boolean);
    mountChartGrid("grid-" + g.id, specs, g.id);
  });
}

function destroyChart(id) {
  const rec = state.charts[id];
  if (rec && rec.chart) {
    rec.chart.remove();
  }
  state.charts[id] = null;
}

async function loadCandle(id, tf, paneKey = id) {
  const pane = document.getElementById("pane-" + paneKey);
  const src = document.getElementById("src-" + paneKey);
  if (!pane || typeof LightweightCharts === "undefined") return;
  try {
    const res = await fetch(`/api/candles/${id}?tf=${tf}`);
    const data = await res.json();
    if (src) {
      const link = data.source_url ? `<a href="${data.source_url}" target="_blank" rel="noopener">${data.source || "Source"}</a>` : (data.source || "");
      src.innerHTML = data.error ? `${link} · ${data.error}` : `${link} · ${tf.toUpperCase()}`;
    }
    destroyChart(paneKey);
    const chart = LightweightCharts.createChart(pane, {
      width: pane.clientWidth || 360,
      height: pane.clientHeight || 240,
      layout: { background: { color: "#ffffff" }, textColor: "#5f6368", fontFamily: "Roboto, Arial, sans-serif" },
      grid: { vertLines: { color: "#f1f3f4" }, horzLines: { color: "#f1f3f4" } },
      rightPriceScale: { borderColor: "#dadce0" },
      timeScale: { borderColor: "#dadce0", timeVisible: tf === "1d" || tf === "1w", secondsVisible: false },
      crosshair: { mode: 0 },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#137333",
      downColor: "#d93025",
      borderUpColor: "#137333",
      borderDownColor: "#d93025",
      wickUpColor: "#137333",
      wickDownColor: "#d93025",
    });
    const bars = (data.candles || []).map((b) => ({
      time: b.time,
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));
    series.setData(bars);
    chart.timeScale().fitContent();
    state.charts[paneKey] = { chart, series, tf };
    const ro = new ResizeObserver(() => {
      if (state.charts[paneKey] && state.charts[paneKey].chart) {
        state.charts[paneKey].chart.applyOptions({ width: pane.clientWidth, height: pane.clientHeight || 240 });
      }
    });
    ro.observe(pane);
  } catch (err) {
    if (src) src.textContent = "Chart unavailable";
  }
}

async function loadSources() {
  const res = await fetch("/api/sources");
  const data = await res.json();
  const el = document.getElementById("page-sources");
  el.innerHTML = `
    <div class="card mb-3">
      <div class="card-head"><h3>Live market APIs to subscribe</h3><span class="sub">Exchange-licensed or broker feeds — not delayed Yahoo</span></div>
      <p class="text-secondary">This board uses Dhan for NSE/BSE/MCX when your access token is connected, and Binance for crypto. Yahoo stays only as a research fallback (US indices, DXY, 10Y) and for charts if Dhan is not logged in. NSE/MCX official realtime cannot be scraped; it has to come from a broker or a licensed vendor.</p>
      <div class="source-grid">
        ${(data.live_feeds || []).map((w) => `
          <div class="source-card">
            <a href="${w.url}" target="_blank" rel="noopener">${w.name}</a>
            <div class="text-secondary mt-1">${w.use}</div>
            <div class="text-secondary mt-1">${w.cost || ""}</div>
          </div>`).join("")}
      </div>
    </div>
    <div class="card mb-3">
      <div class="card-head"><h3>Data sources</h3><span class="sub">Official and research websites used by this board</span></div>
      <div class="source-grid">
        ${(data.websites || []).map((w) => `
          <div class="source-card">
            <a href="${w.url}" target="_blank" rel="noopener">${w.name}</a>
            <div class="text-secondary mt-1">${w.use}</div>
          </div>`).join("")}
      </div>
    </div>
    <div class="card">
      <div class="card-head"><h3>Chart feeds</h3></div>
      <div class="source-grid">
        ${(data.charts || []).map((c) => `
          <div class="source-card">
            <b>${c.title}</b>
            <div><a href="${c.source_url}" target="_blank" rel="noopener">${c.source}</a></div>
          </div>`).join("")}
      </div>
    </div>`;
}

function impactBox(card) {
  if (!card) return "";
  const legs = (card.legs || []).map((l) => `<span class="expect-pill ${l.direction}">${l.asset} ${l.direction}${l.note ? " · " + l.note : ""}</span>`).join("");
  return `<div class="impact-box ${card.certainty} ${card.trigger}">
    <div class="impact-kicker">IMPACT · ${card.trigger.toUpperCase()} · ${card.certainty.toUpperCase()}</div>
    <b>${card.headline}</b>
    <div class="text-secondary">${card.detail || ""}</div>
    <div class="mt-1">${legs}</div>
  </div>`;
}

function makeGauge(el, score) {
  if (!el) return;
  const color = score >= 62 ? "#137333" : score <= 40 ? "#d93025" : "#f9ab00";
  const sweep = (score / 100) * 251.2;
  el.innerHTML = `<svg viewBox="0 0 200 110" width="140" height="78">
    <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="#e8eaed" stroke-width="14" stroke-linecap="round"/>
    <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="${color}" stroke-width="14" stroke-linecap="round" pathLength="251.2" stroke-dasharray="${sweep} 251.2"/>
  </svg>`;
}

function stats(q, keys) {
  if (!q) return "";
  return keys.map(([k, v]) => `<div>${k}<b>${v}</div>`).join("");
}

function briefRow(b) {
  return `<div class="matter ${b.status || ""}">
      <div class="num">${b.rank}</div>
      <div>
        <b>${b.title}</b>
        <div class="text-secondary">${b.impact}</div>
        ${impactBox(b.impact_card)}
      </div>
      <div>
        <span class="sev ${b.status || b.importance}">${(b.status || "").toUpperCase()}</span>
        <div class="text-secondary">${b.event_time_label}</div>
      </div>
    </div>`;
}

function openWhy(alert) {
  const w = alert.why || {};
  const esc = (s) => String(s ?? "").replace(/</g, "&lt;");
  const affect = ((alert.impact && alert.impact.legs) || []).map((l) => l.asset).filter(Boolean);
  const dlg = document.querySelector(".why-dialog");
  if (dlg) dlg.classList.remove("wide");
  document.getElementById("modalTitle").textContent = "WHY?";
  document.getElementById("modalBody").innerHTML = `
    <p class="mb-2"><b>${esc(alert.title)}</b></p>
    <p id="whyPlain" class="why-plain">Reading the tape and related news…</p>
    <p class="text-secondary" id="whyMeta"></p>
    ${affect.length ? `<p class="mb-1"><b>Can affect</b> ${esc(affect.join(", "))}</p>` : ""}
    <p class="text-secondary mb-0">${esc(w.trigger || w.primary || "")}</p>
  `;
  document.getElementById("modal").classList.add("show");
  fetch("/api/alerts/why", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: alert.id }),
  }).then((r) => r.json()).then((data) => {
    const el = document.getElementById("whyPlain");
    const meta = document.getElementById("whyMeta");
    if (!el) return;
    if (!data.ok) {
      el.textContent = data.error || "Could not explain this alert.";
      return;
    }
    el.textContent = data.plain || w.primary || alert.detail;
    if (meta) {
      const from = data.source === "deepseek" ? "Simple reason · DeepSeek" : "Simple reason · board rules + news";
      const news = (data.headlines || []).slice(0, 2).join(" · ");
      meta.textContent = news ? `${from}. News in view: ${news}` : from;
    }
  }).catch(() => {
    const el = document.getElementById("whyPlain");
    if (el) el.textContent = w.trigger || w.primary || "This alert fired because a price or news rule was met.";
  });
}

function renderSentiment(d) {
  const root = document.getElementById("sentimentStack");
  if (!root) return;
  const markets = (d.sentiment && d.sentiment.markets) || [];
  root.innerHTML = markets.map((m) => `
    <div class="sent-block">
      <div class="sent-title"><b>${m.title}</b><span class="sub">${m.label}</span></div>
      <div class="gauge-wrap">
        <div class="gauge" id="gauge-${m.id}"></div>
        <div>
          <div class="h3 mb-0">${m.score}</div>
          <div class="kpi">${(m.kpis || []).join(" · ")}</div>
        </div>
      </div>
      <div class="quote-box">${m.note || ""}</div>
    </div>`).join("") || `<div class="text-secondary">Sentiment loading…</div>`;
  markets.forEach((m) => makeGauge(document.getElementById("gauge-" + m.id), m.score));
}

function tablePage(title, note, rows, cols) {
  return `<div class="card"><div class="card-head"><h3>${title}</h3><span class="sub">${note || ""}</span></div>
    <table class="table"><thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

function renderPages(d) {
  const qRows = (list) => list.map((q) => `<tr>
    <td>${q.name}</td><td>${money(q)}</td><td>${chg(q.change_pct)}</td>
    <td>${q.high ? fmt(q.high) : "—"}</td><td>${q.low ? fmt(q.low) : "—"}</td>
    <td>${q.volume ? fmt(q.volume, 0) : "—"}</td><td>${q.oi ? fmt(q.oi, 0) : "—"}</td>
    <td>${q.source}</td></tr>`).join("");
  const cols = ["Symbol", "LTP", "Change", "High", "Low", "Volume", "OI", "Source"];

  const na = (v, suffix = "") => (v === null || v === undefined || v === "") ? "Awaiting official feed" : `${v}${suffix}`;
  const ind = d.india_structure;
  document.getElementById("page-india").innerHTML = `
    ${tablePage("India indices", "Live via Yahoo research feed until NSE/broker is connected.", qRows(d.india), cols)}
    <div class="grid-4b mt-3">
      <div class="card"><h3>Institutional flows</h3>
        <div class="rowline"><span>FII</span><b>${na(ind.fii, " Cr")}</b></div>
        <div class="rowline"><span>DII</span><b>${na(ind.dii, " Cr")}</b></div>
      </div>
      <div class="card"><h3>Market breadth</h3>
        <div class="rowline"><span>Advances</span><b>${na(ind.advances)}</b></div>
        <div class="rowline"><span>Declines</span><b>${na(ind.declines)}</b></div>
        <div class="rowline"><span>New highs</span><b>${na(ind.new_highs)}</b></div>
        <div class="rowline"><span>New lows</span><b>${na(ind.new_lows)}</b></div>
      </div>
      <div class="card"><h3>Global macro (India-relevant)</h3>${d.macro.slice(0,5).map((m) => `<div class="rowline"><span>${m.label}</span><b>${m.value}</b></div>`).join("")}</div>
      <div class="card"><h3>F&amp;O</h3><p class="text-secondary">${ind.fo_note}</p><button class="view-more" data-page-jump="fo">Open F&amp;O page</button></div>
    </div>`;

  document.getElementById("page-stocks").innerHTML = tablePage("Selected stocks", "Only your watchlist names.", qRows(d.watchlist), cols);
  const foPage = document.getElementById("page-fo");
  if (!foPage.dataset.ready) {
    foPage.innerHTML = `<div class="card mb-3"><div class="card-head"><h3>F&amp;O / Open Interest</h3><span class="sub">Index options and cash options · Dhan chain</span></div><p class="text-secondary mb-0">PCR, total OI and heavy strikes load when you open this page. Participant OI uses the NSE daily file when it is published.</p></div><div id="foRoot"></div>`;
    foPage.dataset.ready = "1";
  }
  document.getElementById("page-mcx").innerHTML = tablePage("MCX commodities", "Primary source target: MCX market watch / broker.", qRows(d.mcx), cols);
  const cs = d.crypto_structure || {};
  const structRow = (label, value, why) => `<div class="struct-card"><div class="rowline"><span>${label}</span><b>${value}</b></div><p class="text-secondary mb-0">${why}</p></div>`;
  document.getElementById("page-crypto").innerHTML = `
    ${tablePage("Crypto market", "Spot from Binance when live. Structure from CoinGecko + Delta funding.", qRows(d.crypto.filter(c => c.symbol !== "TOTALCAP")), cols)}
    <div class="card mt-3">
      <div class="card-head"><h3>Structure</h3><span class="sub">${cs.note || "Market-wide context, not a trade signal."}</span></div>
      <div class="struct-grid">
        ${structRow("BTC dominance", cs.btc_dominance == null ? "—" : Number(cs.btc_dominance).toFixed(1) + "%", "Share of total crypto value in Bitcoin. Rising dominance often means risk-off inside crypto.")}
        ${structRow("ETH dominance", cs.eth_dominance == null ? "—" : Number(cs.eth_dominance).toFixed(1) + "%", "Ethereum share of crypto value. Useful next to BTC.D for rotation vs Bitcoin.")}
        ${structRow("Total mcap", usdCap(cs.total_mcap), "Size of the whole crypto market. Use this, not a single coin, for liquidity context.")}
        ${structRow("24h volume", usdCap(cs.total_volume), "How much is actually trading. Thin volume makes the same % move less trustworthy.")}
        ${structRow("Stablecoin mcap", usdCap(cs.stablecoin_mcap), "USDT+USDC dry powder. Rising stables can mean cash waiting on the sidelines.")}
        ${structRow("Funding", cs.funding || "—", "Perp funding from Delta India when the ticker is up. Positive = longs pay shorts.")}
        ${structRow("Open interest", cs.open_interest == null ? "—" : fmt(cs.open_interest, 0), "Open derivative notional when Delta reports it. Rising OI with price = trend confirmation.")}
        ${structRow("Tracked 5-coin mcap", usdCap(cs.tracked_mcap), "Sum of BTC/ETH/SOL/XRP/BNB market caps from CoinGecko. Fallback if global feed is rate-limited.")}
      </div>
    </div>`;
  const macroRows = (d.macro || []).map((m) => `<tr>
    <td><b>${escHtml(m.label)}</b></td>
    <td>${escHtml(m.value)}</td>
    <td>${m.change ? `<span class="${String(m.change).trim().startsWith("-") ? "down" : "up"}">${escHtml(m.change)}</span>` : "—"}</td>
    <td>${escHtml(m.when || "")}</td>
    <td>${escHtml(m.why || "")}</td>
    <td>${escHtml(m.watch || "")}</td>
    <td><span class="tag">${escHtml(m.status)}</span><div class="text-secondary">${escHtml(m.source || "")}</div></td>
  </tr>`).join("");
  document.getElementById("page-global").innerHTML = `
    ${tablePage("Global indices", "Research fallback: Yahoo. Official: Fed / BLS / Treasury.", qRows(d.global_markets), cols)}
    <div class="card mt-3">
      <div class="card-head"><h3>Macro tape</h3><span class="sub">Why the print matters and what to watch next to it</span></div>
      <div class="table-wrap">
        <table class="table macro-table">
          <thead><tr><th>Print</th><th>Level / status</th><th>Change</th><th>When</th><th>Why it matters</th><th>Watch with</th><th>Source</th></tr></thead>
          <tbody>${macroRows}</tbody>
        </table>
      </div>
    </div>`;
  document.getElementById("page-calendar").innerHTML = `<div class="card"><h3>Economic calendar · IST</h3>${d.briefing.map(briefRow).join("")}</div>`;
  document.getElementById("page-alerts").innerHTML = `<div class="card"><div class="card-head"><h3>Active alerts</h3><span class="sub">History and rules in Settings</span></div><div id="alertsAll"></div></div>`;
  renderAlerts(d.alerts, document.getElementById("alertsAll"));
  document.getElementById("page-watchlist").innerHTML = tablePage("My watchlist", "Configurable names only.", qRows(d.watchlist), cols);
  const news = d.news || [];
  const cats = ["Geopolitics", "Global", "Crypto"];
  const newsSections = cats.map((cat) => {
    const list = news.filter((n) => (n.market || "Global") === cat);
    if (!list.length) return "";
    const banner = cat === "Crypto" ? "/static/img/news-crypto.svg" : cat === "Geopolitics" ? "/static/img/news-geo.svg" : "/static/img/news-global.svg";
    return `<div class="news-section">
      <div class="news-banner ${newsArt({ market: cat })}"><img src="${banner}" alt=""/><h3>${cat}</h3></div>
      <div class="news-grid">${list.map((n) => newsCard(n, news.indexOf(n))).join("")}</div>
    </div>`;
  }).join("");
  document.getElementById("page-news").innerHTML = `<div class="card mb-3"><h3>Contextual news</h3><p class="text-secondary mb-0">Click a story for the summary, mapped impact, and a link to the publisher. Graphics mark Global, Geopolitics and Crypto.</p></div>${newsSections || `<div class="card"><p class="text-secondary mb-0">No headlines yet.</p></div>`}`;
}

function render(d) {
  state.data = d;
  renderPulse(d);
  renderAlerts(d.alerts.slice(0, 5), document.getElementById("alertsHome"));
  document.getElementById("navAlertCount").textContent = d.alert_count;
  document.getElementById("bellCount").textContent = d.alert_count;
  document.getElementById("alertBadge").textContent = d.alert_count;
  document.getElementById("alertChip").textContent = d.alert_count;
  document.getElementById("riskChip").textContent = d.global_risk;
  document.getElementById("liqChip").textContent = d.liquidity;
  document.getElementById("regimeChip").textContent = d.regime;

  const pools = [...(d.pulse || []), ...(d.india || []), ...(d.mcx || []), ...(d.crypto || [])];
  const findQ = (canon) => pools.find((q) => q.canonical === canon);
  const quoteFor = {
    btc: findQ("CRYPTO:BTC") || pools.find((q) => q.symbol === "BTC"),
    eth: findQ("CRYPTO:ETH") || pools.find((q) => q.symbol === "ETH"),
    sol: findQ("CRYPTO:SOL") || pools.find((q) => q.symbol === "SOL"),
    xrp: findQ("CRYPTO:XRP") || pools.find((q) => q.symbol === "XRP"),
    bnb: findQ("CRYPTO:BNB") || pools.find((q) => q.symbol === "BNB"),
    nifty: findQ("NSE:NIFTY50"),
    gold: findQ("MCX:GOLD"),
    silver: findQ("MCX:SILVER"),
    crude: findQ("MCX:CRUDE"),
    natgas: findQ("MCX:NATGAS"),
    copper: findQ("MCX:COPPER"),
    aluminium: findQ("MCX:ALUMINIUM"),
    zinc: findQ("MCX:ZINC"),
    sensex: findQ("BSE:SENSEX"),
    banknifty: findQ("NSE:BANKNIFTY"),
    finnifty: findQ("NSE:FINNIFTY"),
    bankex: findQ("BSE:BANKEX"),
    vix: findQ("NSE:INDIAVIX"),
  };
  const prefixes = ["home", ...CHART_GROUPS.map((g) => g.id)];
  CHART_SPECS.forEach((c) => {
    const q = quoteFor[c.id];
    prefixes.forEach((prefix) => {
      const head = document.getElementById("head-" + prefix + "-" + c.id);
      const st = document.getElementById("stats-" + prefix + "-" + c.id);
      if (!head) return;
      if (q) {
        head.innerHTML = `${money(q)} ${chg(q.change_pct)}`;
        if (st) st.innerHTML = stats(q, [["High", fmt(q.high)], ["Low", fmt(q.low)], ["Volume", fmt(q.volume, 0)], ["Prev", fmt(q.prev_close)]]);
      }
    });
  });

  document.getElementById("corrHome").innerHTML = (d.correlations || []).map((c) => `
    <div class="corr-item ${c.kind}">
      <b>${c.kind === "forward" ? "FUTURE EVENT" : "LIVE TAPE"} · ${c.driver}</b>
      <div class="text-secondary">${c.driver_move || ""}</div>
      <div>${c.reason}</div>
      ${c.alt ? `<div class="text-secondary">${c.alt}</div>` : ""}
      <div>${(c.expected || []).map((e) => `<span class="expect-pill ${e.direction}">${e.asset} ${e.direction}</span>`).join("")}</div>
    </div>`).join("") || `<div class="text-secondary">No cross-asset rule is firing right now. Upcoming macro events still list a playbook below when scheduled.</div>`;
  document.getElementById("seasonNotes").textContent = (d.season_notes || []).join(" · ");
  const board = document.getElementById("impactBoard");
  if (board) {
    board.innerHTML = (d.impact_board || []).map(impactBox).join("") || `<div class="text-secondary">No mapped impact yet. War, CPI, jobs, FII/DII and large moves will appear here.</div>`;
  }

  document.getElementById("globalHome").innerHTML = rowBlock(d.global_markets);
  document.getElementById("cryptoHome").innerHTML = rowBlock(d.crypto.filter((c) => ["BTC", "ETH", "SOL", "XRP", "BNB"].includes(c.symbol)));
  document.getElementById("mcxHome").innerHTML = rowBlock(d.mcx);
  document.getElementById("watchHome").innerHTML = rowBlock(d.watchlist);

  document.getElementById("briefing").innerHTML = (d.briefing || []).map(briefRow).join("") || `<div class="text-secondary">Calendar feed loading…</div>`;

  document.getElementById("newsHome").innerHTML = (d.news && d.news.length ? d.news.slice(0, 8) : [{title:"No live headlines yet", source:"—", age:"", market:""}]).map((n, i) => `
    <button type="button" class="news-item news-hit" data-news="${i}">${newsThumb(n)}<div><b>${escHtml(n.title)}</b><div class="text-secondary">${escHtml(n.source)} · ${escHtml(n.age)}</div></div><span class="tag">${escHtml(n.market || "")}</span></button>`).join("");

  const liveEl = document.getElementById("liveState");
  const stamp = new Date(d.generated_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Asia/Kolkata" });
  liveEl.innerHTML = `<i></i> ${d.live ? "Live tape" : "Delayed"} · ${stamp} IST`;

  renderSentiment(d);
  renderPages(d);
}

async function load() {
  const res = await fetch("/api/dashboard");
  const data = await res.json();
  render(data);
}

document.getElementById("nav").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-page]");
  if (btn) showPage(btn.dataset.page);
});
document.body.addEventListener("click", (e) => {
  const jump = e.target.closest("[data-page-jump]");
  if (jump) showPage(jump.dataset.pageJump);
  const why = e.target.closest("[data-why]");
  if (why && state.data) {
    e.preventDefault();
    e.stopPropagation();
    const id = why.getAttribute("data-why");
    const alert = (state.data.alerts || []).find((a) => a.id === id);
    if (alert) openWhy(alert);
  }
  const newsHit = e.target.closest("[data-news]");
  if (newsHit && state.data) {
    e.preventDefault();
    const idx = Number(newsHit.getAttribute("data-news"));
    openNews((state.data.news || [])[idx]);
  }
});
document.getElementById("modalClose").onclick = () => document.getElementById("modal").classList.remove("show");
document.getElementById("modal").onclick = (e) => { if (e.target.id === "modal") e.target.classList.remove("show"); };

async function loadFO() {
  const root = document.getElementById("foRoot");
  if (!root) return;
  if (!root.dataset.loaded) {
    root.innerHTML = `<div class="card"><p class="text-secondary mb-0">Loading option chain from Dhan. Index + cash underlyings, about 3 seconds apart…</p></div>`;
  }
  try {
    const data = await (await fetch("/api/fo")).json();
    const card = (x) => {
      if (!x.ok) {
        return `<div class="card"><h3>${x.name || "Underlying"}</h3><p class="text-secondary mb-0">${x.error || "Chain unavailable"}</p></div>`;
      }
      const pcrCls = x.pcr == null ? "" : x.pcr >= 1 ? "up" : "down";
      const top = (x.top || []).map((r) => `<div class="rowline"><span>${fmt(r.strike, 0)}</span><span>CE OI ${fmt(r.call_oi, 0)}</span><span>PE OI ${fmt(r.put_oi, 0)}</span></div>`).join("");
      return `<div class="card">
        <div class="card-head"><h3>${x.name}</h3><span class="sub">${x.kind} · ${x.expiry}</span></div>
        <div class="kpi">Spot ${x.spot == null ? "—" : fmt(x.spot)} · PCR <span class="${pcrCls}">${x.pcr ?? "—"}</span> · ATM IV ${x.atm_iv ?? "—"}</div>
        <div class="rowline"><span>Call OI</span><b>${fmt(x.call_oi, 0)}</b></div>
        <div class="rowline"><span>Put OI</span><b>${fmt(x.put_oi, 0)}</b></div>
        <div class="rowline"><span>Max call OI strike</span><b>${x.max_call}</b></div>
        <div class="rowline"><span>Max put OI strike</span><b>${x.max_put}</b></div>
        <div class="text-secondary mt-2">Heaviest strikes</div>
        ${top || `<p class="text-secondary">No strike OI in this expiry.</p>`}
      </div>`;
    };
    const poi = (data.participants || [])[0];
    const poiHtml = poi ? `<div class="card mt-3"><div class="card-head"><h3>Participant-wise OI</h3><span class="sub">NSE file · ${poi.as_of}</span></div>
      <table class="table"><thead><tr><th>Client</th><th>Idx fut long</th><th>Idx fut short</th><th>Idx call long</th><th>Idx put long</th><th>Stk fut long</th><th>Stk fut short</th></tr></thead>
      <tbody>${poi.rows.map((r) => `<tr><td>${r.client}</td><td>${r.fut_idx_long}</td><td>${r.fut_idx_short}</td><td>${r.opt_idx_call_long}</td><td>${r.opt_idx_put_long}</td><td>${r.fut_stk_long}</td><td>${r.fut_stk_short}</td></tr>`).join("")}</tbody></table>
      <a href="${poi.url}" target="_blank" rel="noopener">NSE source file</a></div>` : `<div class="card mt-3"><h3>Participant-wise OI</h3><p class="text-secondary mb-0">NSE has not published today's participant file yet (or the archive was blocked). This is not estimated.</p></div>`;
    root.innerHTML = `
      ${data.error ? `<div class="card mb-3"><p class="text-secondary mb-0">${data.error}</p></div>` : ""}
      <h3 class="chart-cat-head">Index options</h3>
      <div class="grid-4b">${(data.index || []).map(card).join("")}</div>
      <h3 class="chart-cat-head mt-3">Cash stock options</h3>
      <div class="grid-4b">${(data.cash || []).map(card).join("")}</div>
      ${poiHtml}
      <p class="text-secondary mt-2">${data.source ? `Chain: ${data.source}` : ""}</p>`;
    root.dataset.loaded = "1";
  } catch (err) {
    root.innerHTML = `<div class="card"><p class="no-dot mb-0">Could not load F&amp;O: ${err}</p></div>`;
  }
}

bindFolds();
mountChartGrid(
  "homeCharts",
  HOME_CHART_IDS.map((id) => CHART_SPECS.find((c) => c.id === id)).filter(Boolean),
  "home"
);
clock();
setInterval(clock, 1000);
load();
connectLive();

function connectLive() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/live`);
  ws.onmessage = (ev) => {
    try { render(JSON.parse(ev.data)); } catch (e) { /* ignore */ }
  };
  ws.onerror = () => ws.close();
  ws.onclose = () => setTimeout(connectLive, 4000);
}
