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
- Baseline v1 congelata al 2026-07-26 e riproducibile offline.
- Ambiente Python e dipendenze bloccati con hash.
- Esperimento BTC-only `V1-S1`/`V1-B1` riproducibile e separato dal modello.

I valori ufficiali della baseline sono in
[`docs/runs/baseline-v1-2026-07-26/manifest.json`](docs/runs/baseline-v1-2026-07-26/manifest.json).
I valori operativi correnti sono separati in [`docs/manifest.json`](docs/manifest.json).

## Ricerca non operativa

Le varianti `V1-S1` e `V1-B1` sono risultate `NON PROMUOVIBILE` secondo il
protocollo registrato. La baseline, le regole pubblicate e i segnali live non
sono stati cambiati. Il report e in
[`docs/experiments/btc-model-candidates-v1-2026-07-26/report.md`](docs/experiments/btc-model-candidates-v1-2026-07-26/report.md).

## Limiti aperti

- Il modello non e stato validato su un vero campione out-of-sample congelato.
- Costi, spread, slippage, imposte e remunerazione della liquidita sono esclusi.
- I risultati dipendono dallo storico e dalla microstruttura Coinbase.
- LIVE PREVIEW e provvisorio e puo cambiare prima della chiusura UTC.
- Non esiste ancora un modello autonomo BTC-EUR.
- La riproducibilita dimostra il calcolo storico, non elimina overfitting o rischio futuro.
