# BTC Prudential Signal

Sistema Python per il monitoraggio prudenziale di Bitcoin tramite indicatori
tecnici giornalieri, dashboard web e notifiche Telegram.

## Monitor online

**[Apri la dashboard BTC Prudential Signal](https://giuse2003.github.io/BTC_Prudential_Signal/)**

La pagina mostra il segnale corrente, il livello di rischio, i prezzi BTC e
gli ultimi indicatori pubblicati dal monitor.

Il progetto genera tre possibili segnali:

- `ACQUISTA`: tutte le condizioni rialziste richieste sono confermate.
- `MANTIENI`: non ci sono conferme sufficienti per una nuova operazione.
- `VENDI`: le condizioni di debolezza previste dalla strategia sono confermate.

Il segnale e il livello di rischio sono strumenti informativi e non
costituiscono consulenza finanziaria.

## Funzionalita

- Download dei dati giornalieri `BTC-USD` e `BTC-EUR` tramite Yahoo Finance.
- Prezzi spot USD ed EUR tramite endpoint pubblico Coinbase.
- Calcolo di SMA50, SMA200, RSI(14), ATR(14), volume medio e massimo/minimo
  delle ultime 52 settimane.
- Generazione di segnale, punteggio tecnico e livello di rischio.
- Backtest della strategia rispetto al Buy & Hold.
- Report testuale, CSV storico, serie equity e grafico.
- Dashboard locale e dashboard pubblicabile con GitHub Pages.
- Monitor schedulato con GitHub Actions e notifiche Telegram.
- Comando Telegram `/segnale` servito in tempo reale da un webhook FastAPI
  pubblicato su Render.
- Iscrizioni Telegram persistenti su Supabase tramite `/iscrivimi` e
  `/disiscrivimi`.
- Card pubblica per aprire il bot e visualizzare il numero aggregato degli
  iscritti attivi.

## Regole temporali

Bitcoin viene trattato come un mercato attivo 7 giorni su 7:

- l'anno statistico contiene `365` periodi giornalieri;
- massimo e minimo a 52 settimane usano una finestra di `365` giorni;
- rendimento annualizzato e Sharpe Ratio usano `365` periodi;
- i segnali usano esclusivamente candele giornaliere concluse;
- la candela UTC del giorno corrente viene esclusa per evitare segnali basati
  su prezzo e volume ancora parziali.

## Logica del backtest

Il segnale calcolato alla chiusura del giorno viene applicato al rendimento del
giorno successivo, evitando l'uso anticipato di informazioni.

La mappatura del segnale e:

- `ACQUISTA`: esposizione 100%;
- `MANTIENI`: conserva l'esposizione precedente;
- `VENDI`: esposizione 0%.

Una operazione e definita come un trade long completato, dall'entrata
all'uscita. Il numero operazioni e il win rate considerano soltanto trade
chiusi; una posizione ancora aperta alla fine del periodo non viene inclusa.

Il backtest attuale non considera commissioni, spread o slippage.

## Requisiti

- Python 3.13
- Dipendenze elencate in `requirements.txt`

Installazione:

```powershell
git clone https://github.com/giuse2003/BTC_Prudential_Signal.git
cd BTC_Prudential_Signal
python -m pip install -r requirements.txt
```

## Esecuzione analisi

```powershell
python main.py --force-download
```

Output principali:

- `reports/report.txt`
- `reports/historical_signals.csv`
- `reports/price_sma_signals.png`
- `reports/equity_timeseries.csv`
- `reports/status.json`

## Dashboard locale

Prima genera i dati:

```powershell
python main.py --force-download
```

Poi avvia il server:

```powershell
python run_dashboard.py
```

Apri `http://localhost:8000`.

## Dashboard GitHub Pages

La dashboard pubblica e disponibile qui:

**[https://giuse2003.github.io/BTC_Prudential_Signal/](https://giuse2003.github.io/BTC_Prudential_Signal/)**

I file della dashboard si trovano in `docs/` e leggono `docs/status.json`.

Configurazione:

1. Apri **Settings > Pages** nel repository.
2. Seleziona **Deploy from branch**.
3. Imposta il branch `main` e la cartella `/docs`.

Il workflow aggiorna `reports/status.json`, lo copia in `docs/status.json` e
pubblica il nuovo stato.

## Telegram e GitHub Actions

Configura questi GitHub Actions Secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Il workflow `.github/workflows/hourly-monitor.yml`:

1. scarica i dati aggiornati;
2. rimuove la candela giornaliera UTC ancora aperta;
3. calcola segnale e rischio sull'ultima candela chiusa;
4. aggiorna la dashboard;
5. invia Telegram quando cambia il segnale o il rischio diventa `ALTO`.

Un avvio manuale tramite `workflow_dispatch` invia il messaggio operativo
completo, utile per verificare direttamente il layout su Telegram.
La pianificazione GitHub Actions e best effort e puo subire ritardi.

### Comando Telegram in tempo reale

Scrivi al bot:

```text
/segnale
```

Il comando viene gestito dal servizio FastAPI `telegram_webhook.py`, operativo
su Render:

```text
https://btc-prudential-signal.onrender.com
```

Il webhook:

- riceve `POST /webhook` da Telegram;
- accetta comandi soltanto da `TELEGRAM_CHAT_ID`;
- scarica sempre `docs/status.json` dal GitHub Raw URL pubblico;
- non salva copie locali e non modifica il monitor;
- usa il formatter Telegram gia esistente.
- risponde con segnale, rischio, prezzo EUR e indicazione.

Sono disponibili anche `/start` e `/help`.

Il webhook supporta inoltre:

```text
/iscrivimi
/disiscrivimi
/privacy
```

I comandi funzionano nelle chat private con il bot. I gruppi vengono ignorati.

La dashboard pubblica contiene il pulsante **Iscriviti su Telegram**, collegato
a `@BTC_Prudential_Signal_bot`, e mostra il conteggio aggregato ottenuto da:

```text
GET https://btc-prudential-signal.onrender.com/subscribers/count
```

L'endpoint restituisce soltanto `active_subscribers`. Il frontend non contiene
chiavi Supabase, token Telegram o altri secret.

Il deploy e il collegamento Telegram sono stati verificati il 9 giugno 2026:

- servizio Render in stato `Live`;
- health check `GET /` con risposta `{"status":"ok"}`;
- webhook Telegram registrato su `/webhook`;
- comando `/segnale` verificato con risposta immediata.

Guida completa: [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md).

Il workflow `Telegram command listener`, basato su `getUpdates`, resta nel
repository soltanto come fallback e deve rimanere disabilitato mentre il
webhook e registrato. Il workflow `Hourly BTC monitor (Telegram)` deve restare
attivo per aggiornare `docs/status.json` e inviare i cambi automatici.

Sul piano gratuito Render il servizio puo sospendersi dopo un periodo di
inattivita. In quel caso soltanto la prima richiesta puo richiedere piu tempo;
quando il servizio e attivo, la risposta e normalmente immediata.

## Test

```powershell
python -m unittest discover -s tests -v
```

I test verificano:

- esclusione della candela giornaliera corrente;
- gestione di indici con e senza timezone;
- annualizzazione su 365 giorni;
- conteggio dei soli trade completati;
- esclusione delle posizioni ancora aperte dal win rate.

## Struttura

```text
backtest/       motore e metriche del backtest
data/           download, caricamento e filtro candele chiuse
indicators/     indicatori tecnici
live/           prezzi spot Coinbase
notifications/  invio Telegram
reports/        generazione degli output
state/          stato persistente del monitor
strategy/       punteggio, segnale e rischio
tests/          test automatici
docs/           dashboard GitHub Pages
telegram_webhook.py  servizio FastAPI per i comandi Telegram
render.yaml          configurazione Blueprint Render
```

Per lo stato corrente e le decisioni progettuali:

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [DECISION_LOG.md](DECISION_LOG.md)
- [TELEGRAM_SUBSCRIBERS_ROADMAP.md](TELEGRAM_SUBSCRIBERS_ROADMAP.md)
- [SUPABASE_SETUP.md](SUPABASE_SETUP.md)
