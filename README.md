# Remna Routing Updater

Микросервис для автоматического обновления `happRouting` в Remna панели при появлении новых данных в GitHub-репозитории [roscomvpn-happ-routing](https://github.com/hydraponique/roscomvpn-happ-routing).

## Как работает

1. При запуске получает текущие настройки подписки из Remna API (`GET /subscription-settings`)
2. Периодически проверяет файл `DEFAULT.DEEPLINK` в GitHub-репозитории
3. Если содержимое изменилось — отправляет обновление в Remna (`PATCH /subscription-settings`)
4. Если изменений нет — ничего не делает

## Быстрый старт

```bash
<<<<<<< Updated upstream
git clone https://github.com/lifeindarkside/Remnawave-Routing-update
cd Remnawave-Routing-update
cp .env.example .env
=======
mkdir remna-routing-updater && cd remna-routing-updater
>>>>>>> Stashed changes
```

Создайте файл `.env`:

```env
REMNA_BASE_URL=https://your-host/api
REMNA_TOKEN=your_bearer_token
```

Создайте файл `docker-compose.yml`:

```yaml
services:
  routing-updater:
    image: ghcr.io/lifeindarkside/remnawave-routing-update:latest
    container_name: remna-routing-updater
    restart: unless-stopped
    env_file:
      - .env
```

Запуск:

```bash
docker compose up -d
```

### Сборка из исходников

Если хотите собрать образ самостоятельно:

```bash
git clone https://github.com/lifeindarkside/Remnawave-Routing-update.git
cd Remnawave-Routing-update
cp .env.example .env
# отредактируйте .env
docker compose up -d --build
```

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `REMNA_BASE_URL` | да | — | Базовый URL API Remna (например `https://host/api`) |
| `REMNA_TOKEN` | да | — | Bearer-токен для авторизации в Remna API |
| `GITHUB_RAW_URL` | нет | [DEFAULT.DEEPLINK](https://raw.githubusercontent.com/hydraponique/roscomvpn-happ-routing/refs/heads/main/HAPP/DEFAULT.DEEPLINK) | URL файла с роутингом на GitHub |
| `CHECK_INTERVAL` | нет | `300` | Интервал проверки обновлений (в секундах) |

## Логи

```bash
docker compose logs -f
```

## Лицензия

MIT
