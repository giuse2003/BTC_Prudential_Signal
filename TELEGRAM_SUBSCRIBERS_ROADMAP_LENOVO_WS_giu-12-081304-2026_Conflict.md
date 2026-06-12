# Telegram Subscribers Roadmap

Ultimo aggiornamento: 11 giugno 2026

Stato generale: `FASE 3 COMPLETATA - FASE 4 DA IMPLEMENTARE`

## Obiettivo

Permettere ai visitatori della dashboard pubblica di iscriversi alle notifiche
Telegram del progetto senza comunicare manualmente numero di telefono o user ID.

Flusso previsto:

```text
Dashboard GitHub Pages
        |
        v
Pulsante "Ricevi segnali su Telegram"
        |
        v
Bot Telegram
        |
        v
/iscrivimi oppure /disiscrivimi
        |
        v
Database Supabase
        |
        v
Notifica agli iscritti solo quando cambia segnale o rischio
```

## Decisioni gia prese

- Il numero di cellulare non verra richiesto.
- Il Telegram user ID non verra inserito manualmente nella dashboard.
- L'utente dovra aprire volontariamente il bot e interagire con esso.
- Il comando di iscrizione sara `/iscrivimi`.
- Il comando di revoca sara `/disiscrivimi`.
- `/segnale` continuera a mostrare il segnale corrente.
- Le notifiche collettive partiranno solo al cambio di segnale o rischio.
- Non verra inviato un messaggio collettivo ogni ora senza variazioni.
- Il database persistente previsto e Supabase.
- `TELEGRAM_CHAT_ID` attuale identifica l'amministratore, non l'elenco degli
  iscritti.
- Token, password e chiavi non verranno salvati nel repository.

## Responsabilita

### Attivita dell'utente

- Creare o configurare il progetto Supabase.
- Eseguire lo script SQL fornito nel pannello Supabase.
- Recuperare le credenziali Supabase senza condividerle in chat.
- Inserire le variabili protette su Render.
- Inserire i secret richiesti su GitHub Actions.
- Eseguire le prove Telegram finali dal proprio account.

### Attivita di Codex

- Progettare tabella e policy del database.
- Preparare lo script SQL.
- Implementare `/iscrivimi`, `/disiscrivimi`, `/start`, `/privacy` e
  aggiornare `/segnale`.
- Implementare il repository degli iscritti.
- Aggiungere il pulsante alla dashboard.
- Modificare l'invio automatico al cambio di segnale o rischio.
- Gestire utenti che bloccano il bot o chat non piu raggiungibili.
- Aggiungere test automatici.
- Aggiornare documentazione, file di contesto e questa roadmap.
- Eseguire commit e push su GitHub.

## Checklist operativa

### Fase 1 - Supabase

- [x] **1.1 Utente:** creare un account o accedere a Supabase.
- [x] **1.2 Utente:** creare un nuovo progetto Supabase.
- [x] **1.3 Codex:** definire schema, vincoli e policy della tabella iscritti.
- [x] **1.4 Codex:** preparare lo script SQL completo.
- [x] **1.5 Utente:** eseguire lo script nell'SQL Editor Supabase.
- [x] **1.6 Utente:** recuperare `SUPABASE_URL`.
- [x] **1.7 Utente:** recuperare `SUPABASE_SERVICE_ROLE_KEY`.
- [x] **1.8 Verifica:** confermare che la tabella sia accessibile.

### Fase 2 - Webhook Telegram

- [x] **2.1 Codex:** aggiungere client Supabase al servizio FastAPI.
- [x] **2.2 Codex:** implementare `/iscrivimi`.
- [x] **2.3 Codex:** implementare `/disiscrivimi`.
- [x] **2.4 Codex:** aggiornare `/start` e `/help`.
- [x] **2.5 Codex:** aggiungere `/privacy`.
- [x] **2.6 Codex:** mantenere `/segnale` funzionante per ogni utente.
- [x] **2.7 Codex:** impedire iscrizioni duplicate.
- [x] **2.8 Codex:** non esporre operazioni amministrative agli utenti.
- [x] **2.9 Test:** verificare iscrizione, rinnovo e disiscrizione.

### Fase 3 - Dashboard

- [x] **3.1 Utente/Codex:** recuperare username pubblico del bot Telegram.
- [x] **3.2 Codex:** aggiungere pulsante "Ricevi segnali su Telegram".
- [x] **3.3 Codex:** collegare il pulsante al deep link del bot.
- [x] **3.4 Codex:** aggiungere breve testo su consenso e disiscrizione.
- [x] **3.5 Codex:** aggiungere `GET /subscribers/count` al servizio FastAPI.
- [x] **3.6 Codex:** mostrare nella dashboard il numero di iscritti attivi.
- [x] **3.7 Codex:** configurare CORS per l'origine GitHub Pages.
- [x] **3.8 Test:** verificare endpoint, fallback, dashboard desktop e mobile.

#### Specifiche operative Fase 3 - Dashboard Telegram Subscription UI

##### Situazione di partenza

Il sistema di iscrizione Telegram e operativo:

- `/help` funziona;
- `/iscrivimi` funziona;
- `/disiscrivimi` funziona;
- gli iscritti vengono memorizzati correttamente in Supabase;
- `telegram_subscribers.active` cambia correttamente.

La dashboard pubblica non mostra ancora la possibilita di iscriversi. La
funzionalita deve quindi essere resa visibile e facilmente utilizzabile.

##### Card Telegram nella dashboard

Aggiungere una sezione visibile, compatta e coerente con il tema scuro
esistente. La posizione raccomandata e sotto le card principali di segnale e
rischio, vicino allo stato della connessione oppure sopra la nota finale.

La card deve contenere:

```text
NOTIFICHE TELEGRAM

Ricevi un avviso solo quando cambia il segnale BTC o il livello di rischio.

Iscritti attivi: <numero>

[Iscriviti su Telegram]

Dopo l'apertura del bot, invia /iscrivimi.
```

Il pulsante deve aprire il bot tramite:

```text
https://t.me/<BOT_USERNAME>
```

Preferire il deep link seguente solo se il webhook gestisce correttamente
`/start iscrivimi`:

```text
https://t.me/<BOT_USERNAME>?start=iscrivimi
```

Se lo username del bot non e gia disponibile nel progetto, definirlo tramite
una costante JavaScript o una configurazione pubblica priva di secret.

##### Contatore pubblico degli iscritti

Implementare sul servizio FastAPI esistente:

```text
GET /subscribers/count
```

L'endpoint deve:

- interrogare Supabase esclusivamente dal backend con
  `SUPABASE_SERVICE_ROLE_KEY`;
- contare soltanto le righe con `active = true`;
- restituire esclusivamente:

```json
{
  "active_subscribers": 1
}
```

- non restituire chat ID, username, nomi, date o altri dati personali;
- restituire un errore controllato se Supabase non e disponibile.

Il JavaScript della dashboard deve interrogare:

```text
https://btc-prudential-signal.onrender.com/subscribers/count
```

Se il servizio non e disponibile, mostrare:

```text
Iscritti attivi: non disponibile
```

Il mancato caricamento del contatore non deve interrompere le altre funzioni
della dashboard.

##### CORS

Configurare FastAPI, se necessario, per consentire l'origine:

```text
https://giuse2003.github.io
```

Limitare CORS alle origini effettivamente necessarie, senza abilitare accessi
piu ampi del richiesto.

##### Regole di sicurezza

Il frontend pubblico non deve contenere:

- `SUPABASE_SERVICE_ROLE_KEY`;
- chiavi segrete Supabase;
- token del bot Telegram;
- altri secret del backend.

La dashboard non deve interrogare direttamente Supabase con chiavi
privilegiate. Tutte le operazioni sul database devono passare dal backend
FastAPI.

##### Vincoli

Non modificare:

- calcolo del segnale BTC;
- calcolo del rischio;
- struttura di `docs/status.json`;
- comportamento esistente di `/segnale`;
- comportamento di `/iscrivimi` e `/disiscrivimi`, salvo il supporto
  strettamente necessario a un deep link sicuro;
- schema Supabase, salvo necessita tecnica documentata.

##### Deliverable Fase 3

- endpoint FastAPI per il conteggio degli iscritti attivi;
- card Telegram nella dashboard;
- integrazione JavaScript del contatore;
- configurazione CORS minima;
- test automatici dell'endpoint;
- aggiornamento della documentazione;
- verifica esplicita dell'assenza di secret nel frontend pubblico.

### Fase 4 - Invio collettivo

- [ ] **4.1 Codex:** leggere gli iscritti attivi da Supabase.
- [ ] **4.2 Codex:** inviare notifiche solo al cambio di segnale o rischio.
- [ ] **4.3 Codex:** mantenere la notifica amministratore compatibile.
- [ ] **4.4 Codex:** gestire rate limit Telegram e invii parzialmente falliti.
- [ ] **4.5 Codex:** disattivare iscritti che bloccano il bot.
- [ ] **4.6 Test:** simulare invio a piu chat di prova.
- [ ] **4.7 Test:** verificare che nessun messaggio parta senza cambiamenti.

### Fase 5 - Configurazione protetta

- [x] **5.1 Utente:** aggiungere su Render `SUPABASE_URL`.
- [x] **5.2 Utente:** aggiungere su Render `SUPABASE_SERVICE_ROLE_KEY`.
- [ ] **5.3 Utente:** aggiungere su Render `TELEGRAM_ADMIN_CHAT_ID`.
- [ ] **5.4 Utente:** aggiungere su GitHub Actions i secret necessari.
- [x] **5.5 Codex:** mantenere compatibilita temporanea con
  `TELEGRAM_CHAT_ID`, se necessaria.
- [x] **5.6 Verifica:** confermare che nessun secret sia presente nei log o
  nei file versionati.

### Fase 6 - Privacy e rilascio

- [x] **6.1 Codex:** preparare informativa privacy minima.
- [x] **6.2 Codex:** registrare data e origine del consenso.
- [x] **6.3 Codex:** documentare cancellazione e disiscrizione.
- [ ] **6.4 Utente:** approvare testo privacy e comportamento notifiche.
- [ ] **6.5 Codex:** aggiornare menu comandi Telegram.
- [x] **6.6 Codex:** aggiornare README e documenti di contesto.
- [ ] **6.7 Test finale:** `/start`.
- [x] **6.8 Test finale:** `/iscrivimi`.
- [ ] **6.9 Test finale:** `/segnale`.
- [ ] **6.10 Test finale:** notifica collettiva controllata.
- [x] **6.11 Test finale:** `/disiscrivimi`.

## Variabili previste

### Render

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_ADMIN_CHAT_ID
TELEGRAM_WEBHOOK_SECRET
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

### GitHub Actions

Le variabili definitive dipenderanno da dove verra eseguito l'invio
collettivo. Sono previste almeno:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_ADMIN_CHAT_ID
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

## Dati minimi previsti per ogni iscritto

Schema approvato per la Fase 1:

```text
telegram_chat_id
telegram_user_id
telegram_username
telegram_first_name
telegram_language_code
active
subscribed_at
unsubscribed_at
consent_version
consent_source
last_delivered_at
delivery_failures
last_delivery_error
last_delivery_error_at
created_at
updated_at
```

Non verranno memorizzati numeri di cellulare.

## Criteri di completamento

La funzionalita sara considerata completata quando:

- un visitatore apre il bot dalla dashboard;
- `/iscrivimi` registra il consenso senza duplicati;
- l'iscritto riceve una notifica quando cambia segnale o rischio;
- non riceve notifiche orarie senza variazioni;
- `/disiscrivimi` interrompe gli invii;
- il proprietario continua a ricevere e usare le funzioni amministrative;
- utenti non raggiungibili vengono gestiti senza bloccare gli altri invii;
- tutti i test automatici passano;
- documentazione e file di contesto sono aggiornati.

## Registro avanzamento

| Data | Passo | Stato | Note |
|---|---|---|---|
| 2026-06-09 | Creazione roadmap | Completato | Decisioni e responsabilita iniziali registrate. |
| 2026-06-10 | 1.3 Schema Supabase | Completato | Tabella privata via RLS, chiave primaria su telegram_chat_id. |
| 2026-06-10 | 1.4 Script SQL | Completato | Creato `supabase/telegram_subscribers.sql`. |
| 2026-06-10 | Fase 1 Supabase | Completato | RLS forzata, nessuna policy pubblica e test REST riuscito. |
| 2026-06-10 | Fase 2 Webhook | Implementata | Comandi pubblici, repository Supabase e 23 test superati. |
| 2026-06-10 | Pubblicazione Fase 2 | Completato | Commit `a19df0a` pubblicato su `main`; health check Render HTTP 200. |
| 2026-06-10 | Controllo secret | Completato | `.env` ignorato e nessuna credenziale presente nei file versionati. |
| 2026-06-10 | Configurazione Render Supabase | Completato | Variabili Supabase configurate sul servizio Render. |
| 2026-06-10 | Collaudo iscrizioni Telegram | Completato | `/help`, `/iscrivimi` e `/disiscrivimi` funzionanti; campo `active` verificato. |
| 2026-06-10 | Specifiche dashboard Telegram | Pianificato | Definiti card pubblica, contatore, endpoint FastAPI, CORS e requisiti di sicurezza. |
| 2026-06-11 | Username bot | Completato | Verificato pubblicamente `@BTC_Prudential_Signal_bot`. |
| 2026-06-11 | Endpoint contatore | Implementato | Conteggio server-side dei soli record attivi; risposta aggregata senza dati personali. |
| 2026-06-11 | Card Telegram dashboard | Implementata | Deep link `/start iscrivimi`, contatore e fallback neutro. |
| 2026-06-11 | Verifica responsive | Completato | Layout verificato a 1280x720 e 390x844 senza overflow orizzontale. |
| 2026-06-11 | Test Fase 3 | Completato | 32 test automatici e conteggio reale Supabase pari a 1. |
| 2026-06-11 | Deploy pubblico Fase 3 | Completato | Render e GitHub Pages aggiornati; endpoint e card restituiscono il conteggio 1. |
| 2026-06-11 | Verifica CORS e privacy | Completato | Origine GitHub Pages autorizzata; risposta limitata a `active_subscribers`. |

## Prossimo passo

Avviare la Fase 4 per l'invio collettivo ai soli iscritti attivi quando cambia
il segnale o il rischio.

La Fase 4 dovra:

1. leggere da Supabase soltanto gli iscritti con `active = true`;
2. mantenere la notifica amministratore compatibile;
3. evitare invii quando segnale e rischio non cambiano;
4. gestire rate limit, errori parziali e utenti che bloccano il bot;
5. aggiornare gli esiti di consegna senza interrompere gli altri invii;
6. essere verificata con test automatici e una notifica collettiva controllata.
