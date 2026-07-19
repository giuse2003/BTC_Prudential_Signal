# Cloudflare Worker Deployment

Cloudflare Worker e il backend pubblico del progetto per i comandi Telegram e
il conteggio aggregato degli iscritti.

## Endpoint

- `POST /webhook`: riceve gli update Telegram.
- `GET /`: health check.
- `GET /subscribers/count`: conteggio pubblico aggregato per la dashboard.

Restano invariati:

- GitHub Actions per aggiornare `docs/status.json`.
- GitHub Pages per la dashboard.
- Supabase per salvare gli iscritti Telegram.

## Secret richiesti

Nel Worker configura questi secret:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

`STATUS_JSON_URL` e gia definito in `cloudflare-worker/wrangler.toml`.

## Deploy

Da questa cartella:

```powershell
cd D:\GitHub\BTC_Prudential_Signal\cloudflare-worker
npx wrangler login
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put SUPABASE_URL
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
npx wrangler deploy
```

Il deploy restituisce un URL simile a:

```text
https://btc-prudential-signal.<account>.workers.dev
```

## Collegare Telegram

Sostituisci `<WORKER_URL>` e `<SECRET>`:

```powershell
$botToken = "<TELEGRAM_BOT_TOKEN>"
$secret = "<SECRET>"
$workerUrl = "<WORKER_URL>"
Invoke-RestMethod `
  -Method Post `
  -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -ContentType "application/json" `
  -Body (@{
    url = "$workerUrl/webhook"
    secret_token = $secret
    allowed_updates = @("message")
  } | ConvertTo-Json)
```

Verifica:

```powershell
Invoke-RestMethod "$workerUrl/"
Invoke-RestMethod "$workerUrl/subscribers/count"
```

Poi scrivi al bot:

```text
/segnale
/iscrivimi
/disiscrivimi
```

## Aggiornare la dashboard

La dashboard deve usare in `app.js` e `docs/app.js`:

```js
const SUBSCRIBER_COUNT_ENDPOINT =
  "https://btc-prudential-signal.giuse2003.workers.dev/subscribers/count";
```
