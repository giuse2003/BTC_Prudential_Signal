# BTC-USD Signal — Manifesto Crittografico dei Sorgenti (`SHA-256`)

Registro canonico di provenienza e integrita al byte di tutti i sorgenti Python, configurazioni e script di BTC-USD Signal.

- **Regola di Integrita**: gli hash `SHA-256` sono calcolati sui byte esatti del file.
- **Verifica Automatica**: eseguire `python tools/verify_manifests.py` per controllare l'integrita crittografica.
- **Ultimo Aggiornamento**: `2026-11-21 23:03:16 UTC`

| Nome File | Ruolo Architetturale | Bytes | SHA-256 | Percorso Canonico | Stato |
| :--- | :--- | ---: | :--- | :--- | :---: |
| `config.py` | Configurazione centrale | 1,785 | `c27f4a3245475121c4021bc53088a972e7a1c2cdc54f3c2273e27181e87f245d` | `config.py` | `CONFIG` |
| `pipeline.py` | Pipeline di esecuzione e pubblicazione | 6,332 | `5de8829f246ee7ba18db1e05db4427c337c48f0acd1fee945854fd4e9922eaa1` | `pipeline.py` | `CORE` |
| `main.py` | Punto di ingresso CLI e baseline freeze | 2,425 | `fcdd40fcc80bebefe6ed1a83007843514aa9322873427db60afc30e78dac57e5` | `main.py` | `CLI` |
| `hourly_monitor.py` | Monitor orario CI/CD e notifiche | 8,048 | `7588d7b6305bb0421a73a9d4997700c1387180e48fbbd9cfea3391711a9293b0` | `hourly_monitor.py` | `MONITOR` |
| `reproduce.py` | Verifica offline deterministica baseline v1 | 800 | `8697cefb271e3ac82e9277e94e9a61e8c682831c31cb912c95fd76a35e2d0c5e` | `reproduce.py` | `AUDIT` |
| `reproducibility.py` | Framework di riproducibilita baseline | 11,368 | `1497334010d832bf6c34e5c28841acb6046a30d35bffacfe5f9de60e5b31d1ce` | `reproducibility.py` | `CORE` |
| `freeze_baseline.py` | Strumento di congelamento snapshot | 1,046 | `5b30d295617d9850a56cbda76568ec0c9315b523223246ad8dc86b96aa6ed383` | `freeze_baseline.py` | `TOOL` |
| `reproduce_candidate_experiment.py` | Verifica offline esperimenti candidati | 674 | `2809a51a393c8d9683390dda85eddd8544fff74fb6db615f974939d80864ca8d` | `reproduce_candidate_experiment.py` | `AUDIT` |
| `run_candidate_experiment.py` | Esecuzione studio statistico candidati | 1,057 | `9c21ab7308e1e77e8922c5149eb6d48dab46219f600b2073ed98b4321084a183` | `run_candidate_experiment.py` | `EXPERIMENT` |
| `run_dashboard.py` | Avvio server locale per dashboard | 1,311 | `774cc010fed7037a62cc0d841f052062fffb96dae15565649f2f6e6d033654db` | `run_dashboard.py` | `DASHBOARD` |
| `telegram_command.py` | CLI per invio comandi Telegram | 4,314 | `08c05ccf3eeb31685ba19fb94b05386a1dc0388fd8553f5b4e09999a818f0693` | `telegram_command.py` | `CLI` |
| `telegram_subscribers.py` | Interfaccia Supabase iscritti Telegram | 7,179 | `4cd1dc6e065b61f336e3f0a6fba50886ff6ae0698099c613839f83038c7b0a98` | `telegram_subscribers.py` | `DATABASE` |
| `rules.py` | Vocabolario e precedenza delle azioni | 595 | `0b9b9daec52648d77d144e9c9c5f01f5a3c90b7c255da1c033cfc324486d5951` | `strategy/rules.py` | `STRATEGY` |
| `signals.py` | Calcolo condizioni e segnali DAILY/LIVE | 12,280 | `d5c0dc7bed30e659e3fe3129eecde3b753efc5bf8e74625a417258511f34377b` | `strategy/signals.py` | `STRATEGY` |
| `technical_indicators.py` | Indicatori SMA, RSI, ATR, Momentum | 3,401 | `3941bc692f77e6ffd637337cc2df05bae2b7c9388111d4b39f38224838ad7b91` | `indicators/technical_indicators.py` | `INDICATORS` |
| `coinbase.py` | Client Coinbase Advanced Trade API | 8,290 | `206104fb141178019c1c60c2297be3514a345780b1848c1d111efb4809d368ea` | `data/coinbase.py` | `DATA` |
| `daily_candles.py` | Filtraggio candele giornaliere concluse | 1,222 | `8f825901d967be711061b484979026df51fecfce46a431689d029173fc73c8a8` | `data/daily_candles.py` | `DATA` |
| `backtest.py` | Simulatore backtest e metriche di rischio | 6,521 | `5ad70da0ac993d9ffdaf79276694f74d4400357a89b2a2cf6599f094ef438108` | `backtest/backtest.py` | `BACKTEST` |
| `generate.py` | Generatore artefatti JSON, CSV, grafici | 9,205 | `204e498361e5edad677c26fb00061351b711707219844d7093529c4e49298206` | `reports/generate.py` | `REPORT` |
| `publication.py` | Staging atomico, hash SHA-256 e rollback | 6,012 | `60b127f752b9961a07813cca6ac949a6a61c293dbd439cae486ce67b7cf53dab` | `reports/publication.py` | `CORE` |
| `state_store.py` | Persistenza stato monitor e allarmi live | 2,435 | `fb4d00dfc5925ebfeda832a5f0c7c6fda2a226636ebc36275c83043d0b40a904` | `state/state_store.py` | `STATE` |
| `telegram.py` | Formattatore messaggi e client Telegram | 3,628 | `f268b65183c4f3d7386fb80698a2f646360bf3d25624b0107fbcc5ef0def5b3d` | `notifications/telegram.py` | `NOTIFICATION` |
| `candidate_evaluation.py` | Protocollo scientifico test candidati | 23,890 | `6c3b0071d441acd60c3fa3f695ed622f26b508117c419e37c06e79820c9ce2f2` | `experiments/candidate_evaluation.py` | `EXPERIMENT` |
| `candidate_swing_sentinel.py` | Ricerca candidati Swing Sentinel (Aegis style) | 15,935 | `ff96ea9a8608fc4caa31e1ab5dd6ed8e28c6d487e4460697998608df30ce1186` | `experiments/candidate_swing_sentinel.py` | `EXPERIMENT` |
| `worker.js` | Cloudflare Worker Edge API & Webhook | 11,701 | `0ceb6709388a6134648ccbc1fe30f665d1ea470880d1219badec6905141a97f1` | `cloudflare-worker/src/worker.js` | `EDGE_WORKER` |
| `wrangler.jsonc` | Configurazione Cloudflare Worker | 365 | `14479ad160e660de5ac22f34e3115580e16564fb81223e9aeec7ec1b10a848cf` | `cloudflare-worker/wrangler.jsonc` | `CONFIG` |
| `package.json` | Dipendenze Cloudflare Worker | 217 | `c1a8129e448f0c77052d10ca3746f09de00e5f1e68fe8fbf0f8a287fc928902c` | `cloudflare-worker/package.json` | `CONFIG` |
| `verify_manifests.py` | Verificatore integrita crittografica | 3,995 | `fbb691b78008580bca2701cd6af5fff947d220a9788d5d9e4958028b2e526025` | `tools/verify_manifests.py` | `TOOL` |
| `update_manifests.py` | Aggiornatore automatico dei manifesti | 7,534 | `d442f919c8989edb74a372cbf9ade1e7ca4ca9be53d92f775addb82d7e224eaf` | `tools/update_manifests.py` | `TOOL` |
| `test_manifests.py` | Test di integrita crittografica manifesti | 1,158 | `cbebaf8b754e164a0347b4a67f2e399bade47440a16459791ddee0f408f088a1` | `tests/test_manifests.py` | `TEST` |
