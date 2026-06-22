"""
Scaricamento dati giornalieri da Yahoo Finance via yfinance.

Note:
- Usiamo l'intervallo daily (1d).
- La strategia lavora su Close, High, Low, Volume.
- Salviamo un CSV locale per evitare download ripetuti.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

from config import CFG


def _default_output_path(symbol: str) -> Path:
    return Path(__file__).resolve().parents[1] / "data" / f"{symbol}_daily.csv"


def fetch_btc_daily_csv(
    symbol: str | None = None,
    force_download: bool = False,
    is_optional: bool = False,
) -> Path | None:
    """
    Scarica i dati e li salva in /data.

    Returns
    -------
    Path | None
        Percorso del CSV locale, o None se opzionale ed errore.
    """
    symbol = symbol or CFG.symbol
    out_path = _default_output_path(symbol)

    if out_path.exists() and not force_download:
        return out_path

    try:
        # yfinance:
        # - auto_adjust=False per mantenere i valori OHLC "originali"
        # - progress=False per output pulito
        df = yf.download(
            symbol,
            start=CFG.start_date,
            end=None if CFG.end_date == "today" else CFG.end_date,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
        )

        if df is None or df.empty:
            raise RuntimeError(f"Nessun dato scaricato per {symbol}.")

        # yfinance può restituire colonne MultiIndex (es. livello "Price" / "Ticker").
        # Appiattiamo subito per salvare un CSV "pulito" e consistente.
        df = df.copy()
        df.index = pd.to_datetime(df.index)

        if isinstance(df.columns, pd.MultiIndex):
            # In genere il livello 0 contiene i nomi Open/High/Low/Close/Volume.
            df.columns = df.columns.get_level_values(0)

        keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[keep_cols].copy()

        # Salviamo sempre con una colonna "Date" esplicita, evitando header multipli.
        df_out = df.reset_index().rename(columns={"index": "Date", "Date": "Date"})

        out_path.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(out_path, index=False)
        return out_path
    except Exception as e:
        if out_path.exists():
            print(
                f"ATTENZIONE: Fallito download dati per {symbol}: {e}. "
                f"Uso il file storico esistente: {out_path}"
            )
            return out_path

        if is_optional:
            print(f"ATTENZIONE: Fallito download dati per {symbol}: {e}. Continuo con il workflow.")
            return None
        else:
            raise



def load_daily_csv(csv_path: str | Path) -> pd.DataFrame:
    """
    Carica il CSV locale (/data/*_daily.csv) in un DataFrame.
    """
    csv_path = Path(csv_path)
    # Ci sono 2 formati possibili:
    # 1) "pulito" (quello che vogliamo): colonne semplici con "Date" + OHLCV
    # 2) CSV prodotto da yfinance/pandas con MultiIndex columns (2 righe header)
    #    + una riga extra "Date,,,,," prima dei dati (come nel tuo errore).
    #
    # Per essere robusti su Windows e su diverse versioni di yfinance/pandas,
    # proviamo prima il formato semplice e, se non troviamo Date, facciamo fallback.
    try:
        df_simple = pd.read_csv(csv_path)
        if "Date" in df_simple.columns:
            df_simple["Date"] = pd.to_datetime(df_simple["Date"])
            df_simple = df_simple.sort_values("Date").set_index("Date")
            return df_simple
    except Exception:
        # andiamo in fallback sotto
        pass

    # Fallback: prova a leggere come CSV con intestazione su 2 righe (MultiIndex)
    df = pd.read_csv(csv_path, header=[0, 1])

    # La prima colonna è la data, ma può avere un nome MultiIndex tipo ("Price","Ticker").
    date_col = df.columns[0]

    # Elimina l'eventuale riga "Date,,,,," che appare come prima riga dati
    # (in quel caso, la "data" è la stringa "Date").
    first_col = df[date_col].astype(str)
    df = df.loc[first_col.str.lower().ne("date")].copy()

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df = df.sort_values(date_col).set_index(date_col)

    # Appiattisce le colonne MultiIndex tenendo il livello 0: Open/High/Low/Close/Volume
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Keep only standard OHLCV (alcuni download includono anche "Adj Close")
    keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep_cols].copy()

    # Cast numerico robusto
    for c in keep_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["Close"])
    df.index.name = "Date"
    return df

