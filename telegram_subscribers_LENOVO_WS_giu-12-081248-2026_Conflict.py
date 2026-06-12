"""Accesso server-side agli iscritti Telegram memorizzati su Supabase."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import requests


TABLE_NAME = "telegram_subscribers"


@dataclass(frozen=True)
class TelegramSubscriber:
    telegram_chat_id: int
    telegram_user_id: int | None
    telegram_username: str | None
    telegram_first_name: str | None
    telegram_language_code: str | None


class SupabaseSubscriberStore:
    """Repository minimo basato sulle API REST generate da Supabase."""

    def __init__(self, base_url: str, service_role_key: str, timeout_s: int = 8):
        self.table_url = f"{base_url.rstrip('/')}/rest/v1/{TABLE_NAME}"
        self.timeout_s = timeout_s
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }

    def subscribe(self, subscriber: TelegramSubscriber) -> None:
        """Crea o riattiva un'iscrizione senza produrre duplicati."""
        now = _utc_now()
        payload = {
            **asdict(subscriber),
            "active": True,
            "subscribed_at": now,
            "unsubscribed_at": None,
            "consent_version": "v1",
            "consent_source": "telegram_command",
            "delivery_failures": 0,
            "last_delivery_error": None,
            "last_delivery_error_at": None,
        }
        response = requests.post(
            self.table_url,
            params={"on_conflict": "telegram_chat_id"},
            headers={
                **self.headers,
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            json=payload,
            timeout=self.timeout_s,
        )
        response.raise_for_status()

    def unsubscribe(self, telegram_chat_id: int) -> bool:
        """Disattiva l'iscrizione e indica se una riga era presente."""
        response = requests.patch(
            self.table_url,
            params={
                "telegram_chat_id": f"eq.{telegram_chat_id}",
                "select": "telegram_chat_id",
            },
            headers={**self.headers, "Prefer": "return=representation"},
            json={
                "active": False,
                "unsubscribed_at": _utc_now(),
            },
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        result = response.json()
        return isinstance(result, list) and bool(result)

    def count_active(self) -> int:
        """Conta gli iscritti attivi senza scaricare dati personali."""
        response = requests.get(
            self.table_url,
            params={
                "active": "eq.true",
                "select": "telegram_chat_id",
            },
            headers={
                **self.headers,
                "Prefer": "count=exact",
                "Range": "0-0",
            },
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        content_range = response.headers.get("Content-Range", "")
        if "/" not in content_range:
            raise ValueError("Supabase non ha restituito il conteggio richiesto.")

        total = content_range.rsplit("/", maxsplit=1)[1]
        if not total.isdigit():
            raise ValueError("Conteggio Supabase non valido.")
        return int(total)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
