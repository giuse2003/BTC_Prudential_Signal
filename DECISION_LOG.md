# Cronostoria delle decisioni

## 2026-07-27 - Coerenza BTC-USD Signal v1

- Il progetto assume il nome **BTC-USD Signal**.
- Coinbase diventa l'unica sorgente per storico, prezzi e volumi.
- `BTC-USD` e il mercato del modello; `BTC-EUR` resta un controvalore informativo.
- Lo storico inizia dalla prima candela Coinbase disponibile.
- I primi 200 giorni sono warm-up SMA200 e non entrano nel confronto.
- La metodologia finanziaria del backtest resta invariata.
- La baseline ufficiale contiene soltanto quattro regole buy e una regola sell.
- La vendita ha precedenza in caso di conflitto logico.
- Le sole azioni pubblicabili sono `ACQUISTA`, `MANTIENI STATO ATTUALE`, `VENDI`.
- DAILY e LIVE PREVIEW vengono distinti esplicitamente.
- Il Worker Cloudflare non ricalcola il modello: legge il pacchetto validato.
- Ogni pubblicazione usa un unico `run_id`, un manifest e hash SHA-256.
- I report e gli esperimenti non appartenenti alla baseline corrente vengono rimossi.

Il codice precedente alla revisione resta identificabile dal tag Git
`pre-coherence-v1`; non viene presentato come versione operativa o baseline.

## 2026-07-27 - Baseline v1 riproducibile

- La baseline ufficiale viene congelata all'ultima candela del 2026-07-26.
- Lo snapshot OHLCV Coinbase diventa parte del pacchetto versionato.
- Python 3.13.0 e tutte le dipendenze sono bloccati con hash.
- Il manifest registra formule, periodo, metriche, sorgenti e artefatti.
- `reproduce.py` ricalcola offline e richiede output canonici byte-identici.
- Il run operativo resta separato e pubblica il proprio input grezzo.
- Un nuovo intervallo temporale richiedera una nuova baseline e un nuovo tag,
  senza modificare retroattivamente `baseline-v1-2026-07-26`.

## 2026-07-27 - Primo esperimento di miglioramento BTC-only

- La baseline v1 rimane invariata.
- Vengono registrati due candidati: `V1-S1` e `V1-B1`.
- La valutazione usa soltanto lo snapshot congelato BTC-USD.
- Sono applicati cinque scenari di costo, cinque blocchi temporali e bootstrap
  accoppiato a blocchi.
- `V1-S1` migliora molte metriche ma non supera la soglia bootstrap richiesta.
- `V1-B1` non prevale nella maggioranza dei blocchi e non supera il bootstrap.
- Entrambi sono classificati `NON PROMUOVIBILE` e non entrano nei segnali.
