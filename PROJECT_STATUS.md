# Project Status

Ultimo aggiornamento: 9 giugno 2026

## Obiettivo

Produrre segnali prudenziali giornalieri su Bitcoin, pubblicarli in una
dashboard e notificare variazioni rilevanti tramite Telegram.

## Stato corrente

- Pipeline dati Yahoo Finance operativa per `BTC-USD` e `BTC-EUR`.
- Prezzi spot Coinbase disponibili in USD ed EUR.
- Indicatori, strategia, rischio, report e dashboard implementati.
- Monitor GitHub Actions e notifiche Telegram operativi.
- GitHub Pages alimentata da `docs/status.json`.
- Test automatici presenti per calendario, candele chiuse e metriche trade.
- Notifica Telegram semplificata con il solo prezzo EUR e senza sezione
  riepilogativa.
- Avvio manuale GitHub Actions configurato per inviare un'anteprima reale
  della notifica operativa.
- Webhook FastAPI pubblicato e operativo su Render:
  `https://btc-prudential-signal.onrender.com`.
- Webhook Telegram registrato su
  `https://btc-prudential-signal.onrender.com/webhook`.
- Comando `/segnale` verificato con risposta immediata nella chat autorizzata.
- Lettura diretta di `docs/status.json` da GitHub Raw, senza copie locali.
- Workflow `Telegram command listener` mantenuto soltanto come fallback e
  disabilitato durante l'uso del webhook.
- Workflow `Hourly BTC monitor (Telegram)` mantenuto attivo.

## Correzioni completate

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

### Webhook Telegram

- Servizio Render in stato `Live`.
- Health check pubblico verificato con risposta `{"status":"ok"}`.
- Registrazione Telegram verificata tramite `getWebhookInfo`.
- Accesso limitato a `TELEGRAM_CHAT_ID`.
- Richieste autenticate con `TELEGRAM_WEBHOOK_SECRET`.
- `/segnale`, `/start` e `/help` gestiti da FastAPI.

## Verifica

Comando:

```powershell
python -m unittest discover -s tests -v
```

Risultato al momento dell'ultimo aggiornamento:

```text
Ran 16 tests
OK
```

## File principali

- `config.py`: configurazione centralizzata.
- `data/daily_candles.py`: selezione delle candele concluse.
- `strategy/signals.py`: segnale, punteggio e rischio.
- `backtest/backtest.py`: esposizione e metriche.
- `hourly_monitor.py`: esecuzione cloud e Telegram.
- `telegram_command.py`: listener polling mantenuto come fallback.
- `telegram_webhook.py`: endpoint FastAPI per i comandi Telegram.
- `render.yaml`: configurazione di deploy Render.
- `reports/generate.py`: report e stato dashboard.

## Ambito rinviato

Il backtest non include ancora commissioni, spread, slippage o rendimento
della liquidita. Questa estensione e intenzionalmente rinviata.
