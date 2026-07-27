# Valutazione candidati BTC-USD Signal

Cutoff comune: `2026-07-26`. Costo primario: `0.60%` per lato.
Commit sorgente: `f82ead5c7d581206966f5b927338a1c51c88e11a`.

La baseline operativa non e stata modificata. I candidati sono valutati secondo
`MODEL_CANDIDATE_PROTOCOL.md` e usano esclusivamente BTC-USD.

## Decisione

| Candidato | Esito | Fold Sharpe vinti | Probabilita bootstrap |
|---|---|---:|---:|
| V1-S1 | NON PROMUOVIBILE | 4/5 | 49,30% |
| V1-B1 | NON PROMUOVIBILE | 2/5 | 65,96% |

## Risultati al costo primario

| Asset | Variante | Rendimento | Annualizzato | Drawdown | Sharpe | Operazioni | Lati |
|---|---|---:|---:|---:|---:|---:|---:|
| BTC-USD | BASELINE | 23.498,85% | 68,44% | -51,59% | 1,391 | 37 | 74 |
| BTC-USD | V1-B1 | 25.096,80% | 69,49% | -51,79% | 1,393 | 41 | 82 |
| BTC-USD | V1-S1 | 23.737,16% | 68,60% | -49,76% | 1,409 | 43 | 86 |

## Criteri

### V1-S1: NON PROMUOVIBILE

- [x] `sharpe_improves`
- [x] `drawdown_within_2pp`
- [x] `annualized_return_within_5pp`
- [x] `turnover_increase_within_50pct`
- [x] `at_least_3_of_5_fold_sharpe_wins`
- [ ] `bootstrap_probability_at_least_90pct`

### V1-B1: NON PROMUOVIBILE

- [x] `sharpe_improves`
- [x] `drawdown_within_2pp`
- [x] `annualized_return_within_5pp`
- [x] `turnover_increase_within_50pct`
- [ ] `at_least_3_of_5_fold_sharpe_wins`
- [ ] `bootstrap_probability_at_least_90pct`

## Periodi

| Asset | Storico | Valutazione | Osservazioni valutate |
|---|---|---|---:|
| BTC-USD | 2015-07-20 / 2026-07-26 | 2016-02-04 / 2026-07-26 | 3826 |

## Interpretazione corretta

I candidati sono stati scelti dopo aver osservato l'intero storico BTC. I risultati
non sono quindi out-of-sample. I blocchi e il bootstrap misurano stabilita interna,
ma non correggono interamente selection bias e cambi di regime. Nessun dato o
progetto ETH-USD e stato usato in questa valutazione.

Le commissioni Coinbase effettive dipendono da maker/taker e volume personale.
Gli scenari sono stress test, non un preventivo di costo. Slippage, spread, imposte
e rendimento della liquidita restano esclusi.

Riferimenti:

- https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees
- https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
