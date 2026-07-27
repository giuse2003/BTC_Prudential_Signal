# BTC-USD Signal - Architettura

## Contratto informativo

La catena ufficiale e unica:

`Coinbase BTC-USD -> candele DAILY UTC chiuse -> indicatori -> regole -> backtest -> manifest -> dashboard/Worker`

`BTC-EUR` non e una seconda strategia: fornisce esclusivamente il prezzo spot
informativo nei contenuti LIVE PREVIEW.

## Componenti

| Componente | Responsabilita |
|---|---|
| `data/coinbase.py` | download a blocchi, retry, cache, deduplica e controllo giorni mancanti |
| `indicators/technical_indicators.py` | SMA50, SMA200, RSI14, volume medio 20, ATR14 e momentum 7 giorni |
| `strategy/rules.py` | vocabolario delle tre azioni e precedenza della vendita |
| `strategy/signals.py` | applicazione delle quattro regole buy e dell'unica regola sell |
| `backtest/backtest.py` | esposizione 0/100, shift di un giorno, metriche e Buy & Hold |
| `pipeline.py` | esecuzione comune a CLI e monitor |
| `reports/publication.py` | staging, manifest, hash, validazione, promozione e rollback |
| `docs/` | dashboard e pacchetto pubblico coerente |
| `cloudflare-worker/` | Telegram e API pubbliche; consuma il pacchetto, non ricalcola il modello |

## DAILY e LIVE PREVIEW

`DAILY` usa soltanto l'ultima candela Coinbase conclusa. `LIVE PREVIEW` aggiunge
una riga provvisoria con prezzo e volume 24h del medesimo mercato Coinbase.
Entrambi applicano le stesse regole, ma soltanto DAILY alimenta il backtest.

## Riproducibilita

Ogni run ha un `run_id`. `status.json`, `live-status.json`, `chart-data.json` e
`manifest.json` devono avere lo stesso identificativo. Il manifest registra il
periodo, la metodologia, le metriche e l'hash SHA-256 di ogni artefatto.
