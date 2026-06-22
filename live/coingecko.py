"""
Dati market live aggregati da CoinGecko.

Usiamo CoinGecko per il LIVE perche fornisce prezzo e volume 24h aggregati
su piu mercati, a differenza dello spot Coinbase che rappresenta un singolo
exchange.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class CoinGeckoMarket:
    price_usd: float
    price_eur: float | None
    volume_24h_usd: float


def fetch_btc_market(timeout_s: int = 20) -> CoinGeckoMarket:
    """
    Recupera prezzo BTC aggregato e volume 24h da CoinGecko.

    Endpoint pubblico:
    GET https://api.coingecko.com/api/v3/coins/markets
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin",
        "per_page": 1,
        "page": 1,
        "sparkline": "false",
    }
    response = requests.get(
        url,
        params=params,
        headers={"Accept": "application/json"},
        timeout=timeout_s,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        raise RuntimeError("CoinGecko non ha restituito dati market per bitcoin.")

    row = payload[0]
    price_usd = float(row["current_price"])
    volume_24h_usd = float(row["total_volume"])

    price_eur = None
    try:
        eur_response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "eur"},
            headers={"Accept": "application/json"},
            timeout=timeout_s,
        )
        eur_response.raise_for_status()
        eur_payload = eur_response.json()
        price_eur = float(eur_payload["bitcoin"]["eur"])
    except Exception:
        price_eur = None

    return CoinGeckoMarket(
        price_usd=price_usd,
        price_eur=price_eur,
        volume_24h_usd=volume_24h_usd,
    )
