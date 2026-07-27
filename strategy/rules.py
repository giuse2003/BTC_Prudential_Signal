"""Contratto operativo unico della strategia BTC-USD Signal."""

from __future__ import annotations

ACTION_BUY = "ACQUISTA"
ACTION_HOLD = "MANTIENI STATO ATTUALE"
ACTION_SELL = "VENDI"
VALID_ACTIONS = frozenset({ACTION_BUY, ACTION_HOLD, ACTION_SELL})


def action_from_conditions(
    buy_statuses: list[bool],
    sell_statuses: list[bool],
) -> str:
    """Applica le regole pubblicate; la vendita ha sempre la precedenza."""
    if any(sell_statuses):
        return ACTION_SELL
    if buy_statuses and all(buy_statuses):
        return ACTION_BUY
    return ACTION_HOLD
