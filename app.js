const PRICE_ENDPOINT = "https://api.coinbase.com/v2/prices/BTC-EUR/spot";

const els = {
  price: document.getElementById("price"),
  time: document.getElementById("time"),
  refreshSelect: document.getElementById("refreshSelect"),
  historyBody: document.getElementById("historyBody"),
  clearHistory: document.getElementById("clearHistory"),
  statusText: document.getElementById("statusText"),
  statusDot: document.querySelector("#status .dot"),
};

const HISTORY_KEY = "btc_eur_history_v1";
const HISTORY_MAX = 50;

function formatEUR(value) {
  try {
    return new Intl.NumberFormat("it-IT", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${value.toFixed(2)} €`;
  }
}

function formatTime(d) {
  return new Intl.DateTimeFormat("it-IT", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(d);
}

function setStatus(state, text) {
  els.statusDot.classList.remove("ok", "err", "loading");
  if (state) els.statusDot.classList.add(state);
  els.statusText.textContent = text;
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((x) => x && typeof x.t === "number" && typeof x.p === "number")
      .slice(0, HISTORY_MAX);
  } catch {
    return [];
  }
}

function saveHistory(items) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, HISTORY_MAX)));
  } catch {
    // ignore quota / privacy mode
  }
}

function renderHistory(items) {
  els.historyBody.innerHTML = "";
  if (items.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 2;
    td.textContent = "Nessun dato ancora. Attendi un aggiornamento.";
    td.style.color = "rgba(255,255,255,.7)";
    tr.appendChild(td);
    els.historyBody.appendChild(tr);
    return;
  }

  for (const it of items) {
    const tr = document.createElement("tr");

    const tdT = document.createElement("td");
    tdT.className = "mono";
    tdT.textContent = formatTime(new Date(it.t));

    const tdP = document.createElement("td");
    tdP.className = "right";
    tdP.textContent = formatEUR(it.p);

    tr.appendChild(tdT);
    tr.appendChild(tdP);
    els.historyBody.appendChild(tr);
  }
}

async function fetchSpotPriceEUR() {
  const res = await fetch(PRICE_ENDPOINT, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const data = await res.json();
  const amount = Number(data?.data?.amount);
  if (!Number.isFinite(amount)) {
    throw new Error("Risposta non valida");
  }
  return amount;
}

let intervalId = null;
let inFlight = false;

async function tick() {
  if (inFlight) return;
  inFlight = true;
  setStatus("loading", "Aggiornamento in corso…");

  try {
    const price = await fetchSpotPriceEUR();
    const now = new Date();
    els.price.textContent = formatEUR(price);
    els.time.textContent = formatTime(now);

    const history = loadHistory();
    history.unshift({ t: now.getTime(), p: price });
    saveHistory(history);
    renderHistory(history);

    setStatus("ok", "Online");
  } catch (e) {
    setStatus("err", `Errore: ${e?.message ?? "impossibile aggiornare"}`);
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

els.clearHistory.addEventListener("click", () => {
  saveHistory([]);
  renderHistory([]);
});

renderHistory(loadHistory());
start();
tick();

