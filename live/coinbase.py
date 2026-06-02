"""
Prezzo spot "live" da Coinbase (endpoint pubblico).

Usiamo Coinbase perché:
- non richiede API key per lo spot price
- è semplice e stabile per un job schedulato (GitHub Actions).
"""

from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class SpotPrice:
    pair: str  # es. "BTC-USD" o "BTC-EUR"
    price: float


def fetch_spot_price(pair: str = "BTC-USD", timeout_s: int = 20) -> SpotPrice:
    """
    Fetch spot price da Coinbase:
    GET https://api.coinbase.com/v2/prices/<PAIR>/spot
    """
    url = f"https://api.coinbase.com/v2/prices/{pair}/spot"
    r = requests.get(url, headers={"Accept": "application/json"}, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    amount = float(data["data"]["amount"])
    return SpotPrice(pair=pair, price=amount)

