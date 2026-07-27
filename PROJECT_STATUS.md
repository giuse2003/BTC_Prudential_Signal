# Stato del progetto

## Stato corrente

- Nome: **BTC-USD Signal**.
- Versione metodologica: **1.0**.
- Fonte: Coinbase Advanced Trade, mercato `BTC-USD`.
- Controvalore: spot `BTC-EUR`, solo informativo.
- Baseline: quattro condizioni di acquisto, una condizione di vendita.
- Azioni pubblicate: `ACQUISTA`, `MANTIENI STATO ATTUALE`, `VENDI`.
- DAILY e LIVE PREVIEW separati.
- Backtest e Buy & Hold sullo stesso periodo successivo al warm-up SMA200.
- Pubblicazione transazionale con manifest e hash.

I valori ufficiali correnti sono esclusivamente quelli di
[`docs/manifest.json`](docs/manifest.json). Questo evita che documenti e
dashboard mantengano copie manuali non piu sincronizzate.

## Limiti aperti

- Il modello non e stato validato su un vero campione out-of-sample congelato.
- Costi, spread, slippage, imposte e remunerazione della liquidita sono esclusi.
- I risultati dipendono dallo storico e dalla microstruttura Coinbase.
- LIVE PREVIEW e provvisorio e puo cambiare prima della chiusura UTC.
- Non esiste ancora un modello autonomo BTC-EUR.
