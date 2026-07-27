const HELP_MESSAGE = [
  "BTC-USD SIGNAL",
  "",
  "/segnale - mostra l'azione LIVE PREVIEW corrente",
  "/conditions - mostra le condizioni di acquisto e vendita",
  "/iscrivimi - ricevi notifiche quando varia una condizione LIVE",
  "/disiscrivimi - interrompi le notifiche automatiche",
  "/privacy - informazioni sui dati memorizzati",
].join("\n");

const CONDITIONS_MESSAGE = [
  "CONDIZIONI BTC-USD SIGNAL",
  "",
  "ACQUISTA richiede tutte le condizioni:",
  "1. prezzo sopra SMA200;",
  "2. RSI uguale o maggiore di 40;",
  "3. prezzo sopra quello di 7 giorni prima;",
  "4. volume BTC-USD sopra media 20 giorni.",
  "",
  "VENDI ha precedenza e richiede:",
  "1. prezzo sotto SMA50 per 2 giorni consecutivi.",
  "",
  "Negli altri casi: MANTIENI STATO ATTUALE.",
].join("\n");

const PRIVACY_MESSAGE = [
  "PRIVACY",
  "",
  "Per gestire le notifiche vengono memorizzati identificativo Telegram, nome pubblico e stato dell'iscrizione.",
  "Il numero di cellulare non viene richiesto o memorizzato.",
  "Puoi revocare il consenso in qualsiasi momento con /disiscrivimi.",
].join("\n");

const SUBSCRIBED_MESSAGE = "Iscrizione attiva.\n\nRiceverai un messaggio soltanto quando varia una delle 5 condizioni LIVE.\nPuoi annullare con /disiscrivimi.";
const UNSUBSCRIBED_MESSAGE = "Iscrizione disattivata. Non riceverai nuovi segnali.";
const NOT_SUBSCRIBED_MESSAGE = "Non risulta alcuna iscrizione da disattivare.";
const STATUS_ERROR_MESSAGE = "Impossibile recuperare BTC-USD Signal. Riprova tra poco.";
const SUBSCRIPTION_ERROR_MESSAGE = "Non riesco ad aggiornare l'iscrizione in questo momento. Riprova tra poco.";

const CORS_ORIGINS = new Set([
  "https://giuse2003.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
]);

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { headers: corsHeaders(request) });
    if (request.method === "GET" && url.pathname === "/") {
      return json({ status: "ok", project: "BTC-USD Signal" });
    }
    if (request.method === "GET" && url.pathname === "/subscribers/count") {
      return handleSubscriberCount(env, request);
    }
    if (request.method === "GET" && url.pathname === "/live-preview") {
      try {
        return json({ message: await buildLiveSignalMessage(env) }, 200, corsHeaders(request));
      } catch (error) {
        console.error("LIVE PREVIEW non disponibile.", error);
        return json({ detail: "LIVE PREVIEW non disponibile." }, 502, corsHeaders(request));
      }
    }
    if (request.method === "POST" && url.pathname === "/webhook") {
      return handleTelegramWebhook(request, env, ctx);
    }
    return json({ detail: "Not found" }, 404);
  },
};

async function handleSubscriberCount(env, request) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return json({ detail: "Servizio iscritti non configurato." }, 503, corsHeaders(request));
  }
  try {
    return json({ active_subscribers: await countActiveSubscribers(env) }, 200, corsHeaders(request));
  } catch (error) {
    console.error("Conteggio iscritti non riuscito.", error);
    return json({ detail: "Conteggio temporaneamente non disponibile." }, 502, corsHeaders(request));
  }
}

async function handleTelegramWebhook(request, env, ctx) {
  if (!env.TELEGRAM_BOT_TOKEN) return json({ detail: "Configurazione Telegram mancante." }, 503);
  const expectedSecret = (env.TELEGRAM_WEBHOOK_SECRET || "").trim();
  if (expectedSecret && request.headers.get("x-telegram-bot-api-secret-token") !== expectedSecret) {
    return json({ detail: "Webhook secret non valido." }, 403);
  }
  let update;
  try {
    update = await request.json();
  } catch {
    return json({ detail: "Payload JSON non valido." }, 400);
  }
  const command = extractCommand(update);
  if (command) ctx.waitUntil(processCommand(command, env));
  return json({ ok: true });
}

function extractCommand(update) {
  const message = update?.message;
  const chat = message?.chat;
  if (!chat || (chat.type && chat.type !== "private") || !Number.isInteger(chat.id)) return null;
  if (typeof message.text !== "string" || !message.text.trim().startsWith("/")) return null;
  const sender = message.from && typeof message.from === "object" ? message.from : {};
  const parts = message.text.trim().split(/\s+/, 2);
  let command = parts[0].split("@", 1)[0].toLowerCase();
  if (command === "/start" && parts[1] === "iscrivimi") command = "/iscrivimi";
  return {
    command,
    chatId: chat.id,
    userId: Number.isInteger(sender.id) ? sender.id : null,
    username: optionalText(sender.username),
    firstName: optionalText(sender.first_name),
    languageCode: optionalText(sender.language_code),
  };
}

function optionalText(value) {
  return typeof value === "string" && value ? value : null;
}

async function processCommand(request, env) {
  let message;
  if (request.command === "/segnale") {
    try {
      message = await buildLiveSignalMessage(env);
    } catch (error) {
      console.error("Azione LIVE non disponibile.", error);
      message = STATUS_ERROR_MESSAGE;
    }
  } else if (request.command === "/conditions") message = CONDITIONS_MESSAGE;
  else if (request.command === "/start" || request.command === "/help") message = HELP_MESSAGE;
  else if (request.command === "/privacy") message = PRIVACY_MESSAGE;
  else if (request.command === "/iscrivimi") message = await subscribeUser(request, env);
  else if (request.command === "/disiscrivimi") message = await unsubscribeUser(request.chatId, env);
  else message = "Comando non riconosciuto.\nUsa /help";
  await sendTelegramMessage(env, request.chatId, message);
}

function publishedUrl(env, filename) {
  const statusUrl = env.STATUS_JSON_URL ||
    "https://raw.githubusercontent.com/giuse2003/BTC_Prudential_Signal/main/docs/status.json";
  return statusUrl.replace(/\/status\.json(\?.*)?$/, `/${filename}`);
}

async function fetchPublishedJson(env, filename) {
  const url = publishedUrl(env, filename);
  const separator = url.includes("?") ? "&" : "?";
  const response = await fetch(`${url}${separator}t=${Date.now()}`, {
    headers: { Accept: "application/json", "Cache-Control": "no-cache" },
  });
  if (!response.ok) throw new Error(`${filename} HTTP ${response.status}`);
  const payload = await response.json();
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error(`${filename} non valido.`);
  }
  return payload;
}

async function buildLiveSignalMessage(env) {
  const [live, manifest] = await Promise.all([
    fetchPublishedJson(env, "live-status.json"),
    fetchPublishedJson(env, "manifest.json"),
  ]);
  if (!live.run_id || live.run_id !== manifest.run_id) {
    throw new Error("Pacchetto pubblicato con run_id non coerente.");
  }
  return formatMonitorMessage(
    String(live.action || "MANTIENI STATO ATTUALE"),
    Number(live.price_eur),
    live.condition_groups,
  );
}

function formatMonitorMessage(action, priceEur, conditionGroups) {
  const price = Number.isFinite(priceEur)
    ? `${Math.trunc(priceEur).toLocaleString("it-IT")} EUR`
    : "BTC-EUR non disponibile";
  return [
    "BTC-USD Signal - LIVE PREVIEW",
    "",
    `Azione: ${action}`,
    "",
    `Prezzo informativo: ${price}`,
    "",
    "(per le regole: /conditions)",
    "",
    ...formatSignalConditions(conditionGroups),
  ].join("\n");
}

function formatSignalConditions(groups) {
  if (!groups || !Array.isArray(groups.buy) || !Array.isArray(groups.sell)) {
    return ["Condizioni non disponibili."];
  }
  return [
    "ACQUISTA:",
    ...formatConditionGroup(groups.buy),
    "",
    "VENDI:",
    ...formatConditionGroup(groups.sell),
  ];
}

function formatConditionGroup(conditions) {
  return conditions.map((condition, index) => `${condition.passed ? "OK" : "NO"} ${index + 1}.`);
}

async function subscribeUser(request, env) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) return SUBSCRIPTION_ERROR_MESSAGE;
  try {
    const now = new Date().toISOString();
    await supabaseFetch(env, "/telegram_subscribers?on_conflict=telegram_chat_id", {
      method: "POST",
      headers: { Prefer: "resolution=merge-duplicates,return=minimal" },
      body: JSON.stringify({
        telegram_chat_id: request.chatId,
        telegram_user_id: request.userId,
        telegram_username: request.username,
        telegram_first_name: request.firstName,
        telegram_language_code: request.languageCode,
        active: true,
        subscribed_at: now,
        unsubscribed_at: null,
        consent_version: "v1",
        consent_source: "telegram_command",
        delivery_failures: 0,
        last_delivery_error: null,
        last_delivery_error_at: null,
      }),
    });
    return SUBSCRIBED_MESSAGE;
  } catch (error) {
    console.error("Iscrizione non riuscita.", error);
    return SUBSCRIPTION_ERROR_MESSAGE;
  }
}

async function unsubscribeUser(chatId, env) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) return SUBSCRIPTION_ERROR_MESSAGE;
  try {
    const response = await supabaseFetch(
      env,
      `/telegram_subscribers?telegram_chat_id=eq.${chatId}&select=telegram_chat_id`,
      {
        method: "PATCH",
        headers: { Prefer: "return=representation" },
        body: JSON.stringify({ active: false, unsubscribed_at: new Date().toISOString() }),
      },
    );
    const result = await response.json();
    return Array.isArray(result) && result.length ? UNSUBSCRIBED_MESSAGE : NOT_SUBSCRIBED_MESSAGE;
  } catch (error) {
    console.error("Disiscrizione non riuscita.", error);
    return SUBSCRIPTION_ERROR_MESSAGE;
  }
}

async function countActiveSubscribers(env) {
  const response = await supabaseFetch(
    env,
    "/telegram_subscribers?active=eq.true&select=telegram_chat_id",
    { method: "GET", headers: { Prefer: "count=exact", Range: "0-0" } },
  );
  const total = (response.headers.get("Content-Range") || "").split("/").pop();
  if (!total || !/^\d+$/.test(total)) throw new Error("Conteggio Supabase non valido.");
  return Number(total);
}

async function supabaseFetch(env, path, init = {}) {
  const response = await fetch(`${env.SUPABASE_URL.replace(/\/$/, "")}/rest/v1${path}`, {
    ...init,
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!response.ok) throw new Error(`Supabase HTTP ${response.status}: ${await response.text()}`);
  return response;
}

async function sendTelegramMessage(env, chatId, text) {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
  });
  if (!response.ok) throw new Error(`Telegram HTTP ${response.status}: ${await response.text()}`);
}

function json(payload, status = 200, headers = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...headers },
  });
}

function corsHeaders(request) {
  const origin = request.headers.get("Origin");
  if (!origin || !CORS_ORIGINS.has(origin)) return {};
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Accept, Content-Type",
    Vary: "Origin",
  };
}
