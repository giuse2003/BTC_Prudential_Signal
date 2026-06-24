# BTC Signal Guard - Sell Rule Experiments

Ultimo aggiornamento: 2026-06-24

Questo file documenta le prove fatte sulle regole di vendita di BTC Signal Guard.
L'obiettivo e ridurre il drawdown nei crolli senza sacrificare troppo rendimento,
Sharpe Ratio e leggibilita operativa.

## Baseline ufficiale

La regola attuale di vendita e:

```text
VENDI se Close < SMA50 per 2 giorni consecutivi
```

La regola di acquisto non e stata modificata negli esperimenti:

```text
ACQUISTA se:
- Close > SMA200
- SMA50 > SMA200
- RSI >= 40
- Close > Close di 7 giorni prima
- Volume > VolumeAvg20
```

Tutti i test usano il motore `backtest.run_backtest`, con esposizione applicata
dal giorno successivo al segnale, come nella strategia ufficiale.

## File di lavoro

- Script esperimenti: `scripts/experiment_sell_rules.py`
- Risultati principali: `outputs/sell_rule_experiments/sell_rule_metrics.csv`
- Conteggi segnali: `outputs/sell_rule_experiments/sell_rule_signal_counts.csv`
- Griglia parametri: `outputs/sell_rule_experiments/parameter_grid_metrics.csv`
- Uscite condizionali veloci: `outputs/sell_rule_experiments/conditional_fast_exit_metrics.csv`
- Test RSI 40: `outputs/sell_rule_experiments/sma50_rsi40_test.csv`
- Test SMA60: `outputs/sell_rule_experiments/sma50_sma60_2d_test.csv`
- Test SMA70: `outputs/sell_rule_experiments/sma50_sma70_2d_test.csv`
- Test SMA80/SMA90: `outputs/sell_rule_experiments/sma50_sma80_sma90_2d_test.csv`

## Risultati periodo completo 2015-2026

| Regola di vendita | Rendimento totale | Max drawdown | Sharpe | Operazioni | Win rate | Note |
|---|---:|---:|---:|---:|---:|---|
| SMA50 2d baseline | +42.475% | -42,06% | 1,450 | 35 | 51,4% | Regola ufficiale attuale |
| SMA50 1d | +32.407% | -41,07% | 1,413 | 42 | 45,2% | Piu reattiva, ma costa troppo rendimento |
| SMA50 3d | +36.733% | -40,85% | 1,408 | 33 | 54,5% | Migliora poco il drawdown, perde rendimento |
| SMA50 2d oppure SMA50 + RSI < 40 | +30.984% | -42,06% | 1,392 | 36 | 52,8% | Non riduce il drawdown complessivo |
| SMA50 2d oppure SMA50 + RSI < 50 | +38.584% | -41,07% | 1,447 | 39 | 48,7% | Migliora leggermente il drawdown, Sharpe quasi invariato |
| SMA50 2d oppure SMA60 2d | +38.672% | -40,55% | 1,437 | 36 | 50,0% | Migliora bene il 2018, peggiora il recente |
| SMA50 2d oppure SMA70 2d | +38.979% | -38,89% | 1,440 | 36 | 50,0% | Miglior drawdown tra le candidate medie mobili |
| SMA50 2d oppure SMA80 2d | +38.768% | -38,89% | 1,439 | 36 | 50,0% | Simile a SMA70, leggermente peggiore |
| SMA50 2d oppure SMA90 2d | +44.618% | -40,55% | 1,466 | 38 | 47,4% | Miglior compromesso complessivo visto finora |

## Lettura per periodi critici

### 2018 bear market

Le varianti SMA60/SMA70/SMA80/SMA90 a 2 giorni migliorano molto il 2018:

| Regola | Rendimento 2018 | Max drawdown 2018 |
|---|---:|---:|
| Baseline SMA50 2d | -24,05% | -32,40% |
| SMA50 2d oppure SMA60/70/80/90 2d | -10,38% | -23,51% |

### 2022 e 2026

Nel 2022 e nel 2026 disponibile, la strategia rimane gia fuori mercato con la
baseline. Le varianti non cambiano il risultato:

```text
BTC Signal Guard: 0,00%
Buy & Hold 2022: circa -64%
Buy & Hold 2026 YTD: circa -28%
```

### 2024-2026 recente

Il periodo recente penalizza le varianti SMA60/SMA70/SMA80/SMA90:

| Regola | Rendimento 2024-2026 | Max drawdown 2024-2026 |
|---|---:|---:|
| Baseline SMA50 2d | +42,56% | -27,66% |
| SMA50 2d oppure SMA60 2d | +36,71% | -27,66% |
| SMA50 2d oppure SMA70 2d | +32,68% | -28,66% |
| SMA50 2d oppure SMA80 2d | +34,32% | -29,12% |
| SMA50 2d oppure SMA90 2d | +34,32% | -29,12% |

## Raccomandazione corrente

La candidata piu interessante al 2026-06-24 e:

```text
VENDI se Close < SMA50 per 2 giorni consecutivi
oppure Close < SMA90 per 2 giorni consecutivi
```

Motivo:

- rendimento totale migliore della baseline;
- Sharpe Ratio migliore della baseline;
- max drawdown migliore della baseline;
- migliora molto il 2018.

Rischio:

- peggiora il periodo recente 2024-2026;
- aumenta leggermente il numero di operazioni;
- win rate inferiore alla baseline.

Prima di promuoverla a regola ufficiale, conviene testare:

- SMA85, SMA90, SMA95, SMA100;
- soglie diverse per conferma, ad esempio 3 giorni su SMA90;
- una variante stagionale o regime-based, dove la regola SMA90 si attiva solo
  quando il trend lungo e fragile.

## Come continuare i test

Eseguire:

```powershell
python scripts\experiment_sell_rules.py
```

Per aggiungere nuove varianti, modificare la lista `VARIANTS` e la funzione
`sell_condition` in `scripts/experiment_sell_rules.py`, poi rieseguire lo
script e confrontare i nuovi CSV in `outputs/sell_rule_experiments`.
