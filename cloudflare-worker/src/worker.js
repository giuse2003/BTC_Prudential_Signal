const HELP_MESSAGE = [
  "BTC PRUDENTIAL SIGNAL",
  "",
  "/segnale - mostra il segnale BTC corrente",
  "/conditions - mostra le condizioni di acquisto e vendita",
  "/iscrivimi - ricevi notifiche quando cambia segnale o rischio",
  "/disiscrivimi - interrompi le notifiche automatiche",
  "/privacy - informazioni sui dati memorizzati",
].join("\n");
const CONDITIONS_MESSAGE = [
  "CONDIZIONI BTC MONITOR",
  "",
  "Per ACQUISTA devono essere vere tutte queste condizioni:",
  "1. prezzo sopra SMA200;",
  "2. SMA50 sopra SMA200;",
  "3. RSI uguale o maggiore di 40;",
  "4. prezzo sopra quello di 7 giorni prima;",
  "5. volume sopra media 20 giorni.",
  "",
  "Per VENDI deve essere vera questa condizione:",
  "1. prezzo sotto SMA50 per 2 giorni consecutivi.",
].join("\n");
const PRIVACY_MESSAGE = [
  "PRIVACY",
  "",
  "Per gestire le notifiche vengono memorizzati il tuo identificativo Telegram, il nome pubblico e lo stato dell'iscrizione.",
  "Il numero di cellulare non viene richiesto o memorizzato.",
  "Puoi revocare il consenso in qualsiasi momento con /disiscrivimi.",
].join("\n");

const SUBSCRIBED_MESSAGE = [
  "Iscrizione attiva.",
  "",
  "Riceverai un messaggio soltanto quando cambia il segnale BTC o il livello di rischio.",
  "Puoi annullare l'iscrizione con /disiscrivimi.",
].join("\n");

const STATUS_ERROR_MESSAGE =
  "Impossibile recuperare il segnale BTC aggiornato. Riprova tra poco.";
const SUBSCRIPTION_ERROR_MESSAGE =
  "Non riesco ad aggiornare l'iscrizione in questo momento. Riprova tra poco.";
const UNSUBSCRIBED_MESSAGE = "Iscrizione disattivata. Non riceverai nuovi segnali.";
const NOT_SUBSCRIBED_MESSAGE = "Non risulta alcuna iscrizione da disattivare.";

const CORS_ORIGINS = new Set([
  "https://giuse2003.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
]);

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(request) });
    }

    if (request.method === "GET" && url.pathname === "/") {
      return json({ status: "ok" });
    }

    if (request.method === "GET" && url.pathname === "/subscribers/count") {
      return handleSubscriberCount(env, request);
    }

    if (request.method === "POST" && url.pathname === "/webhook") {
      return handleTelegramWebhook(request, env, ctx);
    }

    return json({ detail: "Not found" }, 404);
  },
};

async function handleSubscriberCount(env, request) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return json(
      { detail: "Servizio iscritti non configurato." },
      503,
      corsHeaders(request),
    );
  }

  try {
    const activeSubscribers = await countActiveSubscribers(env);
    return json(
      { active_subscribers: activeSubscribers },
      200,
      corsHeaders(request),
    );
  } catch (error) {
    console.error("Conteggio iscritti non riuscito.", error);
    return json(
      { detail: "Conteggio iscritti temporaneamente non disponibile." },
      502,
      corsHeaders(request),
    );
  }
}

async function handleTelegramWebhook(request, env, ctx) {
  if (!env.TELEGRAM_BOT_TOKEN) {
    return json({ detail: "Configurazione Telegram mancante." }, 503);
  }

  const expectedSecret = (env.TELEGRAM_WEBHOOK_SECRET || "").trim();
  if (
    expectedSecret &&
    request.headers.get("x-telegram-bot-api-secret-token") !== expectedSecret
  ) {
    return json({ detail: "Webhook secret non valido." }, 403);
  }

  let update;
  try {
    update = await request.json();
  } catch {
    return json({ detail: "Payload JSON non valido." }, 400);
  }

  const command = extractCommand(update);
  if (command) {
    ctx.waitUntil(processCommand(command, env));
  }

  return json({ ok: true });
}

function extractCommand(update) {
  const message = update?.message;
  if (!message || typeof message !== "object") return null;

  const chat = message.chat;
  if (!chat || typeof chat !== "object") return null;
  if (chat.type && chat.type !== "private") return null;
  if (!Number.isInteger(chat.id)) return null;

  const text = message.text;
  if (typeof text !== "string" || !text.trim().startsWith("/")) return null;

  const sender = message.from && typeof message.from === "object" ? message.from : {};
  const parts = text.trim().split(/\s+/, 2);
  let command = parts[0].split("@", 1)[0].toLowerCase();
  if (command === "/start" && parts[1] === "iscrivimi") {
    command = "/iscrivimi";
  }

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
      message = buildSignalMessage(await fetchGithubStatus(env));
    } catch (error) {
      console.error("Impossibile recuperare status.json.", error);
      message = STATUS_ERROR_MESSAGE;
    }
  } else if (request.command === "/conditions") {
    message = CONDITIONS_MESSAGE;
  } else if (request.command === "/start" || request.command === "/help") {
    message = HELP_MESSAGE;
  } else if (request.command === "/privacy") {
    message = PRIVACY_MESSAGE;
  } else if (request.command === "/iscrivimi") {
    message = await subscribeUser(request, env);
  } else if (request.command === "/disiscrivimi") {
    message = await unsubscribeUser(request.chatId, env);
  } else {
    message = "Comando non riconosciuto.\nUsa /help";
  }

  await sendTelegramMessage(env, request.chatId, message);
}

async function fetchGithubStatus(env) {
  const statusUrl =
    env.STATUS_JSON_URL ||
    "https://raw.githubusercontent.com/giuse2003/BTC_Prudential_Signal/main/docs/status.json";
  const separator = statusUrl.includes("?") ? "&" : "?";
  const response = await fetch(`${statusUrl}${separator}t=${Date.now()}`, {
    headers: {
      Accept: "application/json",
      "Cache-Control": "no-cache",
    },
  });
  if (!response.ok) {
    throw new Error(`GitHub status HTTP ${response.status}`);
  }
  const status = await response.json();
  if (!status || typeof status !== "object" || Array.isArray(status)) {
    throw new Error("status.json non contiene un oggetto JSON.");
  }
  return status;
}

function buildSignalMessage(status) {
  const signal = String(status.signal || "MANTIENI");
  const priceEur =
    status.price_eur === null || status.price_eur === undefined
      ? null
      : Number(status.price_eur);

  return formatMonitorMessage(
    signal,
    priceEur,
    status.condition_groups || deriveConditionGroups(status),
  );
}

function formatMonitorMessage(signal, priceEur, conditionGroups) {
  const priceText =
    Number.isFinite(priceEur) && priceEur !== null
      ? `${Math.trunc(priceEur).toLocaleString("it-IT")} EUR`
      : "BTC-EUR non disponibile";

  return [
    "BTC MONITOR",
    "",
    `Segnale: ${signal}`,
    "",
    "Prezzo:",
    priceText,
    "",
    "(per le condizioni: /conditions)",
    "",
    ...formatSignalConditions(conditionGroups),
  ].join("\n");
}

function formatSignalConditions(conditionGroups) {
  if (!conditionGroups || !Array.isArray(conditionGroups.buy) || !Array.isArray(conditionGroups.sell)) {
    return [
      "Condizioni:",
      "non disponibili nello status corrente. Attendi il prossimo aggiornamento del monitor.",
    ];
  }

  return [
    "ACQUISTA:",
    ...formatConditionGroup(conditionGroups.buy),
    "",
    "VENDI:",
    ...formatConditionGroup(conditionGroups.sell),
  ];
}

function deriveConditionGroups(status) {
  const close = Number(status.close_last_candle ?? status.price_usd);
  const sma50 = Number(status.sma50);
  const sma200 = Number(status.sma200);
  const rsi = Number(status.rsi);
  const volume = Number(status.volume);
  const volumeAvg20 = Number(status.volume_avg20);
  const close7dAgo = Number(status.close_7d_ago);
  const previousClose = Number(status.previous_close);
  const previousSma50 = Number(status.previous_sma50);

  if (
    ![
      close,
      sma50,
      sma200,
      rsi,
      volume,
      volumeAvg20,
      close7dAgo,
    ].every(Number.isFinite)
  ) {
    return null;
  }

  return {
    buy: [
      { label: "prezzo sopra SMA200", passed: close > sma200 },
      { label: "SMA50 sopra SMA200", passed: sma50 > sma200 },
      { label: "RSI uguale o maggiore di 40", passed: rsi >= 40 },
      {
        label: "prezzo sopra quello di 7 giorni prima",
        passed: close > close7dAgo,
      },
      { label: "volume sopra media 20 giorni", passed: volume > volumeAvg20 },
    ],
    sell: [
      {
        label: "prezzo sotto SMA50 per 2 giorni consecutivi",
        passed:
          typeof status.below_sma50_2d === "boolean"
            ? status.below_sma50_2d
            :
          close < sma50 &&
          Number.isFinite(previousClose) &&
          Number.isFinite(previousSma50) &&
          previousClose < previousSma50,
      },
    ],
  };
}

function formatConditionGroup(conditions) {
  return conditions.map((condition, index) => {
    const marker = condition.passed ? "✅" : "🅾️";
    return `${marker} ${index + 1}.`;
  });
}
async function subscribeUser(request, env) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return SUBSCRIPTION_ERROR_MESSAGE;
  }

  try {
    const now = new Date().toISOString();
    await supabaseFetch(env, "/telegram_subscribers?on_conflict=telegram_chat_id", {
      method: "POST",
      headers: {
        Prefer: "resolution=merge-duplicates,return=minimal",
      },
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
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return SUBSCRIPTION_ERROR_MESSAGE;
  }

  try {
    const response = await supabaseFetch(
      env,
      `/telegram_subscribers?telegram_chat_id=eq.${chatId}&select=telegram_chat_id`,
      {
        method: "PATCH",
        headers: {
          Prefer: "return=representation",
        },
        body: JSON.stringify({
          active: false,
          unsubscribed_at: new Date().toISOString(),
        }),
      },
    );
    const result = await response.json();
    return Array.isArray(result) && result.length
      ? UNSUBSCRIBED_MESSAGE
      : NOT_SUBSCRIBED_MESSAGE;
  } catch (error) {
    console.error("Disiscrizione non riuscita.", error);
    return SUBSCRIPTION_ERROR_MESSAGE;
  }
}

async function countActiveSubscribers(env) {
  const response = await supabaseFetch(
    env,
    "/telegram_subscribers?active=eq.true&select=telegram_chat_id",
    {
      method: "GET",
      headers: {
        Prefer: "count=exact",
        Range: "0-0",
      },
    },
  );
  const contentRange = response.headers.get("Content-Range") || "";
  const total = contentRange.split("/").pop();
  if (!total || !/^\d+$/.test(total)) {
    throw new Error("Conteggio Supabase non valido.");
  }
  return Number(total);
}

async function supabaseFetch(env, path, init = {}) {
  const url = `${env.SUPABASE_URL.replace(/\/$/, "")}/rest/v1${path}`;
  const response = await fetch(url, {
    ...init,
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!response.ok) {
    throw new Error(`Supabase HTTP ${response.status}: ${await response.text()}`);
  }
  return response;
}

async function sendTelegramMessage(env, chatId, text) {
  const response = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: chatId,
        text,
        disable_web_page_preview: true,
      }),
    },
  );
  if (!response.ok) {
    throw new Error(`Telegram HTTP ${response.status}: ${await response.text()}`);
  }
}

function json(payload, status = 200, headers = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...headers,
    },
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


