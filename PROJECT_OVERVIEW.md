# BTC Signal Guard - Documento di progetto

Ultimo aggiornamento: 2026-06-19

Questo documento descrive l'intero progetto BTC Signal Guard: cosa fa,
come genera i segnali Bitcoin, quali dati usa per backtest e monitoraggio,
quali servizi esterni integra e come un altro agente IA puo replicarlo,
testarlo e modificarlo.

Il progetto ha finalita informativa e di monitoraggio tecnico. Non costituisce
consulenza finanziaria.

## Obiettivo

BTC Signal Guard monitora Bitcoin con dati giornalieri e produce tre
segnali:

- `ACQUISTA`: le condizioni tecniche di ingresso sono tutte vere.
- `MANTIENI`: non ci sono condizioni sufficienti per acquistare o vendere.
- `VENDI`: il prezzo ha chiuso sotto SMA50 per due giorni consecutivi.

Il sistema pubblica lo stato su una dashboard GitHub Pages e risponde via bot
Telegram ai comandi manuali. Il webhook Telegram e servito da Cloudflare
Worker per evitare il cold start del vecchio servizio Render.

## Regole della strategia

La strategia usa solo candele giornaliere chiuse. La candela UTC del giorno
corrente viene esclusa, per evitare segnali basati su dati parziali.

### Condizioni di acquisto

Per generare `ACQUISTA` devono essere vere tutte queste condizioni:

1. prezzo `Close` sopra `SMA200`;
2. `RSI(14)` uguale o maggiore di `40`;
3. prezzo `Close` sopra quello di 7 giorni prima;
4. volume giornaliero sopra la media dei volumi a 20 giorni.

Nel codice queste regole sono in `strategy/signals.py`, funzione
`compute_strict_signal`.

### Condizione di vendita

Per generare `VENDI` deve essere vera questa condizione:

1. prezzo `Close` sotto `SMA50` per due giorni consecutivi.

Questa regola ha sostituito le vecchie 5 condizioni di vendita perche, nei
backtest, riduceva molto il drawdown e aumentava il rendimento rispetto alla
vendita tardiva basata su condizioni ribassiste piu lente.

### Mantieni

Se non scatta ne `ACQUISTA` ne `VENDI`, il segnale e `MANTIENI`.

Nel backtest, `MANTIENI` significa: conserva l'esposizione precedente.

## Indicatori calcolati

Gli indicatori sono calcolati in `indicators/technical_indicators.py`.

Indicatori principali:

- `SMA50`: media mobile semplice a 50 giorni.
- `SMA200`: media mobile semplice a 200 giorni.
- `RSI(14)`: Relative Strength Index con media Wilder-like.
- `VolumeAvg20`: volume medio a 20 giorni.
- `ATR(14)`: Average True Range.
- `High52w` e `Low52w`: massimo e minimo degli ultimi 365 giorni.
- `Close_7d_ago`: prezzo di chiusura di 7 giorni prima.

Bitcoin viene trattato come mercato aperto 7 giorni su 7:

- periodi annui per statistiche: `365`;
- finestra 52 settimane: `365` giorni;
- dati giornalieri: `interval="1d"`.

## Punteggio tecnico e rischio

Il progetto calcola anche un punteggio tecnico e un livello di rischio, ma il
segnale operativo e deciso dalle condizioni strette sopra descritte.

Il punteggio informativo aggiunge componenti per:

- prezzo sopra SMA200;
- SMA50 sopra SMA200;
- RSI;
- volume sopra media;
- distanza dalla SMA200.

Nota: `SMA50 sopra SMA200` resta una componente del punteggio informativo, ma
non e piu una condizione operativa obbligatoria per `ACQUISTA`.

Il rischio informativo puo essere:

- `BASSO`;
- `MEDIO`;
- `ALTO`.

Il rischio diventa `ALTO` se, ad esempio, prezzo e SMA50 sono sotto SMA200,
oppure RSI eccessivamente alto, oppure distanza dalla SMA200 superiore al 40%.

## Dati usati

### Dati storici per segnali e backtest

Fonte: Yahoo Finance tramite libreria `yfinance`.

Simboli:

- `BTC-USD`: serie principale per segnali e backtest;
- `BTC-EUR`: serie storica EUR usata come supporto per report/prezzi in euro.

File locali generati:

- `data/BTC-USD_daily.csv`;
- `data/BTC-EUR_daily.csv`.

Il download e il caricamento sono gestiti da `data/fetch_yahoo.py`.

Il filtro delle sole candele giornaliere chiuse e in
`data/daily_candles.py`, funzione `keep_closed_daily_candles`.

### Prezzi spot live

Fonte: Coinbase endpoint pubblico:

```text
GET https://api.coinbase.com/v2/prices/<PAIR>/spot
```

Coppie usate:

- `BTC-USD`;
- `BTC-EUR`.

Il codice e in `live/coinbase.py`.

I prezzi spot live servono per mostrare un prezzo aggiornato nel report e nel
bot Telegram, ma i segnali tecnici continuano a usare l'ultima candela
giornaliera chiusa.

## Backtest

Il motore di backtest e in `backtest/backtest.py`.

Regole di esposizione:

- `ACQUISTA` -> esposizione 100%;
- `MANTIENI` -> conserva esposizione precedente;
- `VENDI` -> esposizione 0%.

Per evitare look-ahead bias:

- il segnale calcolato alla chiusura del giorno `t` viene applicato ai
  rendimenti del giorno successivo;
- nel codice questo avviene con `desired_exposure.shift(1)`.

Metriche calcolate:

- rendimento totale;
- rendimento annualizzato;
- drawdown massimo;
- operazioni completate;
- win rate;
- Sharpe ratio annualizzato su 365 giorni.

Una operazione e considerata completata solo quando una posizione long viene
aperta e poi chiusa. Una posizione ancora aperta a fine serie non entra nel
conteggio operazioni ne nel win rate.

Il backtest non include:

- commissioni;
- spread;
- slippage;
- imposte;
- limiti di liquidita.

### Risultato backtest della strategia corrente

Con dati storici dal 2015 fino all'ultima candela chiusa disponibile nel run
locale del 2026-06-19:

```text
Strategia corrente
Rendimento totale:        +42.475,12%
Rendimento annualizzato:  +69,55%
Drawdown massimo:         -42,06%
Operazioni completate:    35
Win rate:                 51,4%
Sharpe Ratio:             1,451

Buy & Hold
Rendimento totale:        +20.399,17%
Rendimento annualizzato:  +59,08%
Drawdown massimo:         -83,40%
Sharpe Ratio:             1,033
```

Questi numeri sono prodotti da `python main.py` e scritti in
`reports/report.txt`.

## Output generati

Eseguendo:

```powershell
python main.py --force-download
```

vengono generati:

- `reports/report.txt`: report testuale completo;
- `reports/historical_signals.csv`: storico indicatori e segnali;
- `reports/equity_timeseries.csv`: equity line strategia vs Buy & Hold;
- `reports/price_sma_signals.png`: grafico prezzo/SMA/segnali;
- `reports/status.json`: stato corrente per dashboard e bot.

Per pubblicare lo stato nella dashboard GitHub Pages, `reports/status.json`
viene copiato in:

```text
docs/status.json
```

## Dashboard web

La dashboard pubblica e servita da GitHub Pages dalla cartella `docs/`.

URL:

```text
https://giuse2003.github.io/BTC_Prudential_Signal/
```

File principali:

- `docs/index.html`;
- `docs/app.js`;
- `docs/style.css`;
- `docs/status.json`.

La dashboard mostra:

- segnale corrente;
- prezzo BTC;
- indicatori principali;
- conteggio aggregato degli iscritti Telegram.

Il conteggio iscritti viene letto dal Worker Cloudflare:

```text
GET https://btc-prudential-signal.giuse2003.workers.dev/subscribers/count
```

La risposta contiene solo:

```json
{"active_subscribers": 2}
```

Non espone token, chat ID o dati personali.

## Telegram bot

Il bot Telegram e gestito da Cloudflare Worker.

Worker:

```text
https://btc-prudential-signal.giuse2003.workers.dev
```

File:

```text
cloudflare-worker/src/worker.js
cloudflare-worker/wrangler.toml
```

Endpoint Worker:

- `GET /`: health check;
- `GET /subscribers/count`: conteggio iscritti attivi;
- `POST /webhook`: webhook Telegram.

### Comandi Telegram

Il bot supporta:

- `/segnale`: mostra segnale corrente, prezzo, stato sintetico delle condizioni;
- `/conditions`: mostra il testo completo delle condizioni di acquisto/vendita;
- `/iscrivimi`: registra l'utente per notifiche automatiche future;
- `/disiscrivimi`: disattiva l'iscrizione;
- `/privacy`: spiega quali dati vengono salvati;
- `/help`: lista dei comandi.

I comandi manuali rispondono solo alla chat privata dell'utente che li invia.
Non vengono inviati a tutti gli iscritti.

### Messaggio `/segnale`

Il messaggio e volutamente compatto:

```text
BTC Signal Guard

Segnale: VENDI

Prezzo:
55.115 EUR

(per le condizioni: /conditions)

ACQUISTA:
🅾️ 1.
🅾️ 2.
🅾️ 3.
✅ 4.
🅾️ 5.

VENDI:
✅ 1.
```

I numeri fanno riferimento alle condizioni elencate in `/conditions`.

### Menu comandi Telegram

Il menu Telegram viene aggiornato dal workflow GitHub Actions:

```text
.github/workflows/telegram-command.yml
```

Il workflow si chiama `Telegram command menu` e va lanciato manualmente con
`workflow_dispatch`. Aggiorna Telegram tramite `setMyCommands`.

## Supabase

Supabase salva gli iscritti Telegram.

Il progetto Supabase e condiviso con il progetto Ethereum ed e stato rinominato
`crypto-prudential-signal` per non legarlo nominalmente solo a Bitcoin.
La separazione operativa avviene tramite tabelle dedicate:

```text
BTC: public.telegram_subscribers
ETH: public.telegram_subscribers_eth
```

I due bot e i due Worker restano separati. Possono condividere lo stesso
`SUPABASE_URL` e la stessa `SUPABASE_SERVICE_ROLE_KEY`, ma ogni progetto deve
leggere e scrivere esclusivamente la propria tabella.

Schema:

```text
supabase/telegram_subscribers.sql
```

Tabella:

```text
public.telegram_subscribers
```

Campi principali:

- `telegram_chat_id`: chiave primaria, destinatario Telegram;
- `telegram_user_id`;
- `telegram_username`;
- `telegram_first_name`;
- `telegram_language_code`;
- `active`;
- `subscribed_at`;
- `unsubscribed_at`;
- `consent_version`;
- `consent_source`;
- campi di diagnostica delivery.

La tabella ha Row Level Security attiva e forzata. I ruoli `anon` e
`authenticated` non hanno accesso; il Worker usa `service_role`.

La presenza della tabella `public.telegram_subscribers_eth` nello stesso
progetto Supabase e prevista e appartiene al repository
`ETH_Prudential_Signal`.

## GitHub Actions

### Hourly BTC monitor

Workflow:

```text
.github/workflows/hourly-monitor.yml
```

Trigger:

- ogni ora (`cron: "0 * * * *"`);
- manuale (`workflow_dispatch`).

Funzioni:

1. scarica dati aggiornati;
2. esclude la candela giornaliera UTC in corso;
3. calcola indicatori e segnale;
4. genera `reports/status.json`;
5. copia lo stato in `docs/status.json`;
6. committa e pusha l'aggiornamento della dashboard;
7. invia una notifica Telegram solo se cambia il segnale o cambia almeno una
   condizione operativa mostrata nel messaggio;
8. salva lo stato in cache `.state`.

Nota: al momento le notifiche automatiche del monitor usano il secret
`TELEGRAM_CHAT_ID`, quindi sono legate a un destinatario configurato in
GitHub Actions. Gli iscritti Supabase sono gestiti dal bot, ma il broadcast
automatico a tutti gli iscritti non e ancora implementato.

### Telegram command menu

Workflow:

```text
.github/workflows/telegram-command.yml
```

Serve solo ad aggiornare il menu dei comandi Telegram. Non ascolta piu i
comandi: quelli sono gestiti dal Worker Cloudflare.

## Servizi esterni usati

### GitHub

Usato per:

- repository del codice;
- GitHub Actions;
- GitHub Pages;
- Raw URL pubblico di `docs/status.json`.

### Yahoo Finance

Usato via `yfinance` per dati storici giornalieri:

- `BTC-USD`;
- `BTC-EUR`.

### Coinbase

Usato per prezzo spot live:

- `BTC-USD`;
- `BTC-EUR`.

### Cloudflare Workers

Usato per:

- webhook Telegram;
- health check;
- conteggio iscritti;
- eliminare il cold start del vecchio Render.

### Telegram Bot API

Usata per:

- ricezione webhook;
- invio risposte;
- registrazione menu comandi;
- comando `setWebhook`;
- comando `setMyCommands`.

### Supabase

Usato come database per gli iscritti Telegram.

### Render

Render era usato in precedenza per il webhook FastAPI. Il progetto e stato
migrato a Cloudflare Worker. I file legacy `telegram_webhook.py`,
`render.yaml` e `RENDER_DEPLOYMENT.md` possono restare come riferimento o
fallback storico, ma il servizio operativo attuale e Cloudflare Worker.

## Secret e variabili

### Cloudflare Worker

Secret necessari:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Variabile non segreta in `cloudflare-worker/wrangler.toml`:

```text
STATUS_JSON_URL=https://raw.githubusercontent.com/giuse2003/BTC_Prudential_Signal/main/docs/status.json
```

### GitHub Actions

Secret necessari:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

`TELEGRAM_BOT_TOKEN` serve anche al workflow manuale per aggiornare il menu
Telegram.

## Come replicare il progetto

### 1. Clonare e installare

```powershell
git clone https://github.com/giuse2003/BTC_Prudential_Signal.git
cd BTC_Prudential_Signal
python -m pip install -r requirements.txt
```

### 2. Eseguire localmente

```powershell
python main.py --force-download
```

Controllare:

```text
reports/report.txt
reports/status.json
reports/historical_signals.csv
reports/equity_timeseries.csv
```

### 3. Testare

```powershell
python -m unittest discover -s tests -v
```

Attualmente i test coprono:

- backtest e conteggio trade;
- filtro candele giornaliere chiuse;
- regole di acquisto/vendita;
- messaggi Telegram legacy;
- webhook legacy;
- iscrizioni Supabase;
- dashboard e endpoint iscritti.

### 4. Configurare Supabase

1. usare il progetto Supabase condiviso `crypto-prudential-signal`;
2. eseguire `supabase/telegram_subscribers.sql` nel SQL Editor;
3. copiare:
   - Project URL;
   - service role key.

### 5. Configurare Cloudflare Worker

```powershell
cd cloudflare-worker
npx wrangler login
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put SUPABASE_URL
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
npx wrangler deploy
```

Verifiche:

```powershell
curl https://btc-prudential-signal.giuse2003.workers.dev/
curl https://btc-prudential-signal.giuse2003.workers.dev/subscribers/count
```

### 6. Collegare Telegram al Worker

Esempio PowerShell:

```powershell
$BOT_TOKEN = "<token bot>"
$WORKER_URL = "https://btc-prudential-signal.giuse2003.workers.dev"
$WEBHOOK_SECRET = "<secret scelto>"

curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" `
  -H "Content-Type: application/json" `
  -d "{\"url\":\"$WORKER_URL/webhook\",\"secret_token\":\"$WEBHOOK_SECRET\",\"allowed_updates\":[\"message\"]}"
```

La risposta attesa:

```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

### 7. Aggiornare menu Telegram

Nel repository GitHub:

1. aprire `Actions`;
2. scegliere `Telegram command menu`;
3. cliccare `Run workflow`;
4. branch `main`.

## Come un agente IA dovrebbe modificare o testare il progetto

Prima di cambiare la strategia:

1. leggere `strategy/signals.py`;
2. leggere `indicators/technical_indicators.py`;
3. leggere `backtest/backtest.py`;
4. scrivere un backtest comparativo senza modificare subito il codice;
5. confrontare rendimento, drawdown, operazioni, win rate e Sharpe;
6. se la modifica viene accettata, aggiornare:
   - `strategy/signals.py`;
   - `reports/generate.py`;
   - `cloudflare-worker/src/worker.js`;
   - test in `tests/`;
   - `docs/status.json` rigenerato.

Comandi minimi di verifica:

```powershell
python -m unittest discover -s tests -v
python main.py
Copy-Item reports\status.json docs\status.json
& "C:\Program Files\nodejs\node.exe" --check cloudflare-worker\src\worker.js
```

Deploy Worker:

```powershell
cd cloudflare-worker
$env:PATH='C:\Program Files\nodejs;' + $env:PATH
npx wrangler deploy
```

Commit:

```powershell
git status --short
git add <file modificati>
git commit -m "<messaggio>"
git push
```

## Limitazioni note

- Il backtest non considera costi di transazione, spread o slippage.
- La strategia e long-only: non apre posizioni short.
- I segnali si basano su indicatori tecnici giornalieri, non su dati on-chain,
  macroeconomici o fondamentali.
- Il prezzo spot Coinbase serve per visualizzazione, non per decidere il
  segnale.
- Le notifiche automatiche ignorano le oscillazioni del solo prezzo spot: il
  messaggio parte solo se cambia `Segnale` oppure cambia il vero/falso di una
  condizione ACQUISTA/VENDI.
- Il broadcast automatico a tutti gli iscritti Supabase non e ancora
  implementato; il monitor automatico usa il `TELEGRAM_CHAT_ID` configurato nei
  GitHub Secrets.
- Alcuni file legacy Render/FastAPI restano nel repository come fallback
  storico ma non rappresentano il deployment principale attuale.

## File principali

```text
config.py                              configurazione generale
main.py                                esecuzione completa locale
hourly_monitor.py                      monitor GitHub Actions
strategy/signals.py                    regole segnale/rischio
indicators/technical_indicators.py     indicatori tecnici
backtest/backtest.py                   motore backtest
reports/generate.py                    report, status JSON, grafico
data/fetch_yahoo.py                    download/caricamento Yahoo Finance
data/daily_candles.py                  esclusione candela UTC corrente
live/coinbase.py                       prezzi spot Coinbase
cloudflare-worker/src/worker.js        bot Telegram e API pubbliche
cloudflare-worker/wrangler.toml        configurazione Worker
supabase/telegram_subscribers.sql      schema database iscritti
docs/                                  dashboard GitHub Pages
tests/                                 test automatici
```
