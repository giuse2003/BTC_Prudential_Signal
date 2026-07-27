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
