# Telegram Subscribers Roadmap

Ultimo aggiornamento: 9 giugno 2026

Stato generale: `DA INIZIARE`

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

- [ ] **1.1 Utente:** creare un account o accedere a Supabase.
- [ ] **1.2 Utente:** creare un nuovo progetto Supabase.
- [ ] **1.3 Codex:** definire schema, vincoli e policy della tabella iscritti.
- [ ] **1.4 Codex:** preparare lo script SQL completo.
- [ ] **1.5 Utente:** eseguire lo script nell'SQL Editor Supabase.
- [ ] **1.6 Utente:** recuperare `SUPABASE_URL`.
- [ ] **1.7 Utente:** recuperare `SUPABASE_SERVICE_ROLE_KEY`.
- [ ] **1.8 Verifica:** confermare che la tabella sia accessibile.

### Fase 2 - Webhook Telegram

- [ ] **2.1 Codex:** aggiungere client Supabase al servizio FastAPI.
- [ ] **2.2 Codex:** implementare `/iscrivimi`.
- [ ] **2.3 Codex:** implementare `/disiscrivimi`.
- [ ] **2.4 Codex:** aggiornare `/start` e `/help`.
- [ ] **2.5 Codex:** aggiungere `/privacy`.
- [ ] **2.6 Codex:** mantenere `/segnale` funzionante per ogni utente.
- [ ] **2.7 Codex:** impedire iscrizioni duplicate.
- [ ] **2.8 Codex:** limitare operazioni amministrative al chat ID admin.
- [ ] **2.9 Test:** verificare iscrizione, rinnovo e disiscrizione.

### Fase 3 - Dashboard

- [ ] **3.1 Utente/Codex:** recuperare username pubblico del bot Telegram.
- [ ] **3.2 Codex:** aggiungere pulsante "Ricevi segnali su Telegram".
- [ ] **3.3 Codex:** collegare il pulsante al deep link del bot.
- [ ] **3.4 Codex:** aggiungere breve testo su consenso e disiscrizione.
- [ ] **3.5 Test:** verificare dashboard desktop e mobile.

### Fase 4 - Invio collettivo

- [ ] **4.1 Codex:** leggere gli iscritti attivi da Supabase.
- [ ] **4.2 Codex:** inviare notifiche solo al cambio di segnale o rischio.
- [ ] **4.3 Codex:** mantenere la notifica amministratore compatibile.
- [ ] **4.4 Codex:** gestire rate limit Telegram e invii parzialmente falliti.
- [ ] **4.5 Codex:** disattivare iscritti che bloccano il bot.
- [ ] **4.6 Test:** simulare invio a piu chat di prova.
- [ ] **4.7 Test:** verificare che nessun messaggio parta senza cambiamenti.

### Fase 5 - Configurazione protetta

- [ ] **5.1 Utente:** aggiungere su Render `SUPABASE_URL`.
- [ ] **5.2 Utente:** aggiungere su Render `SUPABASE_SERVICE_ROLE_KEY`.
- [ ] **5.3 Utente:** aggiungere su Render `TELEGRAM_ADMIN_CHAT_ID`.
- [ ] **5.4 Utente:** aggiungere su GitHub Actions i secret necessari.
- [ ] **5.5 Codex:** mantenere compatibilita temporanea con
  `TELEGRAM_CHAT_ID`, se necessaria.
- [ ] **5.6 Verifica:** confermare che nessun secret sia presente nei log o
  nei file versionati.

### Fase 6 - Privacy e rilascio

- [ ] **6.1 Codex:** preparare informativa privacy minima.
- [ ] **6.2 Codex:** registrare data e origine del consenso.
- [ ] **6.3 Codex:** documentare cancellazione e disiscrizione.
- [ ] **6.4 Utente:** approvare testo privacy e comportamento notifiche.
- [ ] **6.5 Codex:** aggiornare menu comandi Telegram.
- [ ] **6.6 Codex:** aggiornare README e documenti di contesto.
- [ ] **6.7 Test finale:** `/start`.
- [ ] **6.8 Test finale:** `/iscrivimi`.
- [ ] **6.9 Test finale:** `/segnale`.
- [ ] **6.10 Test finale:** notifica collettiva controllata.
- [ ] **6.11 Test finale:** `/disiscrivimi`.

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

Schema indicativo, ancora da approvare:

```text
telegram_chat_id
telegram_user_id
telegram_username
active
subscribed_at
unsubscribed_at
consent_version
last_delivery_error
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

## Prossimo passo

Creare il progetto Supabase e preparare lo schema SQL della tabella iscritti.
