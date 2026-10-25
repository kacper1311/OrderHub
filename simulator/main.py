"""Symulator kanałów sprzedaży.

Co SIMULATOR_INTERVAL sekund wysyła losowe zamówienie na webhook losowego kanału.
Czasem celowo wysyła duplikat (oczekiwane 409) albo nieznany SKU (oczekiwane 422),
żeby było widać, że backend poprawnie je odrzuca.
"""
import logging
import os
import random
import time
import uuid
from decimal import Decimal

import httpx
from faker import Faker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("simulator")
logging.getLogger("httpx").setLevel(logging.WARNING)  # bez osobnej linii dla każdego żądania

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1").rstrip("/")
INTERVAL = float(os.getenv("SIMULATOR_INTERVAL", "10"))
DUPLICATE_RATE = float(os.getenv("SIMULATOR_DUPLICATE_RATE", "0.1"))
UNKNOWN_SKU_RATE = float(os.getenv("SIMULATOR_UNKNOWN_SKU_RATE", "0.05"))


def parse_channels(raw: str) -> dict[str, str]:
    # Format: "sklep-a:sekretA,sklep-b:sekretB"
    channels = {}
    for entry in filter(None, (part.strip() for part in raw.split(","))):
        code, _, secret = entry.partition(":")
        if not code or not secret:
            raise RuntimeError(f"Zły wpis w SIMULATOR_CHANNELS: {entry!r} (oczekiwano kod:sekret)")
        channels[code] = secret
    return channels


CHANNELS = parse_channels(os.getenv("SIMULATOR_CHANNELS", ""))
SKUS = [sku.strip() for sku in os.getenv("SIMULATOR_SKUS", "").split(",") if sku.strip()]
if not CHANNELS or not SKUS:
    raise RuntimeError("Ustaw SIMULATOR_CHANNELS i SIMULATOR_SKUS w pliku .env")

fake = Faker("pl_PL")
# Ostatnie wysłane zamówienie per kanał – do symulowania duplikatów
last_sent: dict[str, dict] = {}


def random_order(channel_code: str) -> dict:
    items = []
    for sku in random.sample(SKUS, k=random.randint(1, min(3, len(SKUS)))):
        items.append({
            "sku": sku,
            "quantity": random.randint(1, 3),
            "unitPrice": str(Decimal(random.randint(999, 19999)) / 100),
        })
    if random.random() < UNKNOWN_SKU_RATE:
        items.append({"sku": f"NIEZNANY-{random.randint(100, 999)}", "quantity": 1, "unitPrice": "9.99"})

    return {
        "externalOrderId": f"{channel_code.upper()}-{uuid.uuid4().hex[:10].upper()}",
        "customer": {
            "name": fake.name(),
            "email": fake.email(),
            "address": fake.address().replace("\n", ", "),
        },
        "items": items,
    }


def wait_for_backend(client: httpx.Client) -> None:
    while True:
        try:
            if client.get(f"{BACKEND_URL}/health").status_code == 200:
                log.info("Backend dostępny pod %s", BACKEND_URL)
                return
        except httpx.HTTPError:
            pass
        log.info("Czekam na backend...")
        time.sleep(2)


def send_one(client: httpx.Client) -> None:
    channel_code = random.choice(list(CHANNELS))
    if channel_code in last_sent and random.random() < DUPLICATE_RATE:
        order, kind = last_sent[channel_code], "duplikat"
    else:
        order, kind = random_order(channel_code), "nowe"

    response = client.post(
        f"{BACKEND_URL}/webhooks/{channel_code}",
        json=order,
        headers={"X-Webhook-Secret": CHANNELS[channel_code]},
    )
    if response.status_code == 201:
        last_sent[channel_code] = order
        log.info("[%s] %s %s -> 201 %s", channel_code, kind, order["externalOrderId"], response.json()["status"])
    else:
        log.warning("[%s] %s %s -> %s %s", channel_code, kind, order["externalOrderId"],
                    response.status_code, response.json().get("detail"))


def main() -> None:
    log.info("Kanały: %s, SKU: %s, interwał: %ss", ", ".join(CHANNELS), ", ".join(SKUS), INTERVAL)
    with httpx.Client(timeout=10) as client:
        wait_for_backend(client)
        while True:
            try:
                send_one(client)
            except httpx.HTTPError as e:
                log.error("Błąd połączenia: %s", e)
            time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
