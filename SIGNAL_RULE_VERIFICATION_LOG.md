# Signal Rule Verification Log

Questo documento riepiloga le verifiche fatte sulle regole operative del
progetto BTC Signal Guard, incluse le ipotesi messe in dubbio, i test
comparativi e le decisioni finali adottate.

Il file serve come riferimento per futuri agenti IA o sviluppatori che vogliano
capire perche le regole attuali sono state scelte e come replicare le prove.

## Dataset e metodo

- Fonte dati: Yahoo Finance tramite `yfinance`.
- Serie principale: `BTC-USD`.
- Frequenza: candele giornaliere chiuse.
- Periodo usato in questa verifica: dal `2015-01-01` al `2026-06-20`.
- Calendario: crypto a 365 giorni annui.
- Backtest: il segnale calcolato sulla chiusura del giorno `t` viene applicato
  dal giorno successivo, per evitare look-ahead bias.
- Capitale di riferimento nelle tabelle: 1.000 unita monetarie.
- Costi non inclusi: commissioni, spread, slippage, tasse.

Comando di test generale:

```powershell
python -m unittest discover -s tests -v
```

## Regola finale attualmente implementata

### ACQUISTA

Il segnale `ACQUISTA` scatta solo se sono vere tutte queste condizioni:

1. Close sopra SMA200.
2. SMA50 sopra SMA200.
3. RSI(14) maggiore o uguale a 40.
4. Close sopra il Close di 7 giorni prima.
5. Volume giornaliero sopra la media volume a 20 giorni.

### VENDI

Il segnale `VENDI` scatta se:

1. il Close e sotto SMA50 per 2 giorni consecutivi.

### MANTIENI

Il segnale `MANTIENI` viene usato quando non scatta ne `ACQUISTA` ne `VENDI`.
Nel backtest significa: mantenere l'esposizione precedente.

## Verifica 1 - RSI 40-65 oppure RSI >= 40

Ipotesi iniziale: limitare l'acquisto a RSI tra 40 e 65 per evitare ingressi
quando Bitcoin e gia molto forte.

Dubbio emerso: un RSI sopra 65, se accompagnato dalle altre condizioni
rialziste, puo comunque indicare forza e non necessariamente un ingresso
sbagliato.

Risultato del confronto con la vecchia vendita a 5 condizioni:

| Scenario | Rendimento totale | Annualizzato | Max drawdown | Operazioni | Win rate | Sharpe | Giorni ACQUISTA | Giorni VENDI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RSI 40-65 + VENDI 5 condizioni | +11.335,95% | +51,16% | -67,20% | 7 | 71,43% | 1,055 | 275 | 80 |
| RSI >= 40 + VENDI 5 condizioni | +16.899,50% | +56,47% | -67,20% | 7 | 71,43% | 1,110 | 693 | 80 |

Decisione: rimuovere il tetto massimo a 65 e usare `RSI >= 40`.

Motivo: il tetto a 65 tagliava molti giorni di trend positivo senza ridurre il
drawdown massimo nel confronto specifico. La regola finale mantiene la soglia
minima, ma non penalizza la forza del trend.

## Verifica 2 - Condizione volume uguale per acquisto e vendita

Domanda: perche la condizione volume era uguale sia per `ACQUISTA` sia per
`VENDI`?

Valutazione:

- Il volume sopra la media a 20 giorni non ha direzione propria.
- Conferma solo che il movimento e accompagnato da partecipazione superiore
  alla media.
- Per l'acquisto conferma forza del trend rialzista.
- Per la vendita, nella vecchia struttura, confermava che la rottura ribassista
  non era avvenuta con volume debole.

Decisione: nella strategia finale la condizione volume resta solo dentro le 5
condizioni di acquisto. La vendita non usa piu le vecchie 5 condizioni.

## Verifica 3 - Vecchie 5 condizioni di vendita

Vecchia ipotesi `VENDI`:

1. Close sotto SMA200.
2. SMA50 sotto SMA200.
3. RSI sotto 35.
4. Close sotto quello di 7 giorni prima.
5. Volume sopra media 20 giorni.

Problema: queste condizioni sono molto lente. Tendono a confermare una fase
ribassista quando una parte rilevante del drawdown e gia avvenuta.

Confronto chiave:

| Scenario | Rendimento totale | Annualizzato | Max drawdown | Operazioni | Win rate | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| RSI >= 40 + VENDI 5 condizioni | +16.899,50% | +56,47% | -67,20% | 7 | 71,43% | 1,110 |
| RSI >= 40 + VENDI sotto SMA50 1 giorno | +32.406,90% | +65,57% | -41,07% | 42 | 45,24% | 1,413 |
| RSI >= 40 + VENDI sotto SMA50 2 giorni | +42.475,12% | +69,51% | -42,06% | 35 | 51,43% | 1,450 |

Decisione: eliminare le vecchie 5 condizioni di vendita dal modello operativo.

Motivo: la vendita sotto SMA50 protegge prima il capitale e, nel periodo
testato, migliora rendimento, drawdown e Sharpe rispetto alla vecchia vendita
a 5 condizioni.

## Verifica 4 - Una vendita con SMA50 va in conflitto con le 5 condizioni?

Dubbio: se il prezzo chiude sotto SMA50, spesso la SMA50 puo essere ancora sopra
SMA200. In quei casi il modello vende anche se il trend lungo non e ancora
ribassista.

Valutazione:

- Non e un conflitto logico, perche la regola sotto SMA50 e una regola di
  uscita protettiva, non una diagnosi completa di bear market.
- Serve a ridurre esposizione quando il prezzo perde la media veloce.
- Le vecchie 5 condizioni identificavano una debolezza piu profonda, ma piu
  tardiva.

Verifica di ridondanza:

- Vecchie vendite a 5 condizioni rilevate: 80 giorni.
- Vecchie vendite senza Close sotto SMA50 nello stesso giorno: 0 giorni.
- Vecchie vendite senza Close sotto SMA50 per 2 giorni consecutivi: 1 giorno.

Conclusione: le vecchie 5 condizioni erano quasi sempre gia incluse dentro una
situazione di prezzo sotto SMA50. Tenerle insieme alla vendita SMA50 avrebbe
aggiunto poca informazione pratica.

## Verifica 5 - VENDI sotto SMA50: 1 giorno oppure 2 giorni consecutivi

Ipotesi testate:

- Vendere al primo Close sotto SMA50.
- Vendere solo dopo 2 Close consecutivi sotto SMA50.

Risultati:

| Scenario | Rendimento totale | Annualizzato | Max drawdown | Operazioni | Win rate | Sharpe | Giorni VENDI |
|---|---:|---:|---:|---:|---:|---:|---:|
| RSI >= 40 + VENDI sotto SMA50 1 giorno | +32.406,90% | +65,57% | -41,07% | 42 | 45,24% | 1,413 | 1.777 |
| RSI >= 40 + VENDI sotto SMA50 2 giorni | +42.475,12% | +69,51% | -42,06% | 35 | 51,43% | 1,450 | 1.671 |

Decisione: usare 2 giorni consecutivi.

Motivo: nel periodo testato il filtro a 2 giorni riduce il numero di operazioni,
migliora rendimento totale, rendimento annualizzato, win rate e Sharpe. Accetta
un drawdown massimo leggermente peggiore rispetto alla versione a 1 giorno, ma
con un profilo complessivo migliore.

## Verifica 6 - Cosa succede dopo un segnale VENDI

Domanda: dopo il segnale `VENDI`, il prezzo continua a scendere oppure risale
facendo scattare di nuovo le condizioni di acquisto?

Verifica sulla regola finale:

- Eventi di uscita `VENDI` distinti: 82.
- Eventi seguiti da un successivo `ACQUISTA`: 75.
- Eventi senza successivo `ACQUISTA` entro la fine del dataset: 7.
- Drawdown medio successivo all'uscita prima del nuovo acquisto o fine periodo:
  -21,02%.
- Drawdown mediano successivo: -11,13%.
- Peggior discesa evitata dopo una uscita: -72,84%.

Conclusione: molte uscite vengono poi seguite da un nuovo ingresso, quindi il
modello non "abbandona" il mercato in modo definitivo. La funzione principale
della vendita e stare fuori durante fasi in cui, storicamente, dopo la rottura
della SMA50 potevano arrivare ulteriori ribassi rilevanti.

## Verifica 7 - SMA40, SMA50 o SMA60 per la vendita

Ipotesi: cambiare la media mobile di uscita per rendere il modello piu reattivo
o piu lento.

Risultati con `RSI >= 40` in acquisto e vendita dopo 2 giorni consecutivi sotto
la media scelta:

| Scenario | Rendimento totale | Annualizzato | Max drawdown | Operazioni | Win rate | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| VENDI sotto SMA40 per 2 giorni | +29.322,93% | +64,14% | -47,72% | 42 | 47,62% | 1,393 |
| VENDI sotto SMA50 per 2 giorni | +42.475,12% | +69,51% | -42,06% | 35 | 51,43% | 1,450 |
| VENDI sotto SMA60 per 2 giorni | +28.101,71% | +63,53% | -45,29% | 33 | 51,52% | 1,356 |

Decisione: mantenere SMA50.

Motivo: nel periodo testato la SMA50 a 2 giorni consecutivi ha dato il migliore
equilibrio tra rendimento, drawdown, numero operazioni e Sharpe.

## Verifica 8 - Momentum di acquisto: 7 giorni, 6 giorni, 14 giorni o media 7

Regola finale attuale:

- Close di oggi sopra il Close di 7 giorni prima.

Ipotesi testate:

- 6 giorni: ingresso leggermente piu reattivo.
- 14 giorni: ingresso piu lento e piu selettivo.
- Close sopra la media dei Close degli ultimi 7 giorni.

Risultati con vendita finale sotto SMA50 per 2 giorni:

| Scenario | Rendimento totale | Annualizzato | Max drawdown | Operazioni | Win rate | Sharpe | Giorni ACQUISTA |
|---|---:|---:|---:|---:|---:|---:|---:|
| Close > Close 6 giorni fa | +36.658,01% | +67,35% | -48,50% | 35 | 51,43% | 1,422 | 686 |
| Close > Close 7 giorni fa | +42.475,12% | +69,51% | -42,06% | 35 | 51,43% | 1,450 | 693 |
| Close > Close 14 giorni fa | +31.863,01% | +65,33% | -45,67% | 37 | 48,65% | 1,393 | 764 |
| Close > media Close 7 giorni | +39.421,28% | +68,41% | -47,41% | 35 | 54,29% | 1,436 | 648 |

Decisione: mantenere 7 giorni.

Motivo: nel confronto specifico, 7 giorni ha dato il rendimento totale piu alto,
il miglior drawdown massimo e il miglior Sharpe. La media a 7 giorni ha
migliorato il win rate, ma ha peggiorato rendimento e drawdown rispetto alla
regola attuale.

## Verifica 9 - Confronto con Buy & Hold

Sul periodo completo del dataset:

| Strategia | Capitale finale da 1.000 | Rendimento totale | Annualizzato | Max drawdown | Sharpe |
|---|---:|---:|---:|---:|---:|
| BTC Signal Guard finale | 425.751,21 | +42.475,12% | +69,51% | -42,06% | 1,450 |
| Buy & Hold Bitcoin | 202.898,12 | +20.189,81% | +58,90% | -83,40% | 1,031 |

Su finestre piu recenti il confronto puo cambiare:

| Periodo | Strategia | Capitale finale da 1.000 | Rendimento | Max drawdown | Sharpe |
|---|---|---:|---:|---:|---:|
| 2022-01-01 / 2026-06-20 | BTC Signal Guard | 2.017,92 | +101,79% | -27,66% | 0,724 |
| 2022-01-01 / 2026-06-20 | Buy & Hold | 1.337,07 | +33,71% | -66,89% | 0,384 |
| 2024-01-01 / 2026-06-20 | BTC Signal Guard | 1.425,60 | +42,56% | -27,66% | 0,632 |
| 2024-01-01 / 2026-06-20 | Buy & Hold | 1.443,61 | +44,36% | -51,21% | 0,548 |

Interpretazione:

- Su alcuni periodi il sistema puo rendere meno del Buy & Hold.
- La sua funzione non e prevedere ogni massimo rendimento possibile, ma ridurre
  l'esposizione nelle fasi tecnicamente deboli.
- Il vantaggio principale tende a emergere nelle fasi con drawdown profondi.
- In trend rialzisti rapidi e continui il Buy & Hold puo temporaneamente fare
  meglio perche resta sempre esposto.

## Decisione finale operativa

La strategia implementata nel progetto resta:

- `ACQUISTA` con le 5 condizioni rialziste complete.
- RSI di acquisto `>= 40`, senza tetto massimo a 65.
- `VENDI` se il prezzo chiude sotto SMA50 per 2 giorni consecutivi.
- Nessuna vecchia condizione multipla di vendita.
- Notifiche automatiche Telegram solo quando cambia il segnale o cambia lo
  stato delle condizioni; `/segnale` resta sempre disponibile su richiesta.

Questa configurazione e stata scelta perche, nei test storici effettuati, ha
offerto il miglior equilibrio tra rendimento, controllo del drawdown, numero di
operazioni e leggibilita operativa.

## Note per replica tecnica

Per replicare il test:

1. Installare le dipendenze.

```powershell
pip install -r requirements.txt
```

2. Eseguire la pipeline standard.

```powershell
python main.py --force-download
```

3. Verificare i test automatici.

```powershell
python -m unittest discover -s tests -v
```

4. Per varianti sperimentali, modificare temporaneamente:

- `strategy/signals.py` per la logica `ACQUISTA` / `VENDI`;
- `config.py` per `momentum_days`;
- `indicators/technical_indicators.py` se servono nuove medie mobili;
- `backtest/backtest.py` solo se cambia il metodo di simulazione.

Non modificare il motore di backtest quando si vogliono confrontare regole di
segnale: altrimenti il confronto non resta omogeneo.
