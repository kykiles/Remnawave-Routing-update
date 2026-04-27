import asyncio
import base64
import json
import logging
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

REMNA_BASE_URL = os.getenv("REMNA_BASE_URL", "").rstrip("/")
REMNA_TOKEN    = os.getenv("REMNA_TOKEN", "")
GITHUB_RAW_URL = os.getenv(
    "GITHUB_RAW_URL",
    "https://raw.githubusercontent.com/hydraponique/roscomvpn-routing"
    "/refs/heads/main/HAPP/DEFAULT.JSON",
)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "43200"))

# ── Настройки патча ───────────────────────────────────────────────────────────
ROUTING_NAME = os.getenv("ROUTING_NAME", "Glowshine")
FAKE_DNS     = os.getenv("FAKE_DNS", "true").lower() == "true"

# Дополнительные правила — перечисляются через запятую в .env
# EXTRA_PROXY=domain:gemini.google.com,domain:generativelanguage.googleapis.com
# EXTRA_DIRECT=domain:mysite.ru
# EXTRA_BLOCK=domain:ads.example.com
def _parse_list(env_key: str) -> list:
    raw = os.getenv(env_key, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]

EXTRA_PROXY  = _parse_list("EXTRA_PROXY")
EXTRA_DIRECT = _parse_list("EXTRA_DIRECT")
EXTRA_BLOCK  = _parse_list("EXTRA_BLOCK")

# Фрагментация пакетов (обход DPI)
FRAGMENT_ENABLE   = os.getenv("FRAGMENT_ENABLE", "true").lower() == "true"
FRAGMENT_PACKETS  = os.getenv("FRAGMENT_PACKETS", "tlshello")
FRAGMENT_LENGTH   = os.getenv("FRAGMENT_LENGTH", "50-100")
FRAGMENT_INTERVAL = os.getenv("FRAGMENT_INTERVAL", "5")
FRAGMENT_MAXSPLIT = os.getenv("FRAGMENT_MAXSPLIT", "100-200")

# Шум (маскировка трафика)
NOISE_ENABLE      = os.getenv("NOISE_ENABLE", "true").lower() == "true"
NOISE_PACKET_TYPE = os.getenv("NOISE_PACKET_TYPE", "base64")
NOISE_PACKET      = os.getenv("NOISE_PACKET", "7nQBAAABAAAAAAAABnQtcmluZwZtc2VkZ2UDbmV0AAABAAE=")
NOISE_DELAY       = os.getenv("NOISE_DELAY", "50")
NOISE_RAND        = os.getenv("NOISE_RAND", "1-1024")
NOISE_RAND_RANGE  = os.getenv("NOISE_RAND_RANGE", "0-255")
# ─────────────────────────────────────────────────────────────────────────────


def build_deeplink(payload: dict) -> str:
    b64 = base64.b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    return f"happ://routing/onadd/{b64}"


def patch_payload(payload: dict) -> dict:
    original_name = payload.get("Name", "")

    # Основной патч
    payload["Name"] = ROUTING_NAME
    payload.pop("FakeDns", None)
    payload["FakeDNS"] = "true" if FAKE_DNS else "false"

    # Дополнительные правила — добавляем без дублей
    for site in EXTRA_PROXY:
        if site not in payload.get("ProxySites", []):
            payload.setdefault("ProxySites", []).append(site)

    for site in EXTRA_DIRECT:
        if site not in payload.get("DirectSites", []):
            payload.setdefault("DirectSites", []).append(site)

    for site in EXTRA_BLOCK:
        if site not in payload.get("BlockSites", []):
            payload.setdefault("BlockSites", []).append(site)

    # Фрагментация
    payload["fragmentation-enable"] = FRAGMENT_ENABLE
    if FRAGMENT_ENABLE:
        payload["fragmentation-packets"]  = FRAGMENT_PACKETS
        payload["fragmentation-length"]   = FRAGMENT_LENGTH
        payload["fragmentation-interval"] = FRAGMENT_INTERVAL
        payload["fragmentation-maxsplit"] = FRAGMENT_MAXSPLIT
    else:
        for key in ("fragmentation-packets", "fragmentation-length",
                    "fragmentation-interval", "fragmentation-maxsplit"):
            payload.pop(key, None)

    # Шум
    payload["noises-enable"] = NOISE_ENABLE
    if NOISE_ENABLE:
        payload["noises-packet-type"] = NOISE_PACKET_TYPE
        payload["noises-packet"]      = NOISE_PACKET
        payload["noises-delay"]       = NOISE_DELAY
        payload["noises-rand"]        = NOISE_RAND
        payload["noises-rand-range"]  = NOISE_RAND_RANGE
    else:
        for key in ("noises-packet-type", "noises-packet", "noises-delay",
                    "noises-rand", "noises-rand-range"):
            payload.pop(key, None)

    log.info(
        "Патч: Name '%s' → '%s', FakeDNS → %s, Fragment → %s, Noise → %s",
        original_name, ROUTING_NAME, payload["FakeDNS"],
        FRAGMENT_ENABLE, NOISE_ENABLE,
    )
    if EXTRA_PROXY:
        log.info("  + ProxySites: %s", ", ".join(EXTRA_PROXY))
    if EXTRA_DIRECT:
        log.info("  + DirectSites: %s", ", ".join(EXTRA_DIRECT))
    if EXTRA_BLOCK:
        log.info("  + BlockSites: %s", ", ".join(EXTRA_BLOCK))

    return payload


async def fetch_routing_json(session: aiohttp.ClientSession) -> dict:
    try:
        async with session.get(GITHUB_RAW_URL) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)
    except Exception as e:
        log.error("Ошибка получения JSON с GitHub: %s", e)
        return None


async def get_current_routing(session: aiohttp.ClientSession) -> str:
    url = f"{REMNA_BASE_URL}/subscription-settings"
    headers = {"Authorization": f"Bearer {REMNA_TOKEN}"}
    try:
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("response", {}).get("happRouting")
    except Exception as e:
        log.error("Ошибка получения настроек Remna: %s", e)
        return None


async def update_routing(session: aiohttp.ClientSession, deeplink: str) -> bool:
    url = f"{REMNA_BASE_URL}/subscription-settings"
    headers = {
        "Authorization": f"Bearer {REMNA_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        async with session.patch(
            url,
            headers=headers,
            json={
                "uuid": "00000000-0000-0000-0000-000000000000",
                "happRouting": deeplink,
            },
        ) as resp:
            resp.raise_for_status()
            return True
    except Exception as e:
        log.error("Ошибка обновления Remna: %s", e)
        return False


async def main() -> None:
    if not REMNA_BASE_URL or not REMNA_TOKEN:
        raise SystemExit("REMNA_BASE_URL и REMNA_TOKEN обязательны")

    log.info("Запуск. Интервал проверки: %ds", CHECK_INTERVAL)
    log.info("Routing name: '%s', FakeDNS: %s", ROUTING_NAME, FAKE_DNS)
    log.info("Fragment: %s, Noise: %s", FRAGMENT_ENABLE, NOISE_ENABLE)

    async with aiohttp.ClientSession() as session:
        while True:
            payload = await fetch_routing_json(session)

            if payload:
                payload  = patch_payload(payload)
                deeplink = build_deeplink(payload)
                current  = await get_current_routing(session)

                if deeplink != current:
                    ok = await update_routing(session, deeplink)
                    if ok:
                        log.info("Routing обновлён успешно.")
                    else:
                        log.warning("Обновление не удалось.")
                else:
                    log.info("Изменений нет.")

            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
