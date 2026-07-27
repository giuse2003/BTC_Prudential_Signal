# BTC-USD Signal

BTC-USD Signal e una strategia algoritmica giornaliera costruita esclusivamente
sul mercato Coinbase `BTC-USD`. Il prezzo Coinbase `BTC-EUR` e mostrato soltanto
come controvalore informativo e non entra in indicatori, azioni o backtest.

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
- Esecuzione simulata: azione calcolata alla chiusura `t`, esposizione dal giorno successivo.
- Esposizione: 0% o 100%; costi, spread, slippage e imposte non inclusi.
- Benchmark: Buy & Hold sullo stesso identico periodo valutato.

I numeri ufficiali non sono copiati nella documentazione: sono in
[`docs/manifest.json`](docs/manifest.json), insieme a periodo, regole, hash e
metriche del run pubblicato. La dashboard legge direttamente quel manifest.

## Esecuzione

```powershell
python -m pip install -r requirements.txt
python main.py --force-download
python -m unittest discover -s tests -v
```

La pipeline prepara tutti gli artefatti in staging, ne verifica `run_id` e hash,
poi li pubblica insieme. In caso di errore resta disponibile l'ultimo pacchetto
completo. Il monitor schedulato aggiorna la cache Coinbase e pubblica DAILY e
LIVE PREVIEW senza usare provider alternativi.

Dashboard: [BTC-USD Signal](https://giuse2003.github.io/BTC_Prudential_Signal/)

Questo progetto e informativo e sperimentale. Un backtest non e una promessa di
rendimento e non costituisce consulenza finanziaria.
