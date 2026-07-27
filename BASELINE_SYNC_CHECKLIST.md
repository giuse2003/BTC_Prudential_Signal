# Verifica di coerenza della baseline

Prima di pubblicare un run:

- [ ] la cache contiene esclusivamente candele Coinbase `BTC-USD`;
- [ ] non esistono date duplicate o giorni mancanti;
- [ ] la candela UTC corrente e esclusa dal DAILY;
- [ ] la valutazione inizia solo dopo il warm-up SMA200;
- [ ] strategia e Buy & Hold hanno lo stesso primo e ultimo giorno;
- [ ] le azioni appartengono al vocabolario ufficiale;
- [ ] la vendita ha precedenza;
- [ ] costi e slippage sono dichiarati assenti;
- [ ] tutti i JSON pubblici hanno lo stesso `run_id`;
- [ ] gli hash del manifest corrispondono agli artefatti;
- [ ] dashboard e Worker leggono i valori, senza ricopiarli nel codice.

La pipeline esegue automaticamente i controlli strutturali e mantiene l'ultimo
pacchetto completo se una nuova pubblicazione fallisce.
