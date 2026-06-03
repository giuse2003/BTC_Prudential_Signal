# Quotazione BTC/EUR

Piccola dashboard locale per monitorare la quotazione **Bitcoin (BTC)** rispetto all'**Euro (EUR)** usando l'endpoint pubblico di Coinbase:

- `https://api.coinbase.com/v2/prices/BTC-EUR/spot`

## Avvio

### Opzione A (più semplice)

Apri `index.html` con il browser.

### Opzione B (consigliata: mini server locale)

Se hai Python installato:

```powershell
cd "C:\Users\giuse\Quotazione EUR-BTC"
python -m http.server 5173
```

Poi apri `http://localhost:5173`.

## Note

- Mostra lo **spot price** (1 BTC in EUR) e mantiene uno **storico** (massimo 50 righe) in `localStorage`.
- Refresh automatico configurabile (di default **10s**).

---

## App Python: segnali prudenziali (BUY/SELL + backtest)

Questa cartella include anche uno script Python completamente commentato per:
- scaricare dati giornalieri BTC da Yahoo Finance (yfinance)
- calcolare SMA50/SMA200, RSI(14), ATR(14), volume medio (20gg), massimo/minimo 52 settimane
- assegnare un punteggio 0..100 e generare un segnale prudente: ACQUISTA, MANTIENI oppure VENDI / RIDUCI ESPOSIZIONE
- fare backtest vs Buy & Hold
- generare: report testuale, CSV storico, grafico

### Prerequisiti
- Windows 11
- Python 3.13

### Installazione dipendenze
Apri PowerShell nella cartella e installa:

```powershell
cd "C:\Users\giuse\Quotazione EUR-BTC"
pip install -r requirements.txt
```

### Esecuzione
```powershell
cd "C:\Users\giuse\Quotazione EUR-BTC"
python main.py
```

Output:
- `reports/report.txt`
- `reports/historical_signals.csv`
- `reports/price_sma_signals.png`
- `reports/equity_timeseries.csv`

---

## Dashboard online gratuita (GitHub Pages)

La dashboard pubblicabile online vive nella cartella `docs/`.
Non richiede servizi a pagamento, VPS o piattaforme esterne: usa solo GitHub Actions e GitHub Pages.

Per attivarla:

1. Vai nel repository GitHub.
2. Apri **Settings** → **Pages**.
3. In **Build and deployment**, scegli **Deploy from branch**.
4. Imposta:
   - **Branch**: `main`
   - **Folder**: `/docs`
5. Salva.

Il workflow GitHub Actions genera `reports/status.json`, lo copia in `docs/status.json` e committa automaticamente solo quel file quando cambia.
La dashboard online legge `docs/status.json`.

---

## Monitor “cloud” (GitHub Actions) + notifiche Telegram (ogni ora)

Senza VPS/PC sempre acceso: GitHub Actions esegue un job **ogni ora** e manda un messaggio Telegram **solo se cambia il segnale** o se viene superato un livello importante (SMA200 / 52w high / 52w low).

### 1) Crea bot Telegram e ottieni token
Con `@BotFather`:
- crea il bot
- copia il `TELEGRAM_BOT_TOKEN`

Per ottenere `TELEGRAM_CHAT_ID`:
- scrivi un messaggio al bot
- poi apri nel browser: `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates`
- trova `chat.id`

### 2) Configura Secrets su GitHub
Repository → Settings → Secrets and variables → Actions → **Secrets**:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 3) Avvio
Vai su Actions → “Hourly BTC monitor (Telegram)” → Run workflow.
Poi partirà automaticamente ogni ora.

