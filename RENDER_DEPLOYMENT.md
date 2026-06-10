# Deploy del webhook Telegram su Render

Questa guida attiva risposte quasi immediate al comando Telegram `/segnale`
usando il servizio FastAPI definito in `telegram_webhook.py`.

## Stato del deploy

Configurazione completata e verificata il 9 giugno 2026.

```text
Servizio: https://btc-prudential-signal.onrender.com
Webhook:  https://btc-prudential-signal.onrender.com/webhook
Stato:    Live
```

Verifiche completate:

- health check con risposta `{"status":"ok"}`;
- `getWebhookInfo` con URL corretto e nessun update pendente;
- comando `/segnale` con risposta immediata.

## Prima del deploy

Servono:

- un account GitHub con accesso a `giuse2003/BTC_Prudential_Signal`;
- un account gratuito su Render;
- `TELEGRAM_BOT_TOKEN`;
- `TELEGRAM_CHAT_ID`;
- `SUPABASE_URL`;
- `SUPABASE_SERVICE_ROLE_KEY`;
- una stringa segreta scelta dall'utente, ad esempio
  `btc_signal_webhook_2026`.

La stringa usata per `TELEGRAM_WEBHOOK_SECRET` deve contenere soltanto lettere,
numeri, trattino o underscore.

## Creazione del servizio Render

1. Apri <https://render.com/> e crea un account.
2. Collega il tuo account GitHub.
3. Nel Dashboard Render seleziona **New > Web Service**.
4. Seleziona il repository `BTC_Prudential_Signal`.
5. Scegli il piano **Free**.
6. Imposta:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn telegram_webhook:app --host 0.0.0.0 --port $PORT
```

Il file `render.yaml` contiene gia questi valori e puo essere usato anche come
Blueprint.

7. Aggiungi le variabili d'ambiente:

```text
TELEGRAM_BOT_TOKEN=<token BotFather>
TELEGRAM_CHAT_ID=<id numerico della chat>
TELEGRAM_WEBHOOK_SECRET=btc_signal_webhook_2026
SUPABASE_URL=<project URL Supabase>
SUPABASE_SERVICE_ROLE_KEY=<service role secret Supabase>
```

8. Avvia il deploy.
9. Quando lo stato diventa **Live**, copia l'URL HTTPS assegnato da Render,
   per esempio:

```text
https://btc-prudential-signal.onrender.com
```

10. Apri l'URL nel browser. Deve rispondere:

```json
{"status":"ok"}
```

## Registrazione del webhook Telegram

Sostituisci:

- `<TELEGRAM_BOT_TOKEN>` con il token reale;
- `<RENDER_URL>` con l'URL Render senza slash finale;
- `<WEBHOOK_SECRET>` con lo stesso valore configurato su Render.

### Registra

```bash
curl --request POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  --header "Content-Type: application/json" \
  --data '{"url":"<RENDER_URL>/webhook","secret_token":"<WEBHOOK_SECRET>","allowed_updates":["message"],"drop_pending_updates":true}'
```

### Verifica

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

Controlla che:

- `url` termini con `/webhook`;
- `pending_update_count` non continui a crescere;
- `last_error_message` sia assente.

### Rimuovi

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/deleteWebhook"
```

Per eliminare anche gli update rimasti in attesa:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/deleteWebhook?drop_pending_updates=true"
```

## Prova

Nella chat autorizzata scrivi:

```text
/segnale
```

Il webhook:

1. riceve l'update Telegram;
2. restituisce rapidamente HTTP 200;
3. scarica
   `https://raw.githubusercontent.com/giuse2003/BTC_Prudential_Signal/main/docs/status.json`;
4. risponde con segnale, rischio, prezzo EUR e indicazione.

Sono supportati anche `/start` e `/help`.

Con Supabase configurato sono supportati anche:

```text
/iscrivimi
/disiscrivimi
/privacy
```

Non inserire mai `SUPABASE_SERVICE_ROLE_KEY` nel repository o nella dashboard
pubblica. Deve esistere soltanto tra le variabili protette di Render.

## Listener GitHub Actions

Telegram non consente di usare contemporaneamente un webhook e `getUpdates`.
Quando il webhook e attivo, disabilita il workflow
`Telegram command listener` nella sezione GitHub Actions.

Per tornare temporaneamente al listener:

1. esegui `deleteWebhook`;
2. riabilita il workflow GitHub Actions.

Il monitor `Hourly BTC monitor (Telegram)` deve invece rimanere attivo: continua
ad aggiornare `docs/status.json` e a inviare le notifiche automatiche.

## Limite del piano gratuito Render

Render spegne un Web Service gratuito dopo 15 minuti senza traffico in
ingresso. La riattivazione alla prima richiesta richiede circa un minuto.

Quindi:

- servizio gia attivo: risposta normalmente in circa 1-3 secondi;
- servizio addormentato: la prima risposta puo richiedere circa un minuto;
- richieste successive: tornano quasi immediate finche il servizio resta
  attivo.

## Test locali

Installa le dipendenze:

```powershell
python -m pip install -r requirements.txt
```

Avvia FastAPI:

```powershell
$env:TELEGRAM_BOT_TOKEN="token-di-test"
$env:TELEGRAM_CHAT_ID="123456"
$env:TELEGRAM_WEBHOOK_SECRET="test-secret"
uvicorn telegram_webhook:app --host 127.0.0.1 --port 8000
```

Verifica l'health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
```

Esegui i test:

```powershell
python -m unittest discover -s tests -v
```
