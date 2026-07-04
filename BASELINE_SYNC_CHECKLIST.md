# Baseline Sync Checklist

Questa checklist va usata ogni volta che cambia la baseline operativa della
strategia: condizioni `ACQUISTA`, regola `VENDI`, soglie RSI/momentum/volume,
numero o significato delle condizioni mostrate agli utenti.

Obiettivo: evitare che codice, dashboard, bot Telegram, Cloudflare Worker,
documentazione e JSON pubblicati dicano cose diverse.

## 1. Logica core

Aggiornare:

- `strategy/signals.py`
  - `compute_strict_signal`
  - `_buy_condition_statuses`
  - `live_condition_statuses`
  - eventuali formatter collegati a Telegram
- `reports/generate.py`
  - `save_status_json`
  - `save_live_status_json`
  - etichette in `condition_groups`

Controllare se servono modifiche a:

- `config.py`
- `indicators/technical_indicators.py`
- `backtest/backtest.py` solo se cambia il metodo di simulazione, non per
  semplici regole di segnale.

## 2. Dashboard GitHub Pages

Aggiornare:

- `docs/index.html`
  - lista statica delle condizioni nel blocco Metodo
  - statistiche statiche del blocco Backtest, incluse percentuali di
    rendimento, drawdown, Sharpe e barre comparative
  - serie visualizzate nel grafico prezzo e relativa legenda
- `docs/app.js`
  - rendering condizioni, se cambia la struttura JSON
- `docs/status.json`
- `docs/live-status.json`
- `docs/chart-data.json`

Rigenerare gli artefatti con il monitor o con una run locale equivalente:

```powershell
python main.py --force-download
python hourly_monitor.py
```

Se la run locale non puo usare rete o secret, rigenerare almeno i JSON con
dati coerenti e lasciare che GitHub Actions li aggiorni alla prima esecuzione.

## 3. Telegram

Aggiornare:

- `strategy/signals.py`
  - `format_condition_message`
  - `format_telegram_message`
- `telegram_command.py`
  - fallback legacy polling
- `telegram_webhook.py`
  - fallback legacy FastAPI
- `cloudflare-worker/src/worker.js`
  - `CONDITIONS_MESSAGE`
  - `buildLiveSnapshot`
  - `deriveConditionGroups`
  - `formatSignalConditions`

Verificare manualmente dopo il deploy:

```text
/conditions
/segnale
```

## 4. Cloudflare Worker

Il bot Telegram principale usa il Worker. Dopo ogni modifica a
`cloudflare-worker/src/worker.js`, il push GitHub non basta: serve deploy.

Comandi:

```powershell
cd D:\Github\BTC_Prudential_Signal\cloudflare-worker
npx wrangler login
npx wrangler deploy
```

Verifica health check:

```powershell
Invoke-RestMethod "https://btc-prudential-signal.giuse2003.workers.dev/"
```

Risposta attesa:

```json
{"status":"ok"}
```

## 5. GitHub Actions

Controllare:

- `.github/workflows/hourly-monitor.yml`
  - deve continuare a copiare `reports/status.json`,
    `reports/chart-data.json` e `reports/live-status.json` in `docs/`.
- `.github/workflows/telegram-command.yml`
  - se cambia la lista dei comandi, aggiornare il menu Telegram.

Dopo il push, verificare che il workflow `Hourly BTC monitor (Telegram)` non
riporti errori e che pubblichi JSON coerenti.

## 6. Documentazione decisionale

Aggiornare sempre:

- `README.md`
- `PROJECT_OVERVIEW.md`
- `PROJECT_STATUS.md`
- `DECISION_LOG.md`
- `SIGNAL_RULE_VERIFICATION_LOG.md`

Se una variante viene valutata ma non promossa, documentare:

- regola testata;
- periodo dati;
- metriche principali;
- motivo per cui non e stata implementata;
- quando potrebbe diventare il rimpiazzo preferito.

## 7. Test

Aggiornare o aggiungere test per:

- logica segnale in `tests/test_signal_rules.py`;
- messaggi Telegram in `tests/test_telegram_message.py`;
- webhook/command legacy in `tests/test_telegram_webhook.py` e
  `tests/test_telegram_commands.py`;
- Worker Cloudflare in `tests/test_cloudflare_worker_conditions.py`;
- eventuali chiavi condizioni tipo `BUY:0000|SELL:1` nei test dello stato.

Comandi utili:

```powershell
python -m unittest discover -s tests -v
node --check cloudflare-worker/src/worker.js
```

## 8. Checklist finale prima del push

Eseguire:

```powershell
rg "SMA50 sopra SMA200|SMA50 above SMA200|SMA50 live sopra" README.md PROJECT_OVERVIEW.md PROJECT_STATUS.md SIGNAL_RULE_VERIFICATION_LOG.md DECISION_LOG.md strategy reports tests cloudflare-worker docs
git status --short
git diff --check
```

Le occorrenze rimaste devono essere intenzionali, per esempio storico
decisionale o scoring informativo, non condizioni operative attive.

Poi:

```powershell
git pull --rebase origin main
git push origin main
```

Se il push include modifiche al Worker, ricordarsi del deploy Cloudflare.
