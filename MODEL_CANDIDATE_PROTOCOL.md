# Protocollo di valutazione candidati BTC-USD Signal

Stato: preregistrato prima della prima valutazione dei segnali su ETH-USD.

Data del protocollo: 2026-07-27.

## Scopo

Confrontare due sole modifiche candidate con la baseline v1 congelata, senza
modificare segnali, dashboard o monitor operativi:

- `V1-S1`: vendita dopo una sola chiusura sotto SMA50;
- `V1-B1`: eliminazione della condizione volume dall'acquisto.

Le candidate sono nate da un'analisi esplorativa sullo storico BTC completo.
Pertanto nessun sottoperiodo BTC puo essere definito un vero out-of-sample. La
verifica BTC misura soltanto stabilita temporale. ETH-USD viene usato come
controllo cross-asset senza modificare soglie o regole.

## Regole confrontate

### Baseline v1

Acquisto con tutte vere:

1. Close sopra SMA200;
2. RSI14 maggiore o uguale a 40;
3. Close sopra quello di 7 giorni prima;
4. volume base sopra la media a 20 giorni.

Vendita dopo due Close consecutivi sotto SMA50.

### V1-S1

Stesso acquisto della baseline. Vendita dopo il primo Close sotto SMA50.

### V1-B1

Acquisto con trend, RSI e momentum; la condizione volume viene rimossa. Vendita
invariata dopo due Close consecutivi sotto SMA50.

Non verranno ottimizzate altre soglie dopo aver osservato ETH.

## Dati

- BTC-USD: snapshot congelato della baseline v1, cutoff 2026-07-26.
- ETH-USD: Coinbase `ONE_DAY`, cutoff comune 2026-07-26.
- UTC e sole candele concluse.
- ETH parte dal primo tratto giornaliero continuo, 2016-05-23. Le candele
  Coinbase 2016-05-21 e 2016-05-22 sono assenti e non vengono sintetizzate.
- Ogni asset usa il proprio warm-up SMA200, escluso dalla valutazione.
- Nessun dato Yahoo o conversione EUR entra nel test.

## Esecuzione

- Segnale calcolato alla chiusura `t`.
- Esposizione effettiva dal rendimento del giorno successivo.
- Esposizione 0% o 100%.
- `MANTIENI STATO ATTUALE` conserva l'esposizione.
- Vendita con precedenza sull'acquisto.
- Liquidita senza rendimento e tasso privo di rischio pari a zero.

## Costi

Scenari per ogni entrata e per ogni uscita:

- 0,00%;
- 0,10%;
- 0,25%;
- 0,40%;
- 0,60%.

Il costo primario e 0,60% per lato. Non viene presentato come tariffa personale
certa: Coinbase Advanced distingue maker e taker e aggiorna il livello in base
al volume degli ultimi 30 giorni. Lo scenario alto serve a evitare che una
strategia con piu rotazione sembri migliore solo perche il backtest e lordo.

Riferimento ufficiale:
https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees

## Metriche

Per ogni asset, variante e costo:

- rendimento totale e annualizzato;
- drawdown massimo;
- Sharpe annualizzato a 365 giorni;
- operazioni completate e win rate;
- tempo investito;
- numero di lati negoziati e costo cumulativo indicativo.

Il confronto usa anche blocchi temporali comuni con stato della posizione
conservato dalla serie completa:

- 2017-2018;
- 2019-2020;
- 2021-2022;
- 2023-2024;
- 2025-2026 fino al cutoff.

## Bootstrap

Per ogni candidato e asset si esegue un moving-block bootstrap accoppiato sulla
differenza dei rendimenti giornalieri netti rispetto alla baseline:

- costo 0,60% per lato;
- blocchi di 30 giorni;
- 5.000 campioni;
- seed deterministico `20260727`;
- intervallo al 90% della differenza media annualizzata;
- probabilita empirica che la differenza sia positiva.

Il bootstrap non elimina il selection bias originario, ma evita di interpretare
una piccola differenza di Sharpe come certezza.

## Criteri di promozione

Un candidato e indicato come `PROMUOVIBILE` soltanto se soddisfa tutti i criteri
al costo primario di 0,60% per lato:

1. Sharpe superiore alla baseline sia su BTC sia su ETH.
2. Drawdown non peggiore di oltre 2 punti percentuali su nessun asset.
3. Rendimento annualizzato non inferiore di oltre 5 punti percentuali su nessun
   asset.
4. Sharpe superiore alla baseline in almeno 6 dei 10 confronti asset/blocco.
5. Incremento dei lati negoziati non superiore al 50% su nessun asset.
6. Probabilita bootstrap di differenza media positiva almeno 90% su entrambi gli
   asset.

Un fallimento non significa che la variante sia inutile; significa che non c'e
evidenza sufficiente per sostituire la baseline v1.

## Vincoli decisionali

- La baseline v1 rimane immutabile qualunque sia il risultato.
- Nessuna combinazione `V1-S1 + V1-B1` viene promossa in questo esperimento.
- Non si modificano soglie dopo aver letto i risultati ETH.
- Un candidato promuovibile richiedera comunque paper trading prima di diventare
  una nuova baseline operativa.
- Un'eventuale nuova baseline avra nuovo nome, manifest e tag Git.

La selezione ripetuta di varianti sul medesimo storico puo gonfiare i risultati;
il problema e discusso in:

- https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
