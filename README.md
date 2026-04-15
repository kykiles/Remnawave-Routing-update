# Remnawave Routing Updater (patched)

Форк [lifeindarkside/Remnawave-Routing-update](https://github.com/lifeindarkside/Remnawave-Routing-update).

Микросервис автоматически подтягивает маршруты для Happ из репозитория [hydraponique/roscomvpn-happ-routing](https://github.com/hydraponique/roscomvpn-happ-routing) и применяет их в Remnawave панели.

**Отличия от оригинала:**
- Название маршрута задаётся через `.env` переменную `ROUTING_NAME`
- `FakeDNS` задаётся через `.env` переменную `FAKE_DNS`
- Все правила маршрутизации берутся из оригинального источника без изменений

---

## Как работает

1. Каждые N секунд скачивает файл `DEFAULT.DEEPLINK` с GitHub
2. Декодирует base64 → JSON
3. Применяет патч: меняет `Name` и `FakeDNS`
4. Если содержимое изменилось — отправляет `PATCH /subscription-settings` в Remnawave API
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
[INFO] Routing name: 'МоёНазвание', FakeDns: True
[INFO] Патч: Name 'RoscomVPN' → 'МоёНазвание', FakeDns → True
[INFO] Routing обновлён успешно.
```

---

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `REMNA_BASE_URL` | ✅ | — | `https://твой-домен/api` |
| `REMNA_TOKEN` | ✅ | — | Bearer-токен Remnawave |
| `ROUTING_NAME` | ❌ | `routing_name` | Название маршрута в Happ |
| `FAKE_DNS` | ❌ | `true` | Включить FakeDNS |
| `GITHUB_RAW_URL` | ❌ | DEFAULT.DEEPLINK из roscomvpn-happ-routing | Кастомный источник маршрутов |
| `CHECK_INTERVAL` | ❌ | `43200` | Интервал проверки в секундах (43200 = 2 раза в сутки) |

---

## Изменить настройки без пересборки

```bash
nano .env          # изменяешь нужные переменные
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
"
```

---

## На какой сервер деплоить

На сервер с **панелью** Remnawave. `REMNA_BASE_URL` должен указывать на домен панели, не ноды.

---

## Лицензия

MIT