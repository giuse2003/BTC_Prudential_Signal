# Protocollo di valutazione candidati BTC-USD Signal

Versione aggiornata il 2026-07-27 su richiesta dell'utente: l'esperimento usa
esclusivamente BTC-USD e non accede, modifica o valuta il progetto ETH-USD.

## Scopo

Confrontare due sole modifiche candidate con la baseline v1 congelata, senza
modificare segnali, dashboard o monitor operativi:

- `V1-S1`: vendita dopo una sola chiusura sotto SMA50;
- `V1-B1`: eliminazione della condizione volume dall'acquisto.

Le candidate sono nate da un'analisi esplorativa sullo storico BTC completo.
Pertanto nessun sottoperiodo disponibile puo essere definito un vero
out-of-sample. I blocchi temporali e il bootstrap misurano stabilita interna,
non rendimento futuro.

## Regole confrontate

### Baseline v1

Acquisto con tutte vere:

1. Close sopra SMA200;
2. RSI14 maggiore o uguale a 40;
3. Close sopra quello di 7 giorni prima;
4. volume BTC-USD sopra la media a 20 giorni.

Vendita dopo due Close consecutivi sotto SMA50.

### V1-S1

Stesso acquisto della baseline. Vendita dopo il primo Close sotto SMA50.

### V1-B1

Acquisto con trend, RSI e momentum; la condizione volume viene rimossa. Vendita
invariata dopo due Close consecutivi sotto SMA50.

Non vengono valutate combinazioni delle due modifiche o altre soglie.

## Dati

- Unico input: snapshot Coinbase `BTC-USD` della baseline v1.
- Storico congelato dal 2015-07-20 al 2026-07-26.
- UTC e sole candele concluse.
- Warm-up SMA200 escluso dalla valutazione.
- Periodo valutato dal 2016-02-04 al 2026-07-26.
- Nessun dato ETH, Yahoo o BTC-EUR entra nel test.

## Esecuzione

- Segnale calcolato sull'intera storia, incluso il warm-up necessario a valutare
  correttamente la persistenza della vendita al primo giorno utile.
- Warm-up rimosso soltanto dopo il calcolo dei segnali.
- Segnale della chiusura `t` applicato dal rendimento del giorno successivo.
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

Per ogni variante e costo:

- rendimento totale e annualizzato;
- drawdown massimo;
- Sharpe annualizzato a 365 giorni;
- operazioni completate e win rate;
- tempo investito;
- numero di lati negoziati.

Il confronto usa anche blocchi temporali con stato della posizione conservato
dalla serie completa:

- 2017-2018;
- 2019-2020;
- 2021-2022;
- 2023-2024;
- 2025-2026 fino al cutoff.

## Bootstrap

Per ogni candidato si esegue un moving-block bootstrap accoppiato sulla
differenza dei rendimenti giornalieri netti rispetto alla baseline:

- costo 0,60% per lato;
- blocchi di 30 giorni;
- 5.000 campioni;
- seed deterministico `20260727`;
- intervallo al 90% della differenza media annualizzata;
- probabilita empirica che la differenza sia positiva.

Il bootstrap non elimina il selection bias originario, ma evita di interpretare
una piccola differenza come certezza.

## Criteri di promozione

Un candidato e indicato come `PROMUOVIBILE` soltanto se soddisfa tutti i criteri
al costo primario di 0,60% per lato:

1. Sharpe superiore alla baseline.
2. Drawdown non peggiore di oltre 2 punti percentuali.
3. Rendimento annualizzato non inferiore di oltre 5 punti percentuali.
4. Sharpe superiore alla baseline in almeno 3 dei 5 blocchi temporali.
5. Incremento dei lati negoziati non superiore al 50%.
6. Probabilita bootstrap di differenza media positiva almeno 90%.

Un fallimento non significa che la variante sia inutile; significa che lo
storico BTC disponibile non fornisce evidenza sufficiente per sostituire la
baseline v1.

## Vincoli decisionali

- La baseline v1 rimane immutabile qualunque sia il risultato.
- Nessun file o dato ETH viene usato.
- Nessuna combinazione `V1-S1 + V1-B1` viene promossa.
- Non si modificano soglie dopo aver letto i risultati.
- Un candidato promuovibile richiedera comunque paper trading su nuovi dati
  prima di diventare una nuova baseline operativa.
- Un'eventuale nuova baseline avra nuovo nome, manifest e tag Git.

La selezione ripetuta di varianti sul medesimo storico puo gonfiare i risultati;
il problema e discusso in:

- https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
