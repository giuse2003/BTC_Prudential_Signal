const STATUS_ENDPOINT = "./live-status.json";
const CHART_DATA_ENDPOINT = "./chart-data.json";
const COINBASE_EUR_ENDPOINT = "https://api.coinbase.com/v2/prices/BTC-EUR/spot";
const COINBASE_USD_ENDPOINT = "https://api.coinbase.com/v2/prices/BTC-USD/spot";
const COINBASE_CANDLES_ENDPOINT =
  "https://api.exchange.coinbase.com/products/BTC-USD/candles";
const SUBSCRIBER_COUNT_ENDPOINT =
  "https://btc-prudential-signal.giuse2003.workers.dev/subscribers/count";
const CHART_HISTORY_REFRESH_MS = 10 * 60 * 1000;

const els = {
  signalVal: document.getElementById("signalVal"),
  signalHint: document.getElementById("signalHint"),
  signalCard: document.getElementById("signalCard"),
  riskVal: document.getElementById("riskVal"),
  riskHint: document.getElementById("riskHint"),
  riskCard: document.getElementById("riskCard"),
  priceUSD: document.getElementById("priceUSD"),
  priceUSDHint: document.getElementById("priceUSDHint"),
  priceEUR: document.getElementById("priceEUR"),
  priceEURHint: document.getElementById("priceEURHint"),
  lastUpdate: document.getElementById("lastUpdate"),
  monitorStatus: document.getElementById("monitorStatus"),
  refreshSelect: document.getElementById("refreshSelect"),
  statusText: document.getElementById("statusText"),
  statusDot: document.querySelector("#status .dot"),
  corsHelper: document.getElementById("corsHelper"),
  subscriberCount: document.getElementById("subscriberCount"),
  buyConditions: document.getElementById("buyConditions"),
  sellConditions: document.getElementById("sellConditions"),
  btcTrendChart: document.getElementById("btcTrendChart"),
  chartLoading: document.getElementById("chartLoading"),
  chartNote: document.getElementById("chartNote"),
  chartRanges: Array.from(document.querySelectorAll(".chart-range")),
  
  // Technical details
  rsiVal: document.getElementById("rsiVal"),
  sma50Val: document.getElementById("sma50Val"),
  sma200Val: document.getElementById("sma200Val"),
  atrVal: document.getElementById("atrVal"),
};

let botData = null;
let intervalId = null;
let inFlight = false;
let officialChartRows = [];
let chartRows = [];
let chartRange = "180";
let lastChartHistoryFetchAt = 0;
let liveCandleSource = null;

// Custom currency formatting for Italian locale
function formatCurrency(value, currency) {
  try {
    return new Intl.NumberFormat("it-IT", {
      style: "currency",
      currency: currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
}

function setStatus(state, text) {
  els.statusDot.classList.remove("ok", "err", "loading");
  if (state) els.statusDot.classList.add(state);
  els.statusText.textContent = text;
}

// Check if running on local file:// protocol
const isLocalFile = window.location.protocol === "file:";

async function loadSubscriberCount() {
  if (!els.subscriberCount) return;

  try {
    const response = await fetch(SUBSCRIBER_COUNT_ENDPOINT, {
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const payload = await response.json();
    if (!Number.isInteger(payload.active_subscribers)) {
      throw new Error("Risposta non valida");
    }
    els.subscriberCount.textContent =
      `Iscritti attivi: ${payload.active_subscribers}`;
  } catch (error) {
    console.warn("Conteggio iscritti non disponibile:", error.message);
    els.subscriberCount.textContent = "Iscritti attivi: non disponibile";
  }
}

async function loadBotStatus() {
  try {
    const res = await fetch(STATUS_ENDPOINT, { cache: "no-store" });
    if (!res.ok) throw new Error("File di stato non configurato");
    
    botData = await res.ok ? await res.json() : null;
    if (botData) {
      updateBotUI(botData);
      if (els.corsHelper) els.corsHelper.style.display = "none";
    }
  } catch (err) {
    console.warn("Impossibile caricare lo status.json del bot:", err.message);
    if (isLocalFile && els.corsHelper) {
      els.corsHelper.style.display = "block";
    }
    setStatus("err", "Dati bot non ancora disponibili.");
  }
}

function updateBotUI(data) {
  // Update operational signal card
  const signal = data.signal || "MANTIENI";
  els.signalVal.textContent = signal;
  els.signalCard.className = "metric highlight-card"; // reset classes
  
  const isSellSignal = signal.toUpperCase().startsWith("VENDI");

  if (signal === "ACQUISTA") {
    els.signalCard.classList.add("signal-buy");
    els.signalHint.textContent = "Allineamento tecnico favorevole.";
  } else if (isSellSignal) {
    els.signalCard.classList.add("signal-sell");
    els.signalHint.textContent = "Uscita protettiva attiva secondo le regole.";
  } else {
    els.signalCard.classList.add("signal-hold");
    els.signalHint.textContent = "Nessuna nuova operazione secondo il metodo.";
  }

  // Update risk level card
  const risk = data.risk_level || "MEDIO";
  els.riskVal.textContent = risk;
  els.riskCard.className = "ind-box"; // reset classes
  
  if (risk === "BASSO") {
    els.riskCard.classList.add("risk-low");
    els.riskHint.textContent = "Mercato solido, bassa volatilità.";
  } else if (risk === "ALTO") {
    els.riskCard.classList.add("risk-high");
    els.riskHint.textContent = "Trend negativo o mercato surriscaldato.";
  } else {
    els.riskCard.classList.add("risk-medium");
    els.riskHint.textContent = "Zona neutrale di consolidamento.";
  }

  // Update technical details
  els.rsiVal.textContent = data.rsi ? data.rsi.toFixed(2) : "N/D";
  els.sma50Val.textContent = data.sma50 ? formatCurrency(data.sma50, "USD") : "N/D";
  els.sma200Val.textContent = data.sma200 ? formatCurrency(data.sma200, "USD") : "N/D";
  els.atrVal.textContent = data.atr ? data.atr.toFixed(2) : "N/D";
  updateConditionList(els.buyConditions, data.condition_groups?.buy);
  updateConditionList(els.sellConditions, data.condition_groups?.sell);

  // Last update time
  els.lastUpdate.textContent = data.last_update || "N/D";
  els.monitorStatus.textContent = data.status || "Attivo";
  els.monitorStatus.className = "info-val monitor-active";
}

function updateConditionList(listEl, conditions) {
  if (!listEl || !Array.isArray(conditions)) return;

  listEl.innerHTML = "";
  conditions.forEach((condition) => {
    const item = document.createElement("li");
    item.className = condition.passed ? "passed" : "failed";

    const flag = document.createElement("span");
    flag.className = "condition-flag";
    flag.textContent = condition.passed ? "✓" : "0";

    const text = document.createElement("span");
    text.textContent = condition.label;

    item.append(flag, text);
    listEl.appendChild(item);
  });
}

async function loadChartData() {
  if (!els.btcTrendChart) return;

  try {
    const response = await fetch(CHART_DATA_ENDPOINT, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = await response.json();
    if (!Array.isArray(rows)) throw new Error("Formato grafico non valido");

    officialChartRows = rows
      .map((row) => ({
        date: row.date,
        open: nullableNumber(row.open) ?? Number(row.close),
        high: nullableNumber(row.high) ?? Number(row.close),
        low: nullableNumber(row.low) ?? Number(row.close),
        close: Number(row.close),
        sma50: nullableNumber(row.sma50),
        sma200: nullableNumber(row.sma200),
        rsi: nullableNumber(row.rsi),
        volume: nullableNumber(row.volume),
        volumeAvg20: nullableNumber(row.volume_avg20),
        provisional: false,
      }))
      .filter((row) =>
        row.date && [row.open, row.high, row.low, row.close].every(Number.isFinite)
      );

    chartRows = [...officialChartRows];
    lastChartHistoryFetchAt = Date.now();
    drawTrendChart();
  } catch (error) {
    console.warn("Grafico storico non disponibile:", error.message);
    if (els.chartLoading) {
      els.chartLoading.textContent = "Grafico non disponibile.";
      els.chartLoading.style.display = "grid";
    }
  }
}

function utcDateKey(date) {
  return date.toISOString().slice(0, 10);
}

async function fetchRecentCoinbaseCandles() {
  const end = new Date();
  const start = new Date(end.getTime() - 3 * 24 * 60 * 60 * 1000);
  const params = new URLSearchParams({
    granularity: "86400",
    start: start.toISOString(),
    end: end.toISOString(),
  });
  const response = await fetch(`${COINBASE_CANDLES_ENDPOINT}?${params}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Coinbase candles HTTP ${response.status}`);

  const payload = await response.json();
  if (!Array.isArray(payload)) throw new Error("Formato candele Coinbase non valido");

  return payload
    .filter((candle) => Array.isArray(candle) && candle.length >= 6)
    .map(([time, low, high, open, close]) => ({
      date: utcDateKey(new Date(Number(time) * 1000)),
      open: Number(open),
      high: Number(high),
      low: Number(low),
      close: Number(close),
      sma50: null,
      sma200: null,
      rsi: null,
      volume: null,
      volumeAvg20: null,
      provisional: true,
    }))
    .filter((row) => [row.open, row.high, row.low, row.close].every(Number.isFinite))
    .sort((a, b) => a.date.localeCompare(b.date));
}

async function refreshLiveChartCandles() {
  if (!officialChartRows.length) return;

  const latestOfficialDate = officialChartRows[officialChartRows.length - 1].date;
  const provisionalRows = (await fetchRecentCoinbaseCandles()).filter(
    (row) => row.date > latestOfficialDate
  );
  chartRows = [...officialChartRows, ...provisionalRows];
  liveCandleSource = provisionalRows.length ? "coinbase" : null;
  drawTrendChart();
}

function updateLiveChartWithSpot(priceUSD) {
  if (!officialChartRows.length || !Number.isFinite(priceUSD)) return;

  const today = utcDateKey(new Date());
  const existing = chartRows.find((row) => row.provisional && row.date === today);
  const previous = chartRows.filter((row) => row.date < today).at(-1);
  const open = existing?.open ?? previous?.close ?? priceUSD;
  const liveRow = {
    date: today,
    open,
    high: Math.max(existing?.high ?? open, priceUSD),
    low: Math.min(existing?.low ?? open, priceUSD),
    close: priceUSD,
    sma50: null,
    sma200: null,
    rsi: null,
    volume: null,
    volumeAvg20: null,
    provisional: true,
  };
  chartRows = [...chartRows.filter((row) => row.date !== today), liveRow]
    .sort((a, b) => a.date.localeCompare(b.date));
  liveCandleSource = "spot";
  drawTrendChart();
}

function nullableNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function getVisibleChartRows() {
  if (chartRange === "all") return chartRows;
  const count = Number(chartRange);
  return chartRows.slice(Math.max(0, chartRows.length - count));
}

function drawTrendChart() {
  const canvas = els.btcTrendChart;
  if (!canvas || !chartRows.length) return;

  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(320, Math.floor(rect.width || canvas.clientWidth || 1040));
  const height = Math.max(520, Math.floor(width * 0.66));
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const rows = getVisibleChartRows();
  const padding = { top: 18, right: 18, bottom: 34, left: 72 };
  const gap = 22;
  const chartWidth = width - padding.left - padding.right;
  const availableHeight = height - padding.top - padding.bottom - gap * 2;
  const priceHeight = Math.round(availableHeight * 0.58);
  const rsiHeight = Math.round(availableHeight * 0.2);
  const volumeHeight = availableHeight - priceHeight - rsiHeight;
  const pricePanel = { top: padding.top, height: priceHeight };
  const rsiPanel = { top: pricePanel.top + pricePanel.height + gap, height: rsiHeight };
  const volumePanel = { top: rsiPanel.top + rsiPanel.height + gap, height: volumeHeight };

  const xFor = (index) =>
    padding.left + ((index + 0.5) / Math.max(1, rows.length)) * chartWidth;

  const priceValues = rows
    .flatMap((row) => [row.low, row.high, row.sma50, row.sma200])
    .filter(Number.isFinite);
  const minValue = Math.min(...priceValues);
  const maxValue = Math.max(...priceValues);
  const priceRange = maxValue - minValue || 1;
  const priceMin = minValue - priceRange * 0.08;
  const priceMax = maxValue + priceRange * 0.08;
  const priceYFor = (value) =>
    pricePanel.top + ((priceMax - value) / (priceMax - priceMin)) * pricePanel.height;

  const rsiYFor = (value) =>
    rsiPanel.top + ((80 - value) / 60) * rsiPanel.height;

  const volumeValues = rows.flatMap((row) => [row.volume, row.volumeAvg20]).filter(Number.isFinite);
  const volumeMax = Math.max(...volumeValues, 1);
  const volumeYFor = (value) =>
    volumePanel.top + (1 - value / volumeMax) * volumePanel.height;

  drawCompositeGrid(ctx, rows, xFor, width, height, padding, {
    pricePanel,
    rsiPanel,
    volumePanel,
    priceYFor,
    rsiYFor,
    volumeYFor,
    priceMin,
    priceMax,
    volumeMax,
  });
  const candleWidth = Math.max(1, Math.min(10, (chartWidth / rows.length) * 0.68));
  drawCandlesticks(ctx, rows, xFor, priceYFor, candleWidth);
  drawLine(ctx, rows, "sma50", xFor, priceYFor, "#38bdf8", 1.8);
  drawLine(ctx, rows, "sma200", xFor, priceYFor, "#22c55e", 1.8);
  drawLine(ctx, rows, "rsi", xFor, rsiYFor, "#f7931a", 1.8);
  drawVolumeBars(ctx, rows, xFor, volumeYFor, volumePanel, candleWidth);
  drawLine(ctx, rows, "volumeAvg20", xFor, volumeYFor, "#38bdf8", 1.8);

  const first = rows[0];
  const last = rows[rows.length - 1];
  if (els.chartLoading) els.chartLoading.style.display = "none";
  if (els.chartNote) {
    const liveNote = last.provisional
      ? ` Candela UTC in corso da Coinbase (${liveCandleSource === "spot" ? "fallback spot" : "OHLC"}), ancora provvisoria.`
      : "";
    els.chartNote.textContent =
      `Periodo mostrato: ${formatDateShort(first.date)} - ${formatDateShort(last.date)}. ` +
      `Ultimo prezzo BTC-USD: ${formatCurrency(last.close, "USD")}.${liveNote}`;
  }
}

function drawCandlesticks(ctx, rows, xFor, yFor, candleWidth) {
  rows.forEach((row, index) => {
    if (![row.open, row.high, row.low, row.close].every(Number.isFinite)) return;

    const rising = row.close >= row.open;
    const color = rising ? "#22c55e" : "#ef5b66";
    const x = xFor(index);
    const openY = yFor(row.open);
    const closeY = yFor(row.close);
    const highY = yFor(row.high);
    const lowY = yFor(row.low);
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(1, Math.abs(closeY - openY));

    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle = row.provisional ? "rgba(0,0,0,0.18)" : color;
    ctx.lineWidth = row.provisional ? 1.4 : 1;
    if (row.provisional) ctx.setLineDash([3, 2]);
    ctx.beginPath();
    ctx.moveTo(x, highY);
    ctx.lineTo(x, lowY);
    ctx.stroke();
    ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
    if (row.provisional) {
      ctx.strokeRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
    }
    ctx.restore();
  });
}

function drawVolumeBars(ctx, rows, xFor, yFor, panel, candleWidth) {
  rows.forEach((row, index) => {
    if (!Number.isFinite(row.volume)) return;
    const rising = row.close >= row.open;
    const y = yFor(row.volume);
    ctx.fillStyle = rising ? "rgba(34,197,94,0.36)" : "rgba(239,91,102,0.36)";
    ctx.fillRect(
      xFor(index) - candleWidth / 2,
      y,
      candleWidth,
      Math.max(1, panel.top + panel.height - y)
    );
  });
}

function drawCompositeGrid(ctx, rows, xFor, width, height, padding, scale) {
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.08)";
  ctx.fillStyle = "rgba(248,250,252,0.68)";
  ctx.lineWidth = 1;
  ctx.font = "12px Outfit, sans-serif";

  for (let i = 0; i <= 4; i += 1) {
    const value = scale.priceMin + ((scale.priceMax - scale.priceMin) / 4) * i;
    const y = scale.priceYFor(value);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(compactUsd(value), 8, y + 4);
  }

  [40, 70].forEach((level) => {
    const y = scale.rsiYFor(level);
    const isSignalThreshold = level === 40;
    ctx.save();
    if (isSignalThreshold) {
      ctx.strokeStyle = "rgba(14,165,233,0.95)";
      ctx.lineWidth = 2;
      ctx.fillStyle = "rgba(125,211,252,0.98)";
    }
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(isSignalThreshold ? "RSI 40" : String(level), isSignalThreshold ? 16 : 26, y + 4);
    ctx.restore();
  });

  [0.5, 1].forEach((part) => {
    const value = scale.volumeMax * part;
    const y = scale.volumeYFor(value);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(compactUsd(value), 8, y + 4);
  });

  drawPanelLabel(ctx, "Prezzo / SMA", padding.left, scale.pricePanel.top);
  drawPanelLabel(ctx, "RSI(14)", padding.left, scale.rsiPanel.top);
  drawPanelLabel(ctx, "Volume", padding.left, scale.volumePanel.top);

  const tickCount = Math.min(5, rows.length);
  for (let i = 0; i < tickCount; i += 1) {
    const index = Math.round((rows.length - 1) * (i / Math.max(1, tickCount - 1)));
    const x = xFor(index);
    ctx.fillText(formatDateShort(rows[index].date), x - 24, height - 10);
  }
  ctx.restore();
}

function drawPanelLabel(ctx, label, x, y) {
  ctx.save();
  ctx.fillStyle = "rgba(248,250,252,0.78)";
  ctx.font = "700 12px Outfit, sans-serif";
  ctx.fillText(label, x, y + 13);
  ctx.restore();
}

function drawLine(ctx, rows, key, xFor, yFor, color, width) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.beginPath();
  let started = false;

  rows.forEach((row, index) => {
    const value = row[key];
    if (!Number.isFinite(value)) {
      started = false;
      return;
    }
    const x = xFor(index);
    const y = yFor(value);
    if (!started) {
      ctx.moveTo(x, y);
      started = true;
    } else {
      ctx.lineTo(x, y);
    }
  });

  ctx.stroke();
  ctx.restore();
}

function compactUsd(value) {
  return new Intl.NumberFormat("it-IT", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatDateShort(value) {
  const date = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat("it-IT", {
    month: "short",
    year: "2-digit",
  }).format(date);
}

async function fetchLiveCoinbasePrice(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const payload = await res.json();
  return Number(payload?.data?.amount);
}

async function tick() {
  if (inFlight) return;
  inFlight = true;
  setStatus("loading", "Aggiornamento in corso...");

  try {
    // 1. Carica prima lo stato del bot locale
    await loadBotStatus();

    if (Date.now() - lastChartHistoryFetchAt >= CHART_HISTORY_REFRESH_MS) {
      await loadChartData();
    }

    // 2. Recupera i prezzi live in tempo reale da Coinbase
    const [priceEUR, priceUSD] = await Promise.all([
      fetchLiveCoinbasePrice(COINBASE_EUR_ENDPOINT),
      fetchLiveCoinbasePrice(COINBASE_USD_ENDPOINT),
    ]);

    try {
      await refreshLiveChartCandles();
    } catch (chartError) {
      console.warn("Candela Coinbase non disponibile:", chartError.message);
      updateLiveChartWithSpot(priceUSD);
    }

    // Aggiorna prezzi in USD
    els.priceUSD.textContent = formatCurrency(priceUSD, "USD");
    if (botData && botData.price_usd) {
      els.priceUSDHint.textContent = formatCurrency(botData.price_usd, "USD");
    } else {
      els.priceUSDHint.textContent = "Non disponibile";
    }

    // Aggiorna prezzi in EUR
    els.priceEUR.textContent = formatCurrency(priceEUR, "EUR");
    if (botData && botData.price_eur) {
      els.priceEURHint.textContent = formatCurrency(botData.price_eur, "EUR");
    } else {
      els.priceEURHint.textContent = "Non disponibile";
    }

    setStatus("ok", "Connesso live");
  } catch (e) {
    console.error(e);
    setStatus("err", `Errore connessione: ${e.message}`);
    
    // Fallback: se coinbase fallisce ma abbiamo i dati del bot, mostriamo quelli del bot
    if (botData) {
      if (botData.price_usd) els.priceUSD.textContent = formatCurrency(botData.price_usd, "USD");
      if (botData.price_eur) els.priceEUR.textContent = formatCurrency(botData.price_eur, "EUR");
      setStatus("ok", "Visualizzazione dati salvati");
    }
  } finally {
    inFlight = false;
  }
}

function start() {
  const ms = Number(els.refreshSelect.value);
  if (intervalId) window.clearInterval(intervalId);
  intervalId = window.setInterval(tick, ms);
}

els.refreshSelect.addEventListener("change", () => {
  start();
  tick();
});

els.chartRanges.forEach((button) => {
  button.addEventListener("click", () => {
    chartRange = button.dataset.range || "180";
    els.chartRanges.forEach((item) => item.classList.toggle("active", item === button));
    drawTrendChart();
  });
});

window.addEventListener("resize", () => {
  window.requestAnimationFrame(drawTrendChart);
});

async function bootstrap() {
  await loadChartData();
  await tick();
  start();
}

// Avvio
loadSubscriberCount();
bootstrap();
