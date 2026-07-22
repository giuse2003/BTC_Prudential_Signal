# Project Status

Ultimo aggiornamento: 22 luglio 2026

## Obiettivo

Produrre segnali prudenziali giornalieri su Bitcoin, pubblicarli in una
dashboard e notificare variazioni rilevanti tramite Telegram.

## Stato corrente

- Pipeline dati Yahoo Finance operativa per `BTC-USD` e `BTC-EUR`.
- Prezzi spot Coinbase disponibili in USD ed EUR.
- Grafico dashboard a candele giornaliere: storico chiuso Yahoo Finance e
  candela UTC corrente provvisoria Coinbase, sostituita dal dato Yahoo alla
  pubblicazione della chiusura ufficiale.
- Indicatori, strategia, rischio, report e dashboard implementati.
- Monitor GitHub Actions e notifiche Telegram operativi.
- GitHub Pages alimentata da `docs/status.json`.
- Test automatici presenti per calendario, candele chiuse e metriche trade.
- Notifica Telegram semplificata con il solo prezzo EUR e senza sezione
  riepilogativa.
- Avvio manuale GitHub Actions configurato per aggiornare i dati senza inviare
  messaggi Telegram.
- Notifiche Telegram esclusivamente LIVE quando varia una delle 5 condizioni;
  nessun invio DAILY per amministratore o iscritti Supabase.
- `/segnale` usa soltanto `docs/live-status.json`, senza fallback DAILY.
- Webhook Telegram e API pubbliche serviti esclusivamente da Cloudflare
  Worker: `https://btc-prudential-signal.giuse2003.workers.dev`.
- Comando `/segnale` disponibile in ogni chat privata con il bot.
- Database Supabase degli iscritti creato e verificato con RLS forzata.
- Il progetto Supabase e ora condiviso con ETH ed e stato rinominato
  `crypto-prudential-signal` per evitare ambiguita.
- BTC continua a usare la tabella dedicata `public.telegram_subscribers`;
  ETH usa `public.telegram_subscribers_eth`.
- Comandi `/iscrivimi`, `/disiscrivimi` e `/privacy` implementati.
- Dashboard Telegram con deep link e contatore aggregato implementata.
- Dashboard e contatore collegati a GitHub Pages e Cloudflare Worker.
- Lettura diretta di `docs/status.json` da GitHub Raw, senza copie locali.
- Workflow `Telegram command listener` mantenuto soltanto come fallback e
  disabilitato durante l'uso del webhook.
- Workflow `Hourly BTC monitor (Telegram)` mantenuto attivo.
- Baseline aggiornata: la condizione Golden Cross `SMA50 > SMA200` non e piu
  richiesta per `ACQUISTA`.

## Correzioni completate

### Baseline senza Golden Cross

- `ACQUISTA` richiede ora Close sopra SMA200, RSI >= 40, momentum positivo a
  7 giorni e volume sopra la media a 20 giorni.
- `SMA50 > SMA200` resta disponibile nello scoring tecnico/rischio
  informativo, ma non decide piu il segnale operativo di acquisto.
- `VENDI` resta invariato: Close sotto SMA50 per 2 giorni consecutivi.
- Dashboard, Telegram, Cloudflare Worker e JSON di stato mostrano 4 condizioni
  di acquisto e 1 condizione di vendita. La chiave LIVE `BUY:xxxx|SELL:x`
  decide se inviare una nuova notifica automatica.
- La variante prudenziale `No Golden Cross + SMA50 rising 7d` e documentata in
  `SIGNAL_RULE_VERIFICATION_LOG.md` come possibile rimpiazzo futuro.

### Calendario crypto

- `365` periodi giornalieri per annualizzazione e Sharpe Ratio.
- Finestra a 52 settimane impostata a `365` giorni.

### Candele giornaliere

- La candela UTC del giorno corrente viene esclusa.
- Segnale e rischio vengono calcolati sull'ultima candela conclusa.
- La stessa regola viene applicata sia da `main.py` sia da
  `hourly_monitor.py`.

### Operazioni e win rate

- Una operazione corrisponde a un trade long completato.
- Il win rate usa come denominatore soltanto i trade chiusi.
- Le posizioni ancora aperte non vengono considerate concluse.

### Cloudflare Worker

- Health check pubblico disponibile su `GET /`.
- Webhook Telegram disponibile su `POST /webhook`.
- Comandi disponibili nelle chat private; i gruppi vengono ignorati.
- Richieste autenticate con `TELEGRAM_WEBHOOK_SECRET`.
- `/segnale`, `/start`, `/help`, `/privacy`, `/iscrivimi` e
  `/disiscrivimi` gestiti dal Worker.
- Iscrizioni persistenti su Supabase senza duplicati.
- Endpoint pubblico `GET /subscribers/count` senza dati personali.
- CORS limitato all'origine GitHub Pages e agli indirizzi locali di test.
- Il precedente servizio Render e il webhook FastAPI sono stati rimossi.

### Supabase condiviso con ETH

- Il vecchio progetto Supabase nato come `btc-prudential-signal` e stato
  rinominato `crypto-prudential-signal`.
- La rinomina riguarda il nome visualizzato nel pannello Supabase, non la
  separazione dei dati.
- Le iscrizioni BTC restano in `public.telegram_subscribers`.
- Le iscrizioni ETH sono isolate in `public.telegram_subscribers_eth`.
- I Worker BTC ed ETH possono usare lo stesso `SUPABASE_URL` e la stessa
  `SUPABASE_SERVICE_ROLE_KEY`, ma devono puntare a tabelle diverse.
- Token Telegram, webhook secret e repository restano separati tra BTC ed ETH.

## Verifica

Comando:

```powershell
python -m unittest discover -s tests -v
```

Risultato al momento dell'ultimo aggiornamento:

```text
Ran 49 tests
OK
```

## File principali

- `config.py`: configurazione centralizzata.
- `data/daily_candles.py`: selezione delle candele concluse.
- `strategy/signals.py`: segnale, punteggio e rischio.
- `backtest/backtest.py`: esposizione e metriche.
- `hourly_monitor.py`: esecuzione cloud e Telegram.
- `telegram_command.py`: listener polling mantenuto come fallback.
- `telegram_subscribers.py`: accesso server-side agli iscritti Supabase.
- `cloudflare-worker/src/worker.js`: webhook, comandi e API pubbliche.
- `reports/generate.py`: report e stato dashboard.

## Ambito rinviato

Il backtest non include ancora commissioni, spread, slippage o rendimento
della liquidita. Questa estensione e intenzionalmente rinviata.
