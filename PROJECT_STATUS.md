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

## Verifica

Comando:

```powershell
python -m unittest discover -s tests -v
```

Risultato al momento dell'ultimo aggiornamento:

```text
Ran 5 tests
OK
```

## File principali

- `config.py`: configurazione centralizzata.
- `data/daily_candles.py`: selezione delle candele concluse.
- `strategy/signals.py`: segnale, punteggio e rischio.
- `backtest/backtest.py`: esposizione e metriche.
- `hourly_monitor.py`: esecuzione cloud e Telegram.
- `reports/generate.py`: report e stato dashboard.

## Ambito rinviato

Il backtest non include ancora commissioni, spread, slippage o rendimento
della liquidita. Questa estensione e intenzionalmente rinviata.
