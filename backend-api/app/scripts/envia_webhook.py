"""Registers (or repoints) the Envia tracking webhook at this API.

Run with: uv run python -m app.scripts.envia_webhook https://<public-host>

The public host changes on every ngrok start, so run it after each one. It
appends /api/v1/webhooks/envia?token=ENVIA_WEBHOOK_TOKEN, then updates the
account's existing type-3 (simpleTracking) webhook, or creates one. Envia's
queries API (ENVIA_QUERIES_URL) takes the same Bearer ENVIA_API_KEY.

It prints the webhook's `auth_token`: Envia signs every real delivery with it
(X-Webhook-Signature), so put it in .env as ENVIA_WEBHOOK_SECRET.
"""

import asyncio
import sys
from typing import Any

import httpx

from app.core.config import settings

SIMPLE_TRACKING = 3  # GET /webhook-types: "simpleTracking", v2 status update


async def _ours(client: httpx.AsyncClient) -> dict[str, Any] | None:
    # GET /webhooks lists `type` by name, not `type_id` (checked 2026-11-11).
    hooks = (await client.get("/webhooks")).raise_for_status().json().get("data", [])
    return next((w for w in hooks if w.get("type") == "simpleTracking"), None)


async def register(public_base_url: str) -> dict[str, Any]:
    if not settings.ENVIA_API_KEY or not settings.ENVIA_WEBHOOK_TOKEN:
        raise SystemExit("Set ENVIA_API_KEY and ENVIA_WEBHOOK_TOKEN in .env first.")
    url = (
        f"{public_base_url.rstrip('/')}{settings.API_V1_PREFIX}/webhooks/envia"
        f"?token={settings.ENVIA_WEBHOOK_TOKEN}"
    )
    headers = {"Authorization": f"Bearer {settings.ENVIA_API_KEY}"}
    async with httpx.AsyncClient(base_url=settings.ENVIA_QUERIES_URL, headers=headers, timeout=30) as client:
        existing = await _ours(client)
        if existing:
            response = await client.put(f"/webhooks/{existing['id']}", json={"url": url, "active": 1})
        else:
            response = await client.post(
                "/webhooks", json={"type_id": SIMPLE_TRACKING, "url": url, "active": 1}
            )
        response.raise_for_status()
        hook = await _ours(client)
        if hook is None:
            raise SystemExit(f"Envia accepted the webhook but doesn't list it: {response.text}")
        return hook


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: uv run python -m app.scripts.envia_webhook https://<public-host>")
    hook = asyncio.run(register(sys.argv[1]))
    print(f"Webhook {hook['id']} active={hook.get('active')} -> {sys.argv[1]}")
    print(f"ENVIA_WEBHOOK_SECRET={hook.get('auth_token')}")


if __name__ == "__main__":
    main()
