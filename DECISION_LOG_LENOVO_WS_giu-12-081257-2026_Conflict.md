# Decision Log

Registro sintetico delle decisioni che influenzano segnali e metriche.

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
- la notifica collettiva al cambio segnale o rischio resta nella Fase 4.

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
