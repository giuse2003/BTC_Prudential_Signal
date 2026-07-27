# BTC-USD Signal - Valori per valutazione esterna

Questo documento descrive la baseline v1 congelata. La fonte canonica dei
numeri e
[`docs/runs/baseline-v1-2026-07-26/manifest.json`](docs/runs/baseline-v1-2026-07-26/manifest.json).
Il manifest operativo in `docs/manifest.json` cambia invece con le nuove candele.

## Identita e dati

| Voce | Valore |
|---|---|
| Progetto | BTC-USD Signal |
| Versione | 1.0 |
| Mercato del modello | Coinbase `BTC-USD` |
| Controvalore informativo | Coinbase `BTC-EUR` spot |
| Granularita | 1 giorno, UTC |
| Candele usate | solo giornate concluse |
| Prima candela Coinbase | 2015-07-20 |
| Warm-up SMA200 | 2015-07-20 / 2016-02-03 |
| Periodo valutato | 2016-02-04 / 2026-07-26 |
| Durata valutata | 3.826 giorni di calendario |

Non vengono uniti dati di mercati o provider differenti. La cache locale e una
copia del medesimo storico Coinbase e viene controllata per duplicati, buchi e
righe non concluse.

## Regole operative

`ACQUISTA` soltanto quando sono vere tutte le condizioni:

1. Close sopra SMA200.
2. RSI14 maggiore o uguale a 40.
3. Close sopra il Close di 7 giorni prima.
4. Volume giornaliero BTC-USD sopra la propria media a 20 giorni.

`VENDI` quando il Close e sotto SMA50 per due candele giornaliere consecutive.
La vendita ha precedenza. In ogni altro caso l'azione e
`MANTIENI STATO ATTUALE`.

## Metodo del backtest

- Esposizione 100% dopo `ACQUISTA` e 0% dopo `VENDI`.
- `MANTIENI STATO ATTUALE` conserva l'esposizione precedente.
- L'azione calcolata alla chiusura del giorno `t` si applica dal rendimento del
  giorno successivo (`shift(1)`).
- Buy & Hold investe al primo Close del medesimo periodo valutato.
- Calendario di annualizzazione e Sharpe: 365 giorni.
- Tasso privo di rischio: 0%.
- Operazioni e win rate includono soltanto trade long completati.
- Costi, spread, slippage, imposte e rendimento della liquidita: non inclusi.

## Risultati baseline Coinbase

| Metrica | BTC-USD Signal | Buy & Hold BTC-USD |
|---|---:|---:|
| Rendimento totale | +36.738,21% | +16.740,92% |
| Rendimento annualizzato | +75,75% | +63,10% |
| Drawdown massimo | -48,31% | -83,80% |
| Sharpe Ratio | 1,487 | 1,067 |
| Operazioni completate | 37 | n/a |
| Win rate | 48,65% | n/a |

Sono risultati storici lordi, non una previsione. L'assenza di costi e di un
vero periodo out-of-sample congelato impone prudenza: non e corretto tradurre
questi rendimenti in un'aspettativa realistica di profitto futuro.

## Verifica indipendente

Il pacchetto congelato include l'esatto CSV Coinbase usato. Con Python 3.13.0 e
le dipendenze bloccate da `requirements.lock`, il comando seguente ricostruisce
gli output senza rete e ne richiede l'identita byte per byte:

```powershell
python reproduce.py --manifest docs/runs/baseline-v1-2026-07-26/manifest.json
```

Istruzioni da clone pulito, controlli e limiti sono in
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

## Output correnti

`status.json` contiene il DAILY ufficiale; `live-status.json` contiene una LIVE
PREVIEW provvisoria. Entrambi pubblicano soltanto una delle tre azioni ammesse.
Le condizioni restano disponibili a fini esplicativi, ma non costituiscono
azioni aggiuntive o uno stato di portafoglio pubblicato.

Il pacchetto e valido solo se `status.json`, `live-status.json`,
`chart-data.json` e `manifest.json` hanno lo stesso `run_id`. Il manifest include
gli hash SHA-256 di report, storico, equity e grafico.

## Cronostoria

| Data | Modifica |
|---|---|
| 2026-07-27 | Progetto rinominato BTC-USD Signal e baseline fissata alla versione 1.0. |
| 2026-07-27 | Tutta la catena dati migrata alle API pubbliche Coinbase. |
| 2026-07-27 | BTC-EUR limitato al solo controvalore spot informativo. |
| 2026-07-27 | Warm-up SMA200 escluso dal periodo comune strategia/Buy & Hold. |
| 2026-07-27 | DAILY e LIVE PREVIEW separati con un unico vocabolario di azioni. |
| 2026-07-27 | Report ed esperimenti non appartenenti alla baseline v1 rimossi. |
| 2026-07-27 | Aggiunti manifest, hash, validazione e pubblicazione transazionale. |
| 2026-07-27 | Dashboard e Worker collegati allo stesso pacchetto informativo. |
| 2026-07-27 | Congelati input, ambiente e output della baseline v1 con verifica offline. |
| 2026-07-27 | Il run operativo pubblica anche le candele grezze e tutti gli artefatti del manifest. |

## Valutazione critica

Punti positivi: regole deterministiche, nessun look-ahead nell'esecuzione,
benchmark omogeneo, sorgente unica, artefatti verificabili e drawdown storico
inferiore al Buy & Hold.

Rischi residui: selezione delle regole sullo stesso passato osservato, costi non
modellati, risultati dipendenti da Coinbase, esposizione binaria e drawdown
comunque vicino al 50%. Prima di impiegare capitale reale servono almeno un
periodo out-of-sample congelato, simulazioni con costi realistici e sizing del
rischio coerente con la perdita massima tollerabile.
