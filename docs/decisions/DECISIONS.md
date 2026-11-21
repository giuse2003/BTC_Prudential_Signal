# Registro Formale delle Decisioni di Progetto — BTC-USD SIGNAL

Questo documento raccoglie in ordine cronologico e progressivo (`DEC-xxx`) tutte le decisioni architetturali, quantitative, operative e di governance del progetto **BTC-USD Signal**, adottando lo standard formale di **AEGIS EA** e **ARGUS X30**.

---

## DEC-001 — 2026-07-27 — Coerenza Metodologica BTC-USD Signal v1 e Fonte Dati Unica

- **Contesto**: Presenza di feed eterogenei (Yahoo Finance, mercati EUR misti) e nomenclature disallineate che compromettevano l'affidabilita del calcolo.
- **Decisione**:
  - Il progetto assume la denominazione ufficiale **BTC-USD Signal** (versione metodologica `1.0`).
  - **Coinbase Advanced Trade** diventa l'unica sorgente canonica per storico, prezzi e volumi.
  - `BTC-USD` e l'unico mercato del modello (indicatori, regole, segnali e backtest).
  - `BTC-EUR` spot viene utilizzato esclusivamente come controvalore informativo a video per l'utente, senza entrare nel modello.
  - I primi 200 giorni storici Coinbase (dal 2015-07-20 al 2016-02-03) sono warm-up SMA200 e sono esclusi dalla valutazione economica.
  - Le uniche tre azioni canoniche ammesse sono: `ACQUISTA`, `MANTIENI STATO ATTUALE`, `VENDI`.
  - La regola di vendita ha precedenza assoluta in caso di conflitto.
  - Esecuzione simulata conservativa a $t+1$ (azione calcolata alla chiusura $t$, applicata dal giorno successivo per eliminare il lookahead bias).
  - Buy & Hold calcolato sullo stesso identico periodo post warm-up.

---

## DEC-002 — 2026-07-27 — Baseline v1 Congelata e Standard di Riproducibilita Deterministica

- **Contesto**: Necessita di garantire la riproducibilita offline al 100% byte-for-byte dei risultati storici, impedendo che l'arrivo di nuove candele modifichi retroattivamente i numeri approvati.
- **Decisione**:
  - Congelamento della **Baseline v1** alla data `2026-07-26` con tag Git `baseline-v1-2026-07-26`.
  - Lo snapshot OHLCV Coinbase diventa parte del pacchetto versionato in `docs/runs/baseline-v1-2026-07-26/`.
  - Ambiente Python `3.13.0` e dipendenze bloccate con hash SHA-256 in `requirements.lock` (`--require-hashes`).
  - Creazione dello script `reproduce.py` che ricalcola l'intero backtest offline e valida gli hash crittografici SHA-256 di tutti gli artefatti prodotti.
  - Separazione netta tra il run congelato immutabile e il run operativo dinamico (`docs/manifest.json`).

---

## DEC-003 — 2026-07-27 — Protocollo di Ricerca Candidati ed Esito Candidati V1-S1 e V1-B1

- **Contesto**: Studio esplorativo di due possibili miglioramenti alla baseline:
  - `V1-S1`: vendita anticipata al primo Close sotto SMA50 (invece di due chiusure consecutive).
  - `V1-B1`: eliminazione del filtro volumetrico dall'acquisto.
- **Decisione & Evidenza Empirica**:
  - Applicazione del protocollo formale a 5 scenari di costo (0, 10, 25, 50, 100 bps), 5 blocchi temporali e *paired block bootstrap* (1.000 replicazioni).
  - `V1-S1` migliora diverse metriche ma ottiene una probabilita bootstrap di miglioramento positivo solo del $49,3\%$ (soglia richiesta $\ge 90\%$).
  - `V1-B1` non prevale nella maggioranza dei blocchi temporali (2/5) e ottiene una probabilita bootstrap del $65,96\%$.
  - Entrambi i candidati sono classificati formalmente **`NON PROMUOVIBILE`** e archiviati in `docs/experiments/btc-model-candidates-v1-2026-07-26/`.
  - La baseline di produzione v1 e rimasta sigillata e inalterata, prevenendo fenomeni di overfitting a posteriori.

---

## DEC-004 — 2026-11-21 — Integrazione Keep-Alive Supabase nel Monitor Orario

- **Contesto**: Il database Supabase degli iscritti Telegram (`crypto-prudential-signal`, ID `nzdzbzurwhnzxlapeoch`) e andato in pausa automatica per inattivita di 7 giorni nel piano Free, poiche `hourly_monitor.py` contattava il database solo in occasione di rari broadcast di notifica.
- **Decisione**:
  - Aggiunta della funzione `ping_supabase_keepalive()` eseguita ad ogni ciclo del monitor orario su GitHub Actions.
  - La funzione interroga `count_active()` effettuando una query leggera su Postgres, azzerando sistematicamente il timer di 7 giorni senza stressare il database.
  - Gestione sicura delle eccezioni (errore non bloccante per la pubblicazione delle candele).
  - Copertura con 3 test unitari dedicati (`test_hourly_monitor_notifications.py`).
  - Verifica live su GitHub Actions con esito `OK` e conteggio ripristinato (9 iscritti attivi).

---

## DEC-005 — 2026-11-21 — Architettura Ibrida a 2 Livelli (GitHub + MEGA CLOUD) e Avvio Ricerca Swing Sentinel (Know-How Aegis EA / XAU MASTER)

- **Contesto**: Richiesta dell'utente di trasferire il know-how quantitativo dei progetti `Aegis EA`, `Argus X30`, `Gold Sniping` e `XAU MASTER` su Bitcoin per una strategia Swing Trading (orizzonte plurisettimanale/mensile), adottando il rigoroso standard di versionamento e integrita crittografica.
- **Decisione**:
  1. **Adozione dell'Ecosistema a 2 Livelli**:
     - **GitHub Repository** (`D:\GitHub\BTC_Prudential_Signal`): codice sorgente, documentazione, registro decisioni `DECISIONS.md`, manifesti crittografici SHA-256 e metriche compatte.
     - **MEGA CLOUD Data Root** (`D:\MEGA CLOUD\Trading\BTC SIGNAL`): cartella canonica per artefatti pesanti, serie storiche estese, dump grezzi OHLCV e pacchetti di test completi.
  2. **Integrita Crittografica Obbligatoria**:
     - `docs/BTC_SOURCE_MANIFEST.md`: inventario di tutti i sorgenti con byte size e SHA-256 esatto.
     - `manifests/DATA_MANIFEST.csv`: inventario di tutti gli artefatti su MEGA CLOUD con metadati e SHA-256.
     - `tools/verify_manifests.py`: script automatico di verifica di conformita crittografica (fail se mancano file o se gli hash divergono).
     - `tools/update_manifests.py`: script automatico di aggiornamento manifesti.
  3. **Direttiva di Tracciabilita Integrale**:
     - Tutte le prove, i test e i candidati strategici (inclusi quelli non promossi o con esito negativo) devono essere archiviati, registrati nei manifesti, committati e pushati su Git senza alcuna cancellazione o riscrittura retroattiva.
  4. **Avvio Sviluppo Candidato Swing Sentinel (v2.0)**:
     - Ispirato a Aegis EA (motori `S5` ed `S7`): introduzione di Stop Loss strutturale su swing low/ATR, lock a Break-Even, piramidazione a rischio zero su 2 tranche e trailing stop Chandelier su ATR per la protezione dei profitti.

---

## DEC-006 — 2026-11-21 — Risultati Sperimentali Candidati Swing Sentinel v2.0 (Aegis Logic)

- **Contesto**: Valutazione comparativa su 3.943 giorni di storico Coinbase (2016-2026) di due candidati ispirati ai motori `S5` (Runner) ed `S7` di `Aegis EA`:
  1. `V2-CHANDELIER-PARABOLIC`: Uscita con Trailing Stop Chandelier ($Highest - 2.5 \times ATR$) attiva unicamente quando il prezzo e esteso $> 1.5 \times SMA50$.
  2. `V2-DUAL-TRANCHE-PYRAMID`: Entrata frazionata a 2 tranche (50% iniziale + 50% piramidazione a rischio zero solo dopo lock a Break-Even su $+1.5 \times ATR$).
- **Evidenza Empirica**:
  - `V2-CHANDELIER-PARABOLIC` **SUPERA LA BASELINE V1**:
    - Rendimento Totale: **`+44.217,2%`** (vs `+42.999,1%` della Baseline v1).
    - Rendimento Annuo (CAGR): **`+75,79%`** (vs `+75,36%`).
    - Sharpe Ratio: **`1,520`** (vs `1,491`), con un delta positivo costante di **`+0,030`** su tutti gli scenari di costo (da 0 a 100 bps).
    - Max Drawdown: **`-48,31%`** (identico alla baseline, nessun incremento di rischio).
    - Calmar Ratio: **`1,57`** (vs `1,56`).
  - `V2-DUAL-TRANCHE-PYRAMID` **`NON PROMUOVIBILE`**:
    - Il dimezzamento della tranche iniziale attenua l'efficacia sui rally rapidi e verticali di BTC, producendo un rendimento inferiore (`+24.055,1%`). Come da direttiva, il candidato non promosso e comunque registrato, conservato e tracciato nei manifesti.
- **Decisione**:
  - `V2-CHANDELIER-PARABOLIC` viene eletto a **Candidato Ufficiale per la Baseline v2.0**.
  - Tutti i dataset pesanti (`equity_comparison_v2.csv`, `trades_v2_chandelier.csv`, `costs_comparison_v2.csv`) sono archiviati su MEGA CLOUD (`D:\MEGA CLOUD\Trading\BTC SIGNAL\`) con impronte SHA-256 verificate.

