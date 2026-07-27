# BTC-USD Signal

BTC-USD Signal e una strategia algoritmica giornaliera costruita esclusivamente
sul mercato Coinbase `BTC-USD`. Coinbase `BTC-EUR` fornisce solo il controvalore
spot informativo: non entra in indicatori, azioni o backtest.

## Azioni

- `ACQUISTA`: tutte e quattro le condizioni di acquisto sono vere.
- `VENDI`: due chiusure giornaliere consecutive sono sotto SMA50; ha precedenza.
- `MANTIENI STATO ATTUALE`: ogni altro caso; conserva l'esposizione precedente.

Le condizioni di acquisto sono: Close sopra SMA200, RSI14 almeno 40, Close sopra
quello di 7 giorni prima e volume BTC-USD sopra la media a 20 giorni.

## Dati e backtest

- Fonte unica: API pubblica Coinbase Advanced Trade.
- Candele: `BTC-USD`, granularita giornaliera, UTC, solo giornate concluse.
- Storico disponibile: dal 20 luglio 2015.
- Warm-up: 200 giorni, esclusi dalla valutazione.
- Esecuzione simulata: azione alla chiusura `t`, esposizione dal giorno successivo.
- Esposizione: 0% o 100%; costi, spread, slippage e imposte non inclusi.
- Benchmark: Buy & Hold sullo stesso identico periodo valutato.

## Due tipi di run

La baseline ufficiale e congelata al 26 luglio 2026. Il suo pacchetto contiene
input grezzo, output, formule, ambiente e hash SHA-256 in
[`docs/runs/baseline-v1-2026-07-26/manifest.json`](docs/runs/baseline-v1-2026-07-26/manifest.json).
Non cambia quando Coinbase aggiunge nuove candele.

Il run operativo piu recente e invece dinamico. I suoi valori sono in
[`docs/manifest.json`](docs/manifest.json), mentre `docs/raw_candles.csv` rende
pubblico l'esatto input del run. La dashboard legge questo pacchetto.

## Riprodurre la baseline

Servono Git e Python 3.13.0. Da un clone pulito:

```powershell
git clone https://github.com/giuse2003/BTC_Prudential_Signal.git
cd BTC_Prudential_Signal
git checkout baseline-v1-2026-07-26
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.venv\Scripts\python reproduce.py --manifest docs/runs/baseline-v1-2026-07-26/manifest.json
```

Su Linux/macOS usare `.venv/bin/python`. La verifica non interroga Coinbase:
controlla ambiente, sorgenti, snapshot e artefatti, ricalcola il backtest dal
CSV congelato e richiede output byte per byte identici. La procedura completa e
descritta in [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

## Run operativo

```powershell
python -m pip install --require-hashes -r requirements.lock
python main.py --force-download
python -m unittest discover -s tests -v
```

La pipeline prepara gli artefatti in staging, verifica `run_id` e hash, poi li
pubblica insieme. Il monitor schedulato aggiorna la cache Coinbase e pubblica
DAILY e LIVE PREVIEW senza provider alternativi.

Dashboard: [BTC-USD Signal](https://giuse2003.github.io/BTC_Prudential_Signal/)

Questo progetto e informativo e sperimentale. Un backtest non e una promessa di
rendimento e non costituisce consulenza finanziaria.
