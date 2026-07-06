# Decision Log

Registro sintetico delle decisioni che influenzano segnali e metriche.

## 2026-07-06 - Deduplica notifiche Telegram su chiave condizioni

**Decisione:** le notifiche automatiche `DAILY` partono solo quando cambia la
chiave condizioni `BUY:xxxx|SELL:x`.

**Motivazione:** l'utente deve ricevere un nuovo messaggio solo quando cambia
almeno una delle 4 condizioni di acquisto o l'unica condizione di vendita. Se
la chiave resta uguale per piu giorni, l'ultimo messaggio Telegram rimane lo
stato valido; l'utente puo comunque interrogare il bot con `/segnale`.

**Impatto:**

- primo stato senza chiave precedente: invia la prima notifica;
- `BUY:1111|SELL:0` ripetuto: nessun nuovo invio;
- `BUY:1111|SELL:0` -> `BUY:1101|SELL:0`: invia `MANTIENI`;
- `BUY:1101|SELL:0` ripetuto: nessun nuovo invio;
- `BUY:1101|SELL:0` -> `BUY:0000|SELL:1`: invia `VENDI`;
- il workflow manuale `workflow_dispatch` e il comando `/segnale` restano
  richieste esplicite e rispondono sempre.

## 2026-07-04 - Rimozione Golden Cross dalla baseline

**Decisione:** rimuovere `SMA50 > SMA200` dalle condizioni operative di
acquisto della baseline.

**Nuova regola `ACQUISTA`:**

1. Close sopra SMA200.
2. RSI(14) maggiore o uguale a 40.
3. Close sopra il Close di 7 giorni prima.
4. Volume giornaliero sopra la media volume a 20 giorni.

La regola `VENDI` resta invariata: Close sotto SMA50 per 2 giorni consecutivi.

**Test effettuati:**

- confronto full period `2015-01-01 / 2026-07-03`;
- confronto periodo recente `2022-01-01 / 2026-07-03`;
- sensibilita ai costi da 5 a 200 bps per cambio esposizione;
- sensibilita alla data di partenza dal 2015 al 2025;
- finestre rolling a 1, 2, 3, 4 e 5 anni;
- attribuzione degli ingressi anticipati generati dalla rimozione del vincolo.

**Risultati principali:**

| Strategia | Periodo | Rendimento | Max DD | Sharpe | Operazioni |
|---|---|---:|---:|---:|---:|
| Baseline con Golden Cross | 2015-2026 | +42.475,1% | -42,06% | 1,448 | 35 |
| Senza Golden Cross | 2015-2026 | +76.073,6% | -48,77% | 1,519 | 40 |
| Baseline con Golden Cross | 2022-2026 | +101,8% | -27,66% | 0,720 | 16 |
| Senza Golden Cross | 2022-2026 | +215,6% | -29,76% | 1,039 | 18 |

**Candidata non implementata:** `No Golden Cross + SMA50 rising 7d`.

Questa variante richiede che la SMA50 sia superiore al valore di 7 giorni
prima. Sul periodo completo ha prodotto +66.937,3%, max drawdown -42,25%,
Sharpe 1,517, 31 operazioni e win rate 61,3%.

**Motivo del rinvio:** e la migliore candidata prudenziale se in futuro si
volesse ridurre il drawdown, ma non viene promossa ora per mantenere la
baseline piu semplice e per catturare interamente il vantaggio storico
dell'ingresso anticipato senza Golden Cross.

## 2026-06-11 - Iscrizione visibile nella dashboard

**Decisione:** aggiungere alla dashboard pubblica una card Telegram con deep
link e numero aggregato degli iscritti attivi.

**Impatto:**

- il link pubblico usa `@BTC_Prudential_Signal_bot`;
- `/start iscrivimi` viene trattato come `/iscrivimi`;
- `GET /subscribers/count` conta server-side soltanto le righe attive;
- nessun dato personale viene restituito dal nuovo endpoint;
- la dashboard mostra un fallback neutro se Render non risponde;
- CORS accetta soltanto GitHub Pages e gli indirizzi locali di sviluppo;
- nessun secret Supabase o Telegram e presente nel frontend.

## 2026-06-10 - Iscrizioni Telegram persistenti

**Decisione:** consentire l'uso del bot in ogni chat privata e memorizzare le
iscrizioni in Supabase.

**Impatto:**

- `/iscrivimi` crea o riattiva l'iscrizione senza duplicati;
- `/disiscrivimi` disattiva gli invii senza cancellare la registrazione;
- `/privacy` descrive i dati conservati;
- gruppi e supergruppi vengono ignorati;
- il numero di cellulare non viene richiesto;
- la service role resta nelle variabili protette del backend;
- la notifica collettiva verra rifinita nella Fase 4; la regola corrente e
  deduplicare sulla chiave condizioni `BUY:xxxx|SELL:x`.

## 2026-06-09 - Webhook Render attivato

**Stato:** operativo e verificato.

**Configurazione:**

- servizio pubblico:
  `https://btc-prudential-signal.onrender.com`;
- endpoint Telegram:
  `https://btc-prudential-signal.onrender.com/webhook`;
- health check verificato con `{"status":"ok"}`;
- registrazione Telegram verificata tramite `getWebhookInfo`;
- `/segnale` verificato con risposta immediata.

**Decisione operativa:**

- mantenere attivo `Hourly BTC monitor (Telegram)`;
- mantenere disabilitato `Telegram command listener`;
- usare il listener `getUpdates` soltanto come fallback dopo aver eseguito
  `deleteWebhook`.

## 2026-06-09 - Webhook Telegram FastAPI

**Decisione:** aggiungere un servizio FastAPI separato, distribuibile su
Render, per ricevere direttamente gli update Telegram.

**Motivazione:** eliminare la latenza dello scheduler GitHub Actions senza
spostare o modificare il calcolo dei segnali.

**Impatto:**

- `POST /webhook` gestisce `/segnale`, `/start` e `/help`;
- ogni `/segnale` scarica il JSON dal GitHub Raw URL pubblico;
- nessun database, copia locale o autenticazione GitHub;
- accesso limitato a `TELEGRAM_CHAT_ID`;
- supporto opzionale a `TELEGRAM_WEBHOOK_SECRET`;
- il listener `getUpdates` resta come fallback, ma deve essere disabilitato
  mentre il webhook e registrato.

## 2026-06-09 - Comando Telegram `/segnale`

**Decisione:** aggiungere un listener GitHub Actions separato che controlla
Telegram ogni 5 minuti.

**Motivazione:** permettere la richiesta manuale del segnale direttamente
dalla chat senza avviare il workflow dal sito GitHub.

**Impatto:**

- `/segnale` restituisce segnale, rischio, prezzo EUR live e indicazione;
- `/start` e `/help` mostrano il comando disponibile;
- rispondono soltanto i messaggi provenienti da `TELEGRAM_CHAT_ID`;
- la risposta puo essere ritardata dallo scheduler GitHub Actions;
- non e richiesto un server esterno sempre attivo.

## 2026-06-09 - Notifica Telegram essenziale

**Decisione:** mostrare nella notifica soltanto il prezzo BTC in euro ed
eliminare la sezione `Sintesi`.

**Motivazione:** il doppio prezzo e il riepilogo tecnico rendevano il messaggio
meno immediato.

**Impatto:**

- nessun prezzo USD nel messaggio Telegram;
- restano segnale, rischio, prezzo EUR e indicazione;
- il prezzo storico `BTC-EUR` viene usato se Coinbase non e disponibile.
- l'avvio manuale del workflow invia lo stesso formato dei cambi di segnale,
  senza aggiornare lo stato delle notifiche automatiche.

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
