# Configurazione Supabase per gli iscritti Telegram

Questa guida copre la Fase 1 della roadmap:

- creazione del progetto Supabase;
- creazione sicura della tabella degli iscritti;
- recupero delle credenziali server;
- verifica iniziale.

Non inserire token o chiavi Supabase nei file del repository.

## 1. Accedi a Supabase

1. Apri <https://supabase.com/dashboard>.
2. Accedi oppure crea un account.
3. Seleziona il progetto condiviso `crypto-prudential-signal`.

## 2. Progetto Supabase

Il progetto Supabase era nato per BTC con il nome:

```text
btc-prudential-signal
```

Dal 24 giugno 2026 e stato rinominato:

```text
crypto-prudential-signal
```

La rinomina serve perche lo stesso progetto Supabase viene condiviso anche dal
progetto Ethereum. La separazione dei dati non dipende dal nome del progetto,
ma dalle tabelle dedicate:

```text
BTC: public.telegram_subscribers
ETH: public.telegram_subscribers_eth
```

Non creare una nuova tabella BTC se `public.telegram_subscribers` esiste gia.
Non usare la tabella ETH per il bot BTC.

Se devi ricreare il progetto da zero, usa comunque un nome neutro come
`crypto-prudential-signal`, non `btc-prudential-signal`.

## 3. Crea la tabella

1. Nel progetto Supabase apri **SQL Editor**.
2. Premi **New query**.
3. Apri nel repository:

```text
supabase/telegram_subscribers.sql
```

4. Copia l'intero contenuto nel SQL Editor.
5. Premi **Run**.

Lo script BTC:

- crea `public.telegram_subscribers`;
- usa `telegram_chat_id` come chiave primaria e impedisce duplicati;
- registra consenso, iscrizione e disiscrizione;
- prepara campi per errori di consegna;
- aggiorna automaticamente `updated_at`;
- abilita e forza Row Level Security;
- revoca ogni accesso ad `anon` e `authenticated`;
- concede accesso soltanto a `service_role`.

## 4. Verifica il risultato

Alla fine dello script, la prima query deve restituire:

```text
table_name             rls_enabled   rls_forced
telegram_subscribers   true          true
```

La seconda query, relativa alle policy, deve restituire zero righe.

Puoi anche aprire **Table Editor** e verificare la presenza della tabella:

```text
telegram_subscribers
```

La tabella inizialmente deve essere vuota.

Nel progetto condiviso puoi vedere anche:

```text
telegram_subscribers_eth
```

Quella tabella appartiene al progetto ETH e non deve essere modificata dal
codice BTC.

## 5. Recupera URL e chiave server

Nel pannello Supabase apri:

```text
Project Settings > API
```

Recupera:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Nel pannello piu recente i nomi possono apparire come:

```text
Project URL
service_role secret
```

La service role:

- deve essere usata soltanto da backend/Worker e GitHub Actions;
- non deve essere inserita nella dashboard web;
- non deve essere aggiunta al repository;
- non deve essere inviata in chat;
- non deve essere mostrata nei log.

Non usare la chiave `anon` o `publishable` per il backend degli iscritti.

Nel progetto attuale la stessa `SUPABASE_URL` e la stessa
`SUPABASE_SERVICE_ROLE_KEY` possono essere configurate sia nel Worker BTC sia
nel Worker ETH. La sicurezza operativa resta affidata alle tabelle separate e
al fatto che i secret non siano mai esposti nel frontend.

## 6. Cosa non fare ancora

Non aggiungere ancora le credenziali a Cloudflare Worker o GitHub. Questo
avverra nella Fase 5, dopo l'implementazione e i test del client Supabase.

Non inserire manualmente righe nella tabella. La prima iscrizione verra creata
dal comando `/iscrivimi`.

## 7. Conferma necessaria

Quando hai completato i passaggi, comunica soltanto:

```text
Progetto Supabase disponibile come crypto-prudential-signal.
Script SQL eseguito.
Tabella telegram_subscribers presente.
RLS enabled: true.
RLS forced: true.
Policy trovate: 0.
```

Se vedi anche `telegram_subscribers_eth`, e normale: e la tabella usata dal
progetto Ethereum nello stesso Supabase condiviso.

Non comunicare URL, chiavi, password o altri secret.

## Motivazione della sicurezza

La tabella si trova nel schema `public`, esposto dalle API Supabase, ma RLS e
attiva senza policy per utenti pubblici. Le chiavi client non possono quindi
leggere o modificare gli iscritti.

L'accesso avverra esclusivamente dal backend con la service role. La
documentazione Supabase specifica che le service key possono bypassare RLS e
non devono mai essere esposte nel browser o ai clienti.

Fonti ufficiali:

- <https://supabase.com/docs/guides/database/postgres/row-level-security>
- <https://supabase.com/docs/guides/getting-started/api-keys>
