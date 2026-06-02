"""
Job "hourly" pensato per GitHub Actions (piano gratuito).

Comportamento:
- Scarica/aggiorna dati giornalieri BTC-USD (Yahoo Finance) e calcola indicatori giornalieri.
- Calcola punteggio + segnale "di regime" (prudente).
- Legge prezzo spot "live" da Coinbase (di default BTC-USD, configurabile).
- Invia notifica Telegram SOLO se:
  - cambia il segnale rispetto al run precedente, oppure
  - scatta un evento "livello importante" (attraversamento SMA200 / High52w / Low52w), oppure
  - il segnale è (o diventa) RIDURRE ESPOSIZIONE.

Persistenza:
- salva uno state.json in `.state/` che viene cache-ato dal workflow.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from data.fetch_yahoo import fetch_btc_daily_csv, load_daily_csv
from indicators.technical_indicators import compute_all_indicators
from live.coinbase import fetch_spot_price
from notifications.telegram import TelegramConfig, send_telegram_message
from strategy.signals import compute_signals
from state.state_store import MonitorState, load_state, save_state


def _fmt_money(x: float, currency: str) -> str:
    if currency == "EUR":
        return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{x:,.2f} {currency}"


def _detect_level_events(
    prev_spot: float | None,
    spot: float,
    sma200: float | None,
    high52w: float | None,
    low52w: float | None,
) -> list[str]:
    """
    Rileva attraversamenti tra prev_spot -> spot.
    """
    events: list[str] = []
    if prev_spot is None:
        return events

    def crossed(level: float, direction: str) -> bool:
        if direction == "up":
            return prev_spot < level <= spot
        return prev_spot > level >= spot

    if sma200 and pd.notna(sma200):
        if crossed(float(sma200), "up"):
            events.append("Cross UP SMA200")
        elif crossed(float(sma200), "down"):
            events.append("Cross DOWN SMA200")

    if high52w and pd.notna(high52w) and crossed(float(high52w), "up"):
        events.append("New 52w High breakout")

    if low52w and pd.notna(low52w) and crossed(float(low52w), "down"):
        events.append("New 52w Low breakdown")

    return events


def _action_from_context(signal: str, level_events: list[str]) -> str | None:
    """
    Decide l'azione che vogliamo comunicare.

    Formato richiesto:
    - "Acquista: motivazione"
    - "Vendi: motivazione"

    Regole conservative:
    - se il segnale è RIDURRE ESPOSIZIONE => Vendi
    - altrimenti, se abbiamo un "Cross DOWN SMA200" o "52w Low breakdown" => Vendi
    - altrimenti, se il segnale è in zona acquisto/accumulo => Acquista
    - altrimenti, nessuna azione (non notifichiamo per EVITARE senza eventi)
    """
    buy_signals = {"ACCUMULO GRADUALE", "ACQUISTO", "ACQUISTO FORTE"}

    if signal == "RIDURRE ESPOSIZIONE":
        return "Vendi"

    for e in level_events:
        if "Cross DOWN SMA200" in e or "52w Low breakdown" in e:
            return "Vendi"

    for e in level_events:
        if "Cross UP SMA200" in e or "52w High breakout" in e:
            # Se rompe livelli al rialzo e regime è buy-ish, manteniamo buy.
            # Se regime non è buy-ish, lasciamo comunque "Acquista" solo se segnale lo supporta.
            break

    if signal in buy_signals:
        return "Acquista"

    return None


def _build_motivation(
    *,
    date: str,
    live_pair: str,
    spot: float,
    live_ccy: str,
    signal: str,
    score: float,
    sma50: float | None,
    sma200: float | None,
    rsi: float | None,
    atr: float | None,
    level_events: list[str],
    reasons: list[str],
    sell_reason: str | None,
) -> str:
    """
    Genera una motivazione breve (una sola riga) adatta a Telegram.
    """
    bits: list[str] = []
    bits.append(f"daily {date}")
    bits.append(f"segnale={signal} punteggio={score:.0f}/100")
    bits.append(f"spot {live_pair}={_fmt_money(spot, live_ccy)}")
    if sma200 is not None:
        bits.append(f"SMA200={sma200:.0f}")
    if sma50 is not None:
        bits.append(f"SMA50={sma50:.0f}")
    if rsi is not None:
        bits.append(f"RSI={rsi:.1f}")
    if atr is not None:
        bits.append(f"ATR={atr:.0f}")
    if level_events:
        bits.append("livelli=" + ",".join(level_events))
    if sell_reason:
        bits.append(f"rischio={sell_reason}")
    if reasons:
        bits.append("trigger=" + "; ".join(reasons))
    return " | ".join(bits)


def main() -> None:
    # Telegram secrets (GitHub Actions -> Settings -> Secrets and variables -> Actions)
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise RuntimeError("Mancano TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nelle variabili d'ambiente.")

    # Coppia spot live (Coinbase). Default: BTC-USD per coerenza con Yahoo BTC-USD.
    live_pair = os.environ.get("LIVE_PAIR", "BTC-USD").strip()
    live_ccy = live_pair.split("-")[-1] if "-" in live_pair else "USD"

    project_root = Path(__file__).resolve().parent
    state_path = project_root / ".state" / "state.json"

    # 1) Stato precedente
    state = load_state(state_path)

    # 2) Dati giornalieri + indicatori
    csv_path = fetch_btc_daily_csv(symbol="BTC-USD", force_download=True)
    df = load_daily_csv(csv_path)
    df_ind = compute_all_indicators(df)
    df_sig = compute_signals(df_ind)

    latest = df_sig.iloc[-1]
    date = df_sig.index[-1].strftime("%Y-%m-%d")
    signal = str(latest["Segnale"])
    score = float(latest["Punteggio"])
    sma200 = float(latest["SMA200"]) if pd.notna(latest["SMA200"]) else None
    sma50 = float(latest["SMA50"]) if pd.notna(latest["SMA50"]) else None
    rsi = float(latest["RSI"]) if pd.notna(latest["RSI"]) else None
    atr = float(latest["ATR"]) if pd.notna(latest["ATR"]) else None
    high52w = float(latest["High52w"]) if pd.notna(latest["High52w"]) else None
    low52w = float(latest["Low52w"]) if pd.notna(latest["Low52w"]) else None
    sell_reason = str(latest.get("SellReason")) if pd.notna(latest.get("SellReason")) else None

    # 3) Prezzo spot live
    spot = fetch_spot_price(pair=live_pair).price

    # 4) Eventi
    level_events = _detect_level_events(state.last_spot_price, spot, sma200, high52w, low52w)
    signal_changed = (state.last_signal is not None) and (signal != state.last_signal)

    must_notify = False
    reasons: list[str] = []

    if signal_changed:
        must_notify = True
        reasons.append(f"Cambio segnale: {state.last_signal} → {signal}")

    if signal == "RIDURRE ESPOSIZIONE":
        # prudenziale: se siamo in riduzione, notifichiamo (almeno una volta)
        if state.last_signal != "RIDURRE ESPOSIZIONE":
            must_notify = True
            reasons.append("Condizione di rischio: RIDURRE ESPOSIZIONE")

    # Livelli importanti: notifichiamo solo se ci sono eventi e non è lo stesso evento già notificato nel run precedente.
    if level_events:
        # Dedup semplice: se l'evento principale è lo stesso di prima, non spammiamo.
        primary = level_events[0]
        if primary != state.last_level_event:
            must_notify = True
            reasons.append("Livello importante: " + ", ".join(level_events))

    # Applichiamo il formato richiesto: notifichiamo solo se possiamo produrre "Acquista" o "Vendi".
    action = _action_from_context(signal, level_events)
    if action is None:
        must_notify = False

    # 5) Invio Telegram (solo se serve)
    if must_notify:
        cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)

        motivation = _build_motivation(
            date=date,
            live_pair=live_pair,
            spot=float(spot),
            live_ccy=live_ccy,
            signal=signal,
            score=score,
            sma50=sma50,
            sma200=sma200,
            rsi=rsi,
            atr=atr,
            level_events=level_events,
            reasons=reasons,
            sell_reason=sell_reason,
        )
        send_telegram_message(cfg, f"{action}: {motivation}")

    # 6) Salvataggio stato
    state.last_signal = signal
    state.last_spot_price = float(spot)
    state.last_level_event = level_events[0] if level_events else state.last_level_event
    save_state(state_path, state)


if __name__ == "__main__":
    main()

