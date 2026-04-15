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
REMNA_TOKEN = os.getenv("REMNA_TOKEN", "")
GITHUB_RAW_URL = os.getenv(
    "GITHUB_RAW_URL",
    "https://raw.githubusercontent.com/hydraponique/roscomvpn-happ-routing"
    "/refs/heads/main/HAPP/DEFAULT.DEEPLINK",
)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "43200"))

# ── Настройки патча ──────────────────────────────────────────────────────────
ROUTING_NAME = os.getenv("ROUTING_NAME", "Glowshine")
FAKE_DNS = os.getenv("FAKE_DNS", "true").lower() == "true"
# ────────────────────────────────────────────────────────────────────────────


def patch_deeplink(raw_deeplink: str) -> str:
    """
    Принимает happ://routing/onadd/<base64>,
    декодирует JSON, применяет патч, возвращает новый deeplink.
    """
    prefix = "happ://routing/onadd/"
    if not raw_deeplink.startswith(prefix):
        log.warning("Неожиданный формат deeplink, патч пропущен.")
        return raw_deeplink

    b64_part = raw_deeplink[len(prefix):]

    # base64 может быть без padding — добавляем
    padding = 4 - len(b64_part) % 4
    if padding != 4:
        b64_part += "=" * padding

    try:
        payload = json.loads(base64.b64decode(b64_part).decode("utf-8"))
    except Exception as e:
        log.error("Не удалось декодировать payload: %s", e)
        return raw_deeplink

    # ── применяем изменения ──────────────────────────────────────────────────
    original_name = payload.get("Name", "")
    payload["Name"] = ROUTING_NAME
    payload.pop("FakeDns", None)  # убираем неправильный ключ если есть
    payload["FakeDNS"] = "true" if FAKE_DNS else "false"  # правильный ключ, строка
    # ────────────────────────────────────────────────────────────────────────

    log.info(
        "Патч: Name '%s' → '%s', FakeDNS → %s",
        original_name, ROUTING_NAME, payload["FakeDNS"],
    )

    new_b64 = base64.b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode().rstrip("=")

    return f"{prefix}{new_b64}"


async def fetch_deeplink(session: aiohttp.ClientSession) -> str | None:
    try:
        async with session.get(GITHUB_RAW_URL) as resp:
            resp.raise_for_status()
            return (await resp.text()).strip()
    except Exception as e:
        log.error("Ошибка получения deeplink с GitHub: %s", e)
        return None


async def get_current_routing(session: aiohttp.ClientSession) -> str | None:
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

    async with aiohttp.ClientSession() as session:
        while True:
            raw = await fetch_deeplink(session)
            if raw:
                patched = patch_deeplink(raw)
                current = await get_current_routing(session)

                if patched != current:
                    ok = await update_routing(session, patched)
                    if ok:
                        log.info("Routing обновлён успешно.")
                    else:
                        log.warning("Обновление не удалось.")
                else:
                    log.info("Изменений нет.")

            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())