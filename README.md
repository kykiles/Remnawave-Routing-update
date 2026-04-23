# Remnawave Routing Updater

[![Build and Push Docker Image](https://github.com/kykiles/Remnawave-Routing-update/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/kykiles/Remnawave-Routing-update/actions/workflows/docker-publish.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Форк [lifeindarkside/Remnawave-Routing-update](https://github.com/lifeindarkside/Remnawave-Routing-update).

Микросервис автоматически подтягивает маршруты для Happ из репозитория [hydraponique/roscomvpn-routing](https://github.com/hydraponique/roscomvpn-routing) и применяет их в Remnawave панели.

**Отличия от оригинала:**
- Источник — `DEFAULT.JSON` из `roscomvpn-routing` (первоисточник, обновляется автоматически)
- Название маршрута задаётся через `.env` переменную `ROUTING_NAME`
- `FakeDNS` задаётся через `.env` переменную `FAKE_DNS`
- Поддержка кастомных правил через `EXTRA_PROXY`, `EXTRA_DIRECT`, `EXTRA_BLOCK`
- Исправлена совместимость с Remnawave API (обязательный `uuid` в PATCH-запросе)
- Все базовые правила маршрутизации берутся из оригинального источника без изменений

---

## Как работает

1. Каждые N секунд скачивает `DEFAULT.JSON` с GitHub
2. Применяет патч: меняет `Name` и `FakeDNS`, добавляет кастомные правила
3. Кодирует JSON в base64 → собирает `happ://routing/onadd/<base64>`
4. Если deeplink изменился — отправляет `PATCH /subscription-settings` в Remnawave API
5. Если изменений нет — ничего не делает

---

## Быстрый старт

### 1. Создай директорию и клонируй репо

```bash
mkdir -p /opt/remna-routing-updater
cd /opt/remna-routing-updater
git clone https://github.com/kykiles/Remnawave-Routing-update.git .
```

### 2. Получи API-токен Remnawave

Remnawave панель → **Settings → API Tokens → Create Token**

Скопируй токен — он показывается только один раз.

### 3. Создай `.env`

```bash
cp .env.example .env
nano .env
```

```env
REMNA_BASE_URL=https://твой-домен/api
REMNA_TOKEN=вставь_токен_сюда
ROUTING_NAME=МоёНазвание
FAKE_DNS=true
```

### 4. Запусти

```bash
docker compose build
docker compose up -d
```

### 5. Проверь логи

```bash
docker compose logs -f
```

Нормальный вывод:
```
[INFO] Запуск. Интервал проверки: 43200s
[INFO] Routing name: 'МоёНазвание', FakeDNS: True
[INFO] Патч: Name 'RoscomVPN' → 'МоёНазвание', FakeDNS → true
[INFO] Routing обновлён успешно.
```

---

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `REMNA_BASE_URL` | ✅ | — | `https://твой-домен/api` |
| `REMNA_TOKEN` | ✅ | — | Bearer-токен Remnawave |
| `ROUTING_NAME` | ❌ | `Твой маршрут` | Название маршрута в Happ |
| `FAKE_DNS` | ❌ | `true` | Включить FakeDNS |
| `EXTRA_PROXY` | ❌ | — | Добавить домены в ProxySites (через запятую) |
| `EXTRA_DIRECT` | ❌ | — | Добавить домены в DirectSites (через запятую) |
| `EXTRA_BLOCK` | ❌ | — | Добавить домены в BlockSites (через запятую) |
| `GITHUB_RAW_URL` | ❌ | DEFAULT.JSON из roscomvpn-routing | Кастомный источник маршрутов |
| `CHECK_INTERVAL` | ❌ | `43200` | Интервал проверки в секундах (43200 = 2 раза в сутки) |

### Формат значений EXTRA_*

```env
# Конкретный домен и все поддомены:
EXTRA_PROXY=domain:gemini.google.com,domain:generativelanguage.googleapis.com

# Категория из geosite:
EXTRA_PROXY=geosite:google

# Несколько значений:
EXTRA_PROXY=domain:gemini.google.com,domain:aistudio.google.com,geosite:openai
```

---

## Если панель в Docker на том же сервере

Добавь в `docker-compose.yml` секцию networks и используй внутреннее имя контейнера:

```env
REMNA_BASE_URL=http://remnawave:3000/api
```

---

## Изменить настройки без пересборки

```bash
nano .env
docker compose restart
```

---

## Проверить что маршрут применился

```bash
curl -s \
  -H "Authorization: Bearer ВАШ_ТОКЕН" \
  https://твой-домен/api/subscription-settings \
  | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
hr = data['response']['happRouting']
b64 = hr.split('/')[-1]
b64 += '=' * (4 - len(b64) % 4)
decoded = json.loads(base64.b64decode(b64))
print('Name:', decoded.get('Name'))
print('FakeDNS:', decoded.get('FakeDNS'))
print('ProxySites:', decoded.get('ProxySites'))
"
```

---

## На какой сервер деплоить

На сервер с **панелью** Remnawave. `REMNA_BASE_URL` должен указывать на домен панели, не ноды.

---

## Лицензия

MIT
