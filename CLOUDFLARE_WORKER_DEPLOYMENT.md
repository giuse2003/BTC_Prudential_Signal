# Cloudflare Worker

Il Worker espone webhook Telegram, conteggio iscritti e `/live-preview`. Non
scarica candele e non ricalcola indicatori: legge `live-status.json` e
`manifest.json` dal ramo `main`, verificando che il `run_id` coincida.

L'identificatore tecnico del servizio resta `btc-prudential-signal` per non
interrompere URL e webhook esistenti; il nome pubblico e **BTC-USD Signal**.

## Configurazione

Le variabili pubbliche sono in `wrangler.jsonc`. I segreti devono essere caricati
con Wrangler e non committati:

```powershell
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put SUPABASE_URL
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
```

Verifica e deploy:

```powershell
npx wrangler deploy --dry-run
npx wrangler deploy
```

Endpoint corrente:
`https://btc-prudential-signal.giuse2003.workers.dev`
