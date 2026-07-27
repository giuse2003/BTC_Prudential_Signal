# Riproducibilita

## Oggetto verificato

La baseline congelata `baseline-v1-2026-07-26` usa le candele Coinbase
`BTC-USD` dal 2015-07-20 al 2026-07-26. Il pacchetto si trova in
`docs/runs/baseline-v1-2026-07-26/` e comprende:

- `raw_candles.csv`: input OHLCV esatto;
- `manifest.json`: identita, ambiente, formule, periodo, metriche e hash;
- `status.json` e `chart-data.json`: stato e serie per la dashboard;
- `historical_signals.csv`: indicatori, condizioni e azioni giornaliere;
- `equity_timeseries.csv`: equity strategia e Buy & Hold;
- `report.txt`: riepilogo leggibile.

Il PNG operativo non fa parte degli artefatti canonici congelati, perche il
raster prodotto da Matplotlib puo variare tra piattaforme pur a parita di dati.
Le serie numeriche da cui deriva sono invece verificate byte per byte.

## Procedura da clone pulito

Prerequisiti: Git e Python CPython 3.13.0 a 64 bit.

```powershell
git clone https://github.com/giuse2003/BTC_Prudential_Signal.git
cd BTC_Prudential_Signal
git checkout baseline-v1-2026-07-26
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.venv\Scripts\python reproduce.py --manifest docs/runs/baseline-v1-2026-07-26/manifest.json
```

Comandi equivalenti Linux/macOS:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python reproduce.py --manifest docs/runs/baseline-v1-2026-07-26/manifest.json
```

L'installazione richiede accesso all'indice Python. Dopo l'installazione,
`reproduce.py` lavora offline e non contatta Coinbase o altri servizi.

## Cosa viene controllato

La verifica fallisce se cambia almeno uno di questi elementi:

- versione Python o versione di una dipendenza bloccata;
- hash di `requirements.lock`;
- hash di un file sorgente che determina il modello;
- hash dello snapshot Coinbase o di un artefatto pubblicato;
- periodo, metrica o byte di un output rigenerato.

Il tag Git identifica il checkout; gli hash dei singoli sorgenti nel manifest
sono il controllo definitivo del codice effettivamente usato. I terminatori dei
sorgenti vengono normalizzati a `LF` prima dell'hash, per non confondere una
conversione Git Windows con una modifica del modello. Gli artefatti canonici
sono invece confrontati byte per byte e il repository ne forza i terminatori `LF`.

## Creare un nuovo congelamento

Questa operazione usa Coinbase e crea una baseline distinta; non aggiorna
silenziosamente quella v1 esistente.

```powershell
python freeze_baseline.py --as-of YYYY-MM-DD --output docs/runs/NOME-RUN --run-id NOME-RUN --source-tag NOME-TAG --force-download
python reproduce.py --manifest docs/runs/NOME-RUN/manifest.json
```

Il nuovo snapshot va revisionato, committato e associato al tag dichiarato nel
manifest. Cambiare la data significa creare una nuova baseline, non riscrivere
la baseline `baseline-v1-2026-07-26`.

## Run operativo corrente

Il pacchetto in `docs/` e aggiornato nel tempo e quindi non puo avere output
immutabili. Rimane pero tracciabile: pubblica `raw_candles.csv`, commit sorgente,
versioni dirette, hash del lock e hash di ogni artefatto. Tutti i file del
manifest vengono promossi insieme dal workflow GitHub Actions.
