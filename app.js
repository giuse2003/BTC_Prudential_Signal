const STATUS_ENDPOINT = "./reports/status.json";
const COINBASE_EUR_ENDPOINT = "https://api.coinbase.com/v2/prices/BTC-EUR/spot";
const COINBASE_USD_ENDPOINT = "https://api.coinbase.com/v2/prices/BTC-USD/spot";
const SUBSCRIBER_COUNT_ENDPOINT =
  "https://btc-prudential-signal.onrender.com/subscribers/count";

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
  
  // Technical details
  rsiVal: document.getElementById("rsiVal"),
  sma50Val: document.getElementById("sma50Val"),
  sma200Val: document.getElementById("sma200Val"),
  atrVal: document.getElementById("atrVal"),
};

let botData = null;
let intervalId = null;
let inFlight = false;

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
    setStatus("err", "Dati bot non collegati. Esegui run_dashboard.py");
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
    els.signalHint.textContent = "Rilevata forte debolezza. Ridurre rischio.";
  } else {
    els.signalCard.classList.add("signal-hold");
    els.signalHint.textContent = "Nessuna operazione. Mantieni posizioni.";
  }

  // Update risk level card
  const risk = data.risk_level || "MEDIO";
  els.riskVal.textContent = risk;
  els.riskCard.className = "metric highlight-card"; // reset classes
  
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

  // Last update time
  els.lastUpdate.textContent = data.last_update || "N/D";
  els.monitorStatus.textContent = data.status || "Attivo";
  els.monitorStatus.className = "info-val monitor-active";
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

    // 2. Recupera i prezzi live in tempo reale da Coinbase
    const priceEUR = await fetchLiveCoinbasePrice(COINBASE_EUR_ENDPOINT);
    const priceUSD = await fetchLiveCoinbasePrice(COINBASE_USD_ENDPOINT);

    // Aggiorna prezzi in USD
    els.priceUSD.textContent = formatCurrency(priceUSD, "USD");
    if (botData && botData.price_usd) {
      els.priceUSDHint.innerHTML = `Live Spot (Bot run: <b>${formatCurrency(botData.price_usd, "USD")}</b>)`;
    } else {
      els.priceUSDHint.textContent = "Prezzo live spot Coinbase";
    }

    // Aggiorna prezzi in EUR
    els.priceEUR.textContent = formatCurrency(priceEUR, "EUR");
    if (botData && botData.price_eur) {
      els.priceEURHint.innerHTML = `Live Spot (Bot run: <b>${formatCurrency(botData.price_eur, "EUR")}</b>)`;
    } else {
      els.priceEURHint.textContent = "Prezzo live spot Coinbase";
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

// Avvio
start();
tick();
loadSubscriberCount();
