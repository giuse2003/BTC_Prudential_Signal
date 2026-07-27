"""Dati pubblici Coinbase per BTC-USD Signal.

Le candele sono giornaliere UTC del mercato Coinbase BTC-USD. Il file locale
e' una cache della stessa sorgente, mai un fallback verso provider differenti.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from config import CFG
from data.daily_candles import keep_closed_daily_candles

BASE_URL = "https://api.coinbase.com/api/v3/brokerage/market"
MAX_CANDLES = 300
CHUNK_DAYS = 299
USER_AGENT = "BTC-USD-Signal/1.0"


@dataclass(frozen=True)
class MarketSnapshot:
    product_id: str
    price: float
    volume_24h: float | None


def _default_cache_path(product_id: str) -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "data" / f"{product_id}_coinbase_daily.csv"


def _request_json(
    url: str,
    *,
    params: dict[str, str | int] | None = None,
    timeout_s: int = 20,
    max_attempts: int = 4,
    session: requests.Session | None = None,
) -> dict:
    client = session or requests.Session()
    headers = {
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "User-Agent": USER_AGENT,
    }
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = client.get(url, params=params, headers=headers, timeout=timeout_s)
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(
                    f"Coinbase HTTP {response.status_code}", response=response
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Risposta Coinbase non valida.")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt + 1 < max_attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Coinbase non raggiungibile dopo {max_attempts} tentativi: {last_error}")


def fetch_product_snapshot(
    product_id: str,
    *,
    timeout_s: int = 20,
    session: requests.Session | None = None,
) -> MarketSnapshot:
    payload = _request_json(
        f"{BASE_URL}/products/{product_id}",
        timeout_s=timeout_s,
        session=session,
    )
    price = float(payload["price"])
    volume_raw = payload.get("volume_24h")
    volume = float(volume_raw) if volume_raw not in (None, "") else None
    if price <= 0 or (volume is not None and volume < 0):
        raise ValueError(f"Snapshot Coinbase {product_id} non valido.")
    return MarketSnapshot(product_id=product_id, price=price, volume_24h=volume)


def _parse_candles(payload: dict) -> pd.DataFrame:
    candles = payload.get("candles")
    if not isinstance(candles, list):
        raise ValueError("La risposta Coinbase non contiene 'candles'.")
    rows = []
    for candle in candles:
        rows.append(
            {
                "Date": pd.to_datetime(int(candle["start"]), unit="s", utc=True).tz_localize(None),
                "Open": float(candle["open"]),
                "High": float(candle["high"]),
                "Low": float(candle["low"]),
                "Close": float(candle["close"]),
                "Volume": float(candle["volume"]),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    return pd.DataFrame(rows).set_index("Date").sort_index()


def _download_candles(
    product_id: str,
    start: date,
    end_exclusive: date,
    *,
    timeout_s: int = 20,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    cursor = start
    while cursor < end_exclusive:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end_exclusive)
        start_ts = int(datetime.combine(cursor, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        end_ts = int(datetime.combine(chunk_end, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        payload = _request_json(
            f"{BASE_URL}/products/{product_id}/candles",
            params={
                "start": str(start_ts),
                "end": str(end_ts),
                "granularity": "ONE_DAY",
                "limit": MAX_CANDLES,
            },
            timeout_s=timeout_s,
            session=session,
        )
        frame = _parse_candles(payload)
        if not frame.empty:
            frames.append(frame)
        cursor = chunk_end
    if not frames:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    result = pd.concat(frames).sort_index()
    return result[~result.index.duplicated(keep="last")]


def load_cached_candles(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    frame.index = pd.DatetimeIndex(frame.index).tz_localize(None)
    return frame.sort_index()


def validate_daily_candles(frame: pd.DataFrame) -> None:
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing_columns = required.difference(frame.columns)
    if frame.empty or missing_columns:
        raise ValueError(f"Dataset Coinbase vuoto o incompleto: {sorted(missing_columns)}")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Date Coinbase duplicate o non ordinate.")
    numeric = frame[list(required)]
    if numeric.isna().any().any() or (numeric[["Open", "High", "Low", "Close"]] <= 0).any().any():
        raise ValueError("Valori OHLCV Coinbase mancanti o non validi.")
    expected = pd.date_range(frame.index[0], frame.index[-1], freq="D")
    missing_days = expected.difference(frame.index)
    if len(missing_days):
        preview = ", ".join(day.strftime("%Y-%m-%d") for day in missing_days[:5])
        raise ValueError(f"Mancano {len(missing_days)} candele giornaliere Coinbase: {preview}")


def fetch_daily_candles(
    product_id: str = CFG.product_id,
    *,
    start_date: str = CFG.start_date,
    cache_path: str | Path | None = None,
    refresh_all: bool = False,
    as_of: str | date | None = None,
    now_utc: datetime | pd.Timestamp | None = None,
    timeout_s: int = 20,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Aggiorna la cache Coinbase e restituisce solo candele daily concluse."""
    current = pd.Timestamp.now(tz="UTC") if now_utc is None else pd.Timestamp(now_utc)
    current = current.tz_localize("UTC") if current.tzinfo is None else current.tz_convert("UTC")
    cutoff_date = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
    last_included_date = cutoff_date or (current.date() - timedelta(days=1))
    end_exclusive = last_included_date + timedelta(days=1)
    path = Path(cache_path) if cache_path is not None else _default_cache_path(product_id)
    cached: pd.DataFrame | None = None
    if path.exists() and not refresh_all:
        cached = load_cached_candles(path)

    requested_start = date.fromisoformat(start_date)
    fetch_start = requested_start
    if cached is not None and not cached.empty:
        fetch_start = max(requested_start, cached.index[-1].date() - timedelta(days=2))

    try:
        downloaded = _download_candles(
            product_id,
            fetch_start,
            end_exclusive,
            timeout_s=timeout_s,
            session=session,
        )
    except RuntimeError:
        if cached is None or cached.empty:
            raise
        downloaded = pd.DataFrame(columns=cached.columns)

    frames = [frame for frame in (cached, downloaded) if frame is not None and not frame.empty]
    if not frames:
        raise RuntimeError(f"Nessuna candela Coinbase disponibile per {product_id}.")
    merged = pd.concat(frames).sort_index()
    merged = merged[~merged.index.duplicated(keep="last")]
    cutoff_utc = pd.Timestamp(end_exclusive, tz="UTC")
    merged = keep_closed_daily_candles(merged, now_utc=cutoff_utc)
    validate_daily_candles(merged)

    path.parent.mkdir(parents=True, exist_ok=True)
    output = merged.copy()
    output.index.name = "Date"
    output.to_csv(path)
    return merged
