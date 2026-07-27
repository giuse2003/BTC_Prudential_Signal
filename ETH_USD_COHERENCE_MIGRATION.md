# Piano di migrazione del progetto gemello a ETH-USD Signal

Questo documento e un handoff operativo per un agente incaricato di applicare
al progetto Ethereum lo stesso lavoro di coerenza, tracciabilita e
riproducibilita eseguito su BTC-USD Signal.

## Obiettivo

Trasformare il progetto Ethereum in **ETH-USD Signal**, con:

- Coinbase come unica fonte di dati;
- `ETH-USD` come unico mercato del modello;
- `ETH-EUR` usato soltanto come prezzo spot informativo;
- una baseline v1 chiaramente definita e separata dal run operativo corrente;
- input, codice, ambiente e output verificabili;
- dashboard, Telegram, Worker, report e documentazione coerenti tra loro;
- una baseline congelata riproducibile offline da un clone pulito.

Non copiare nel progetto Ethereum date, prezzi, metriche, hash o artefatti del
progetto Bitcoin. Vanno ricalcolati usando esclusivamente lo storico Coinbase
`ETH-USD`.

## Contratto non negoziabile

Al termine deve esistere una sola catena informativa ufficiale:

```text
Coinbase ETH-USD
  -> candele DAILY UTC concluse
  -> indicatori
  -> quattro regole di acquisto e una regola di vendita
  -> azione
  -> backtest e Buy & Hold sullo stesso periodo
  -> manifest e artefatti
  -> dashboard e Worker Cloudflare
```

Yahoo Finance non deve essere un fallback. Vecchi file Yahoo possono restare
nella cronologia Git, ma non devono essere letti dal codice, citati come fonte
corrente o mescolati con Coinbase.

Le sole azioni pubblicabili sono:

- `ACQUISTA`;
- `MANTIENI STATO ATTUALE`;
- `VENDI`.

Non introdurre `STATO ATTUALE`, `CONDIZIONE`, Golden Cross o altre strategie
storiche. Eliminare dalla documentazione e dagli output correnti risultati di
vecchie versioni non appartenenti alla baseline v1.

## 1. Audit iniziale

Prima di modificare file:

1. Leggere `README`, documenti metodologici, configurazione, pipeline, strategia,
   backtest, report, workflow GitHub, dashboard e Worker Cloudflare.
2. Eseguire `git status`, annotare il branch e non annullare modifiche esistenti
   dell'utente.
3. Inventariare tutte le occorrenze di `BTC`, `ETH`, `EUR`, `USD`, Yahoo,
   Coinbase, Golden Cross e dei vecchi nomi del progetto.
4. Eseguire i test esistenti e conservare il risultato come riferimento.
5. Identificare quali numeri siano calcolati e quali siano copiati manualmente.
6. Identificare tutti i consumatori degli output: dashboard, Telegram, Worker,
   GitHub Pages, Supabase e workflow schedulati.
7. Creare un branch, per esempio `codex/eth-usd-coherence`.

Comandi orientativi:

```powershell
git status --short --branch
rg -n "BTC|ETH|EUR|USD|Yahoo|Coinbase|Golden Cross|golden_cross" .
rg --files
python -m unittest discover -s tests -v
```

Se il progetto Ethereum usa nomi o cartelle differenti, adattare la struttura
senza imporre meccanicamente quella Bitcoin.

## 2. Identita del progetto

Aggiornare configurazione, titoli, report, dashboard, messaggi e documentazione:

| Campo | Valore Ethereum |
|---|---|
| Nome | `ETH-USD Signal` |
| Mercato del modello | Coinbase `ETH-USD` |
| Prezzo informativo | Coinbase `ETH-EUR` spot |
| Versione metodologica iniziale | `1.0` |
| Granularita | `ONE_DAY` |
| Fuso temporale | UTC |
| Cache | `data/ETH-USD_coinbase_daily.csv` |

Non eseguire una sostituzione globale cieca: URL del repository, nomi dei
segreti, endpoint, nomi di tabelle e identificatori Cloudflare possono richiedere
valutazioni specifiche.

## 3. Migrazione completa a Coinbase

Creare o adattare un modulo dati equivalente a `data/coinbase.py`.

Requisiti:

1. Usare l'API pubblica Coinbase Advanced Trade market.
2. Scaricare `/products/ETH-USD/candles` con granularita `ONE_DAY`.
3. Gestire il limite Coinbase scaricando a blocchi e deduplicando le date.
4. Usare retry e timeout espliciti per errori temporanei e rate limit.
5. Conservare OHLCV con colonne `Open`, `High`, `Low`, `Close`, `Volume`.
6. Considerare `Volume` come volume base in ETH.
7. Escludere sempre la candela UTC corrente non conclusa.
8. Supportare un cutoff deterministico `as_of=YYYY-MM-DD`, inclusivo.
9. Validare date ordinate, assenza di duplicati, valori validi e nessun giorno
   mancante tra prima e ultima candela.
10. Usare la cache soltanto come copia della medesima fonte Coinbase.
11. Se Coinbase non e raggiungibile, ammettere la cache solo se valida; non
    passare a Yahoo o a un altro mercato.
12. Recuperare separatamente gli snapshot `ETH-USD` e `ETH-EUR`; quest'ultimo
    non deve entrare in indicatori o backtest.

La prima data disponibile deve essere scoperta dai dati Coinbase e registrata
nel manifest. Non copiare `2015-07-20`, che appartiene a BTC-USD.

## 4. Contratto della baseline

Se il progetto Ethereum gemello adotta la stessa baseline approvata, applicare
esattamente queste regole alle candele `ETH-USD`.

### Acquisto

`ACQUISTA` soltanto se tutte e quattro le condizioni sono vere:

1. `Close > SMA200`;
2. `RSI14 >= 40`;
3. `Close > Close.shift(7)`;
4. `Volume ETH-USD > media mobile Volume a 20 giorni`.

### Vendita

`VENDI` quando il Close e sotto SMA50 nella candela corrente e in quella
immediatamente precedente.

La vendita ha precedenza sull'acquisto. In ogni altro caso pubblicare
`MANTIENI STATO ATTUALE`.

### Formule

Rendere esplicite nel manifest le formule effettive:

- SMA50 e SMA200: media aritmetica rolling con finestra completa;
- RSI14: delta, gain/loss separati, EWM con `alpha=1/14`, `adjust=False` e
  `min_periods=14`;
- VolumeAvg20: media aritmetica rolling a 20 giorni;
- ATR14: true range massimo tra `H-L`, `abs(H-prevClose)` e
  `abs(L-prevClose)`, poi EWM a 14;
- momentum 7 giorni: confronto con `Close.shift(7)`.

Prima di procedere, verificare che queste siano davvero le regole approvate per
il progetto Ethereum. Se il progetto possiede una baseline differente, non
cambiarla in silenzio: documentare la differenza e chiedere conferma.

## 5. Backtest coerente

Il backtest deve conservare la metodologia approvata:

1. Esposizione desiderata: `ACQUISTA=100%`, `VENDI=0%`, mantenimento tramite
   forward-fill; esposizione iniziale 0%.
2. Segnale calcolato alla chiusura del giorno `t` e applicato dal rendimento del
   giorno successivo tramite `shift(1)`.
3. Rendimento ETH: `Close.pct_change()`.
4. Rendimento strategia: esposizione effettiva moltiplicata per rendimento ETH.
5. Buy & Hold: ingresso al primo Close del periodo valutato.
6. Strategia e Buy & Hold devono avere lo stesso primo e ultimo giorno.
7. Escludere dalla valutazione il warm-up necessario alla SMA200.
8. Annualizzazione e Sharpe su calendario crypto di 365 giorni.
9. Sharpe con tasso privo di rischio pari a zero e deviazione standard campionaria.
10. Win rate e numero operazioni devono includere solo trade long completati;
    un'eventuale posizione finale aperta non e un trade completato.
11. Dichiarare chiaramente che commissioni, spread, slippage, imposte e
    rendimento della liquidita sono esclusi, se la baseline li lascia invariati.

Non usare il numero di righe del dataset come durata se esistono buchi: la
validazione deve impedire i buchi e il manifest deve registrare sia osservazioni
sia giorni di calendario.

## 6. DAILY e LIVE PREVIEW

Separare due concetti:

- `DAILY`: usa esclusivamente l'ultima candela Coinbase conclusa ed e il solo
  input ufficiale del backtest;
- `LIVE PREVIEW`: aggiunge una riga provvisoria usando spot e volume 24h
  `ETH-USD`, ricalcola gli indicatori ed evidenzia che puo cambiare prima della
  chiusura UTC.

Entrambi usano le stesse regole e lo stesso vocabolario di azioni. Il prezzo
`ETH-EUR` resta un controvalore informativo nei contenuti live.

## 7. Pipeline unica

CLI, monitor schedulato e generazione dei report devono chiamare la stessa
pipeline. Evitare duplicazioni delle regole tra script.

La pipeline operativa deve:

1. caricare candele Coinbase chiuse;
2. calcolare provenienza dell'input;
3. calcolare indicatori e segnali;
4. eliminare il warm-up;
5. eseguire strategia e Buy & Hold;
6. recuperare gli snapshot live `ETH-USD` e `ETH-EUR`;
7. generare DAILY e LIVE PREVIEW;
8. scrivere tutto in staging;
9. creare e validare il manifest;
10. promuovere l'intero pacchetto in modo transazionale;
11. mantenere il pacchetto precedente se la pubblicazione fallisce.

## 8. Pacchetto operativo

Pubblicare insieme almeno questi file:

```text
raw_candles.csv
status.json
live-status.json
chart-data.json
historical_signals.csv
equity_timeseries.csv
report.txt
price_sma_signals.png
manifest.json
```

`raw_candles.csv` deve contenere l'esatto input del run. Il suo SHA-256 deve
coincidere sia con l'artefatto dichiarato sia con l'hash input nella provenienza.

Tutti i JSON pubblici devono condividere lo stesso `run_id`. Il manifest deve
includere:

- tipo run `operational-latest`;
- nome, versione, mercato, fonte, UTC e istante di generazione;
- periodo di storico, warm-up e valutazione;
- regole ed execution delay;
- metriche strategia e Buy & Hold;
- commit sorgente;
- versione Python e dipendenze;
- hash di `requirements.lock`;
- hash, dimensione e percorso di ogni artefatto;
- numero, prima data e ultima data delle candele di input;
- collegamento al manifest della baseline congelata.

Dashboard e Worker devono leggere questi file. Non devono ricopiare metriche o
ricalcolare il modello.

## 9. Pubblicazione deterministica

Per impedire differenze artificiali tra Windows e Linux:

1. aggiungere `.gitattributes` con testo `LF` e PNG binari;
2. serializzare JSON e report in UTF-8 con terminatori `LF`;
3. serializzare i CSV con `lineterminator="\n"`;
4. non includere timestamp variabili nella baseline congelata, salvo metadati
   esplicitamente esclusi dal confronto;
5. normalizzare a `LF` i sorgenti prima di calcolarne l'hash;
6. confrontare byte per byte gli artefatti canonici.

Esempio `.gitattributes`:

```gitattributes
* text=auto eol=lf
*.png binary
```

## 10. Ambiente bloccato

Usare lo stesso approccio del progetto BTC:

- `.python-version` con la versione Python esatta;
- `requirements.in` con le dipendenze dirette esatte;
- `requirements.lock` con dipendenze transitive e hash;
- `requirements.txt` che include il lock.

Se il progetto Ethereum usa lo stesso stack, partire da Python 3.13.0 e dalle
versioni bloccate del progetto BTC. Rigenerare comunque il lock nel progetto ETH
e verificarlo con:

```powershell
python -m pip install --require-hashes -r requirements.lock
```

Non dichiarare riproducibile un ambiente installato da dipendenze senza versione
o senza hash.

## 11. Baseline congelata

Scegliere esplicitamente una data `AS_OF` corrispondente a una candela UTC
conclusa. Per confronto contemporaneo con BTC si puo proporre `2026-07-26`, ma
la data deve essere approvata e non assunta implicitamente.

Creare:

```text
docs/runs/baseline-v1-AAAA-MM-GG/
```

Artefatti canonici congelati:

```text
raw_candles.csv
status.json
chart-data.json
historical_signals.csv
equity_timeseries.csv
report.txt
manifest.json
```

Il PNG non deve essere canonico byte per byte, perche il raster Matplotlib puo
variare tra piattaforme. Le serie numeriche che lo generano devono esserlo.

Il manifest congelato deve contenere:

- `run_type: frozen-baseline`;
- `run_id`, per esempio `baseline-v1-2026-07-26`;
- tag Git omonimo;
- hash normalizzati dei file sorgente che determinano il modello;
- Python, tutte le dipendenze e hash del lock;
- endpoint, prodotto, granularita e cutoff Coinbase;
- hash dello snapshot grezzo;
- formule complete;
- periodo effettivo e numero osservazioni;
- metriche complete;
- hash e dimensione degli artefatti.

Creare comandi equivalenti a:

```powershell
python freeze_baseline.py --as-of 2026-07-26 --output docs/runs/baseline-v1-2026-07-26 --run-id baseline-v1-2026-07-26 --source-tag baseline-v1-2026-07-26 --force-download
python reproduce.py --manifest docs/runs/baseline-v1-2026-07-26/manifest.json
```

La seconda istruzione deve lavorare offline usando lo snapshot incluso.

## 12. Verifica offline

`reproduce.py` deve fallire se cambia uno dei seguenti elementi:

- versione Python;
- versione di una dipendenza bloccata;
- hash di `requirements.lock`;
- hash di un sorgente del modello;
- hash dello snapshot Coinbase;
- hash di un artefatto pubblicato;
- periodo o metrica ricalcolata;
- byte di un output rigenerato.

Deve leggere `raw_candles.csv`, ricalcolare indicatori, segnali e backtest in una
directory temporanea e confrontare gli output con il manifest.

Non limitarsi a verificare che i numeri nel Markdown coincidano con quelli nel
JSON: quella sarebbe coerenza documentale, non riproducibilita.

## 13. Test automatici

Adattare e ampliare i test del progetto Ethereum. Coprire almeno:

### Dati

- esclusione della candela UTC corrente;
- cutoff `as_of` inclusivo;
- rifiuto di duplicati e giorni mancanti;
- cache Coinbase valida quando la rete non e disponibile;
- nessun fallback Yahoo.

### Regole

- esattamente quattro condizioni buy;
- acquisto soltanto con tutte vere;
- vendita con due Close consecutivi sotto SMA50;
- nessuna vendita con un solo Close sotto SMA50;
- precedenza della vendita;
- LIVE PREVIEW ricalcolata con spot e volume live.

### Backtest

- shift di un giorno senza look-ahead;
- annualizzazione a 365 giorni;
- conteggio dei trade completati;
- posizione finale aperta esclusa dal win rate;
- identico periodo strategia/Buy & Hold.

### Pubblicazione

- stesso `run_id` nei JSON;
- rifiuto di pacchetti misti;
- hash di ogni artefatto;
- hash del CSV grezzo uguale alla provenienza;
- rollback o mancata promozione in caso di errore.

### Interfacce

- dashboard alimentata da manifest e JSON;
- nessun segreto nel frontend;
- Worker privo di logica di calcolo del modello;
- Telegram con sole tre azioni;
- quattro condizioni buy e una sell;
- icona verde per condizione vera e rossa per condizione falsa.

### Baseline congelata

- riproduzione completa della baseline ETH;
- assert su `run_id`, periodo, osservazioni e metriche ETH effettive;
- confronto byte per byte degli artefatti canonici.

Non cercare di ottenere esattamente 57 test: quello e il conteggio corrente del
progetto BTC, non un requisito. Conta la copertura dei contratti Ethereum.

## 14. GitHub Actions

Creare un workflow per push e pull request che:

1. esegua checkout;
2. installi la versione Python esatta;
3. installi con `--require-hashes` da `requirements.lock`;
4. esegua l'intera suite;
5. esegua la riproduzione offline della baseline congelata.

Aggiornare il monitor schedulato affinche:

- usi la versione Python esatta e il lock con hash;
- mantenga cache e stato del monitor;
- esegua la pipeline comune;
- copi in `docs/` tutti gli artefatti elencati nel manifest, incluso
  `raw_candles.csv`;
- aggiunga al commit tutti gli artefatti, non soltanto i JSON;
- serializzi le esecuzioni con un gruppo `concurrency`;
- non cancelli un run gia iniziato;
- non esponga segreti nei log o nel repository.

Attenzione: se il workflow committa direttamente su `main`, sincronizzare sempre
il repository prima di modifiche manuali per evitare conflitti.

## 15. Dashboard, Telegram e Cloudflare

### Dashboard

- mostrare chiaramente `ETH-USD Signal`;
- leggere DAILY, LIVE PREVIEW, periodo e metriche dagli artefatti;
- rappresentare candele e indicatori ETH, non BTC;
- non contenere valori finanziari hardcoded;
- non contenere token, service role key o altri segreti;
- mantenere il collegamento Telegram se previsto.

### Telegram

Il messaggio deve usare il formato approvato:

```text
ETH-USD Signal - LIVE PREVIEW

Azione: MANTIENI STATO ATTUALE
Prezzo informativo: ... EUR

ACQUISTA:
[rosso/verde] 1.
[rosso/verde] 2.
[rosso/verde] 3.
[rosso/verde] 4.

VENDI:
[rosso/verde] 1.
```

Usare le stesse icone quadrate rosse e verdi del progetto BTC, non `NO` e `OK`.

### Worker Cloudflare

- aggiornare nome, mercato, URL GitHub Pages/raw e testi da BTC a ETH;
- fare leggere al Worker il pacchetto pubblicato;
- non duplicare indicatori o regole nel Worker;
- mantenere autorizzazioni e gestione iscritti;
- eseguire test locali;
- pubblicare con Wrangler soltanto dopo test e commit;
- verificare endpoint pubblico e comando Telegram dopo il deployment.

Non modificare o ricreare segreti Cloudflare/Supabase se non necessario. Non
committare mai i loro valori.

## 16. Documentazione da produrre

Aggiornare o creare:

- `README.md`: identita, regole, dati, due tipi di run e comandi essenziali;
- `EVALUATION_VALUES.md`: valori ETH della baseline e valutazione critica;
- `PROJECT_OVERVIEW.md`: architettura e contratto informativo;
- `PROJECT_STATUS.md`: stato corrente e limiti aperti;
- `BASELINE_SYNC_CHECKLIST.md`: checklist prima della pubblicazione;
- `DECISION_LOG.md`: cronostoria delle decisioni;
- `REPRODUCIBILITY.md`: procedura completa da clone pulito;
- eventuale guida Cloudflare/Supabase aggiornata.

La documentazione deve distinguere sempre:

1. **baseline congelata**, immutabile e canonica;
2. **run operativo corrente**, dinamico ma tracciabile.

La fonte canonica dei risultati baseline e il manifest dentro
`docs/runs/baseline-v1-DATA/`. La fonte del run corrente e `docs/manifest.json`.

Documentare esplicitamente i limiti finanziari:

- risultati storici, non previsione;
- rischio di overfitting;
- assenza di costi se non modellati;
- nessun vero out-of-sample se non ancora creato;
- dipendenza dalla qualita dei dati Coinbase;
- esposizione binaria e drawdown storico;
- nessuna consulenza finanziaria.

## 17. Ordine consigliato di esecuzione

Seguire questo ordine per evitare manifest incoerenti:

1. Audit e test iniziali.
2. Branch dedicato.
3. Configurazione ETH e migrazione Coinbase.
4. Regole, segnali, DAILY/LIVE e pipeline unica.
5. Backtest e pubblicazione transazionale.
6. Dashboard, Telegram e Worker.
7. Ambiente bloccato e serializzazione deterministica.
8. Tool di congelamento e riproduzione.
9. Test automatici.
10. Documentazione.
11. Generazione della baseline ETH definitiva.
12. Riproduzione locale completa.
13. Primo commit con codice, lock, documentazione e baseline congelata.
14. Tag Git della baseline sul primo commit.
15. Da quel commit pulito, esecuzione del run operativo.
16. Verifica che `source_commit` del manifest operativo punti al primo commit.
17. Secondo commit contenente il pacchetto operativo corrente.
18. Push del branch, del tag e di `main` secondo il flusso approvato.
19. Attesa dei test GitHub su Linux.
20. Verifica GitHub Pages.
21. Deployment Cloudflare, se il Worker e cambiato.
22. Verifica finale di dashboard, endpoint e Telegram.

La separazione in due commit evita che il manifest operativo dichiari un commit
precedente al codice oppure tenti di riferirsi circolarmente al commit che
contiene il manifest stesso.

## 18. Prova da clone pulito

Dopo il primo commit e prima di considerare concluso il lavoro:

1. creare un worktree o clone temporaneo del commit destinato al tag;
2. creare un ambiente virtuale nuovo;
3. installare esclusivamente da `requirements.lock` con hash;
4. eseguire `reproduce.py` senza contattare Coinbase;
5. eseguire tutti i test;
6. ripetere su GitHub Actions Linux;
7. verificare che l'albero Git finale sia pulito.

Esempio utente finale:

```powershell
git clone URL_REPOSITORY_ETH
cd NOME_REPOSITORY_ETH
git checkout baseline-v1-AAAA-MM-GG
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.venv\Scripts\python reproduce.py --manifest docs/runs/baseline-v1-AAAA-MM-GG/manifest.json
```

Su Linux/macOS usare `.venv/bin/python`.

## 19. Strategia Git

Prima di eliminare vecchi report o codice obsoleto, conservarne la reperibilita
nella cronologia Git. Se utile, creare un tag pre-migrazione, ma non mantenere
quei contenuti nella documentazione operativa corrente.

Nomi suggeriti:

```text
branch: codex/eth-usd-coherence
commit 1: Rendi riproducibile la baseline ETH-USD v1
tag: baseline-v1-AAAA-MM-GG
commit 2: Pubblica il pacchetto operativo ETH tracciabile
```

Non spostare o sovrascrivere in seguito il tag della baseline. Una modifica a
dati, regole, formule, ambiente o periodo richiede una nuova baseline e un nuovo
tag.

## 20. Criteri di accettazione

Il lavoro e completo soltanto se tutte le risposte sono **si**:

- [ ] Il progetto si chiama ovunque ETH-USD Signal?
- [ ] Il modello usa solo Coinbase `ETH-USD`?
- [ ] `ETH-EUR` e esclusivamente informativo?
- [ ] Yahoo e assente dalla pipeline runtime?
- [ ] Esistono soltanto le tre azioni approvate?
- [ ] Golden Cross e vecchie versioni sono assenti dalla baseline corrente?
- [ ] Le quattro regole buy e la regola sell sono implementate una sola volta?
- [ ] La vendita ha precedenza?
- [ ] DAILY esclude la candela corrente?
- [ ] LIVE PREVIEW e chiaramente provvisoria?
- [ ] Strategia e Buy & Hold usano lo stesso periodo post warm-up?
- [ ] Non esiste look-ahead nell'esecuzione?
- [ ] Il run operativo pubblica il CSV grezzo?
- [ ] Tutti gli artefatti hanno hash e appartengono allo stesso `run_id`?
- [ ] Il manifest operativo indica il commit realmente eseguito?
- [ ] La baseline congelata contiene input, formule, ambiente, metriche e output?
- [ ] `reproduce.py` funziona offline da un checkout pulito?
- [ ] Gli output canonici sono identici su Windows e Linux?
- [ ] I test locali e GitHub Actions sono verdi?
- [ ] GitHub Pages mostra i dati ETH correnti?
- [ ] Telegram usa icone rosse/verdi e testi ETH?
- [ ] Il Worker Cloudflare pubblicato legge il pacchetto ETH corretto?
- [ ] La documentazione permette a un estraneo di ripetere la verifica?
- [ ] Limiti e rischi finanziari sono dichiarati senza ambiguita?
- [ ] Branch, commit, tag e push sono stati completati e verificati?

## 21. Resoconto richiesto all'agente

Alla fine l'agente deve comunicare:

1. branch, commit e tag creati;
2. data di cutoff e intervallo ETH effettivo;
3. prima data Coinbase e fine warm-up;
4. metriche strategia e Buy & Hold, senza arrotondamenti nel manifest;
5. numero di test e risultato locale/Linux;
6. risultato della riproduzione da checkout pulito;
7. URL GitHub Pages e stato del deployment;
8. stato del Worker Cloudflare e verifica Telegram;
9. eventuali differenze motivate rispetto al progetto BTC;
10. rischi residui e attivita non eseguite.

L'agente non deve dichiarare completato il lavoro se rimangono sessioni, test,
push o deployment necessari ancora in esecuzione.
