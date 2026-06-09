# Decision Log

Registro sintetico delle decisioni che influenzano segnali e metriche.

## 2026-06-09 - Notifica Telegram essenziale

**Decisione:** mostrare nella notifica soltanto il prezzo BTC in euro ed
eliminare la sezione `Sintesi`.

**Motivazione:** il doppio prezzo e il riepilogo tecnico rendevano il messaggio
meno immediato.

**Impatto:**

- nessun prezzo USD nel messaggio Telegram;
- restano segnale, rischio, prezzo EUR e indicazione;
- il prezzo storico `BTC-EUR` viene usato se Coinbase non e disponibile.

## 2026-06-08 - Calendario crypto a 365 giorni

**Decisione:** usare `365` periodi annui per Bitcoin.

**Motivazione:** Bitcoin viene negoziato tutti i giorni; il calendario
tradizionale da 252 sedute sottostima la finestra annuale e altera rendimento
annualizzato e Sharpe Ratio.

**Impatto:**

- `CFG.periods_per_year = 365`;
- finestra 52 settimane pari a 365 osservazioni;
- annualizzazione e Sharpe basati su 365 periodi.

## 2026-06-08 - Segnali solo su candele concluse

**Decisione:** escludere sempre la candela giornaliera UTC corrente.

**Motivazione:** durante il giorno prezzo, volume e indicatori della candela
sono incompleti e possono produrre cambi di segnale non confermati.

**Impatto:**

- funzione condivisa `keep_closed_daily_candles`;
- comportamento coerente tra analisi locale e monitor GitHub Actions;
- prezzo spot Coinbase resta live, ma non entra nel calcolo del segnale
  giornaliero.

## 2026-06-08 - Operazione definita come trade chiuso

**Decisione:** contare come operazione soltanto una sequenza completa di
entrata long e successiva uscita.

**Motivazione:** contare ogni variazione di esposizione mescolava ingressi e
uscite, producendo un denominatore incoerente per il win rate.

**Impatto:**

- `num_operations` rappresenta i trade completati;
- `win_rate` e il rapporto tra trade chiusi positivi e trade chiusi totali;
- una posizione aperta a fine backtest resta esclusa da entrambe le metriche.

## Decisioni rinviate

- Costi di transazione, spread e slippage.
- Versionamento bloccato delle dipendenze.
- Revisione generale di manutenibilita, workflow e duplicazione frontend.
