# Quotazione BTC/EUR

Piccola dashboard locale per monitorare la quotazione **Bitcoin (BTC)** rispetto all'**Euro (EUR)** usando l'endpoint pubblico di Coinbase:

- `https://api.coinbase.com/v2/prices/BTC-EUR/spot`

## Avvio

### Opzione A (più semplice)

Apri `index.html` con il browser.

### Opzione B (consigliata: mini server locale)

Se hai Python installato:

```powershell
cd "C:\Users\giuse\Quotazione EUR-BTC"
python -m http.server 5173
```

Poi apri `http://localhost:5173`.

## Note

- Mostra lo **spot price** (1 BTC in EUR) e mantiene uno **storico** (massimo 50 righe) in `localStorage`.
- Refresh automatico configurabile (di default **10s**).

