# RDS-2P-assistants-skills

[![Deploy](https://github.com/ShiWarai/RDS-2P-assistants-skills/actions/workflows/deploy.yml/badge.svg)](https://github.com/ShiWarai/RDS-2P-assistants-skills/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/github/license/ShiWarai/RDS-2P-assistants-skills)](https://opensource.org/licenses/MIT)
![Python Version](https://img.shields.io/badge/python-3.10-blue)
![Docker Ready](https://img.shields.io/badge/docker-ready-blue?logo=docker)

Сервер веб-хуков для управления роботом-пандой через голосовые команды в **Сбер Салют** и **Яндекс Алису**. Привязка пользователь ↔ робот, классификация намерений через CVC, доставка команд роботам через внутрикластерный **robot-gateway** (gRPC).

## Стек технологий

| Категория       | Технологии                                                                 |
| --------------- | --------------------------------------------------------------------------- |
| API             | FastAPI, Uvicorn                                                            |
| Данные          | Redis (привязки, состояния диалога)                                         |
| Роботы          | gRPC (Stream), Protobuf                                                     |
| NLP             | [CVC](https://github.com/ShiWarai/CVC) (внешний сервис классификации команд) |
| Архитектура     | Clean Architecture (Domain, Application, Infrastructure, Presentation)     |
| Инфраструктура  | Docker, Docker Compose                                                      |
| Разработка      | pytest, ruff, fakeredis                                                      |

## Оглавление

| Раздел | Содержание |
| ------ | ---------- |
| [Быстрый старт](#быстрый-старт) | Запуск за 3 шага (Docker) |
| [Установка и запуск](#установка-и-запуск) | Docker, fake_robot, тома Redis |
| [Возможности](#возможности) | Привязка, NLP, помощь, gRPC |
| [Архитектура](#архитектура) | Схема и описание слоёв |
| [API](#api) | Эндпоинты |
| [Структура проекта](#структура-проекта) | Дерево каталогов |
| [Тестирование](#тестирование) | Тесты, линт |
| [CI/CD](#cicd) | Пайплайн, публикация образа, ARM64 |
| [Лицензия](#лицензия) | Использование |

---

## Быстрый старт

1. Создайте `.env` из примера и задайте **`REDIS_PASSWORD`** (обязательно для `docker compose up`):
   ```bash
   cp .env.example .env
   # Отредактируйте REDIS_PASSWORD, например: openssl rand -hex 32
   ```
2. Соберите и запустите контейнеры:
   ```bash
   docker compose up -d
   ```
3. **Salute:** http://localhost:20000 · **Alice:** http://localhost:20002 · **robot-gateway (gRPC):** порт **50051**. Документация Salute: http://localhost:20000/docs

Остановка: `docker compose down` (без `-v`, чтобы не удалять данные Redis).

---

## Установка и запуск

### Docker (рекомендуется)

- **Локальная разработка / сборка:** `docker compose up -d`. Сервисы: `robot-gateway` (50051), `salute` (20000), `alice` (20002), Redis.
- **Продакшен (образы из GHCR):** `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`. Предварительно:
  ```bash
  docker pull ghcr.io/shiwarai/rds-2p-assistants-skills-robot-gateway:main
  docker pull ghcr.io/shiwarai/rds-2p-assistants-skills-salute:main
  docker pull ghcr.io/shiwarai/rds-2p-assistants-skills-alice:main
  ```

### Тестирование без реального робота

В каталоге **fake_robot/** — имитатор робота (gRPC-клиент с `robot_id=0`). После `docker compose up -d` запустите имитатор с хостом **robot-gateway** (порт 50051): робот будет виден навыкам salute и alice. Подробно: [fake_robot/README.md](fake_robot/README.md).

### Навык Алисы

Webhook для [Яндекс Диалогов](https://yandex.ru/dev/dialogs/alice/doc/ru/): укажите в консоли backend `https://<host>/v1/webhook` (сервис **alice**, порт 20002 локально).

### Почему могут пропадать привязки после перезапуска

Привязки хранятся в Redis в томе **redis_data**.

- В `docker-compose.yml` задано **`name: rds-2p-assistants-skills`**, поэтому том один и тот же с любого пути запуска.
- Redis пишет AOF в **`--dir /data`** (смонтированный том).
- Команда **`docker compose down -v`** удаляет тома — после следующего `up` Redis будет пустой. Для обычного перезапуска: `docker compose down && docker compose up --build -d`.

### Безопасность Redis

- **Порт 6379 наружу не публикуется** — приложение подключается к Redis только по внутренней сети Docker.
- Включён **`requirepass`**, пароль задаётся в `.env` как **`REDIS_PASSWORD`**; в `REDIS_URL` для сервиса `app` пароль подставляется автоматически.
- В логах приложения URL Redis выводится **без пароля** (маскировка).

После обновления с версии без пароля: положите `REDIS_PASSWORD` в `.env` и выполните `docker compose up -d` (при необходимости пересоздайте контейнер Redis). Старые данные в томе `redis_data` сохраняются; Redis при старте просто начнёт требовать пароль.

---

## Возможности

### Привязка роботов

- Запрос: «Привяжи робота 1». Система запрашивает 4-значный код у робота (код в логах робота). Код действует 5 минут, 3 попытки ввода. Привязка сохраняется в Redis.

### Управление по голосу (NLP)

Через **CVC** распознаются естественные фразы, например:

- «Попроси панду лечь» → `lie_down`
- «Вставай» → `dismiss`
- «Дай лапу» → `give_paw`

### Интерактивная помощь

- «Помощь» — выбор между служебными и исполняемыми командами. Состояние диалога сохраняется (например, «расскажи про бегать»).

### gRPC

Роботы подключаются по gRPC и держат Stream; команды доставляются мгновенно.

---

## Архитектура

Реализация в стиле **Clean Architecture**: домен не зависит от фреймворков, сценарии в Use Cases, инфраструктура подключается через интерфейсы.

### Схема

```mermaid
graph TD
    subgraph "Presentation"
        API[FastAPI Routes / Webhook]
    end

    subgraph "Application"
        UC[Use Cases: ProcessCommand, BindRobot, GetHelp]
        DTO[DTOs: CommandRequest, CommandResponse]
    end

    subgraph "Domain"
        Entities[Entities: User]
        VO[Value Objects: UserState, RobotId, BindingCode]
        RepoInterfaces[Interfaces: IBindingRepository, IUserRepository, ...]
        ServiceInterfaces[Interfaces: ICommandClassifier, IRobotConnector]
    end

    subgraph "Infrastructure"
        Redis[Redis Persistence]
        gRPC[gRPC Server & Robot Connector]
        CVC[CVC Classifier Implementation]
    end

    API --> UC
    UC --> Entities
    UC --> RepoInterfaces
    UC --> ServiceInterfaces
    Redis -.-> RepoInterfaces
    gRPC -.-> ServiceInterfaces
    CVC -.-> ServiceInterfaces
```

### Слои

- **Domain** — сущности (`User`), value objects (`UserState`, `RobotId`, `BindingCode`), интерфейсы репозиториев и сервисов. Без внешних зависимостей.
- **Application** — Use Cases и DTO; оркестрируют сценарии.
- **Infrastructure** — реализации: Redis, gRPC-сервер и коннектор к роботам, клиент CVC.
- **Presentation** — FastAPI-роуты, вебхуки Сбера → вызовы Use Cases.

---

## API

| Метод | Путь | Описание |
| ----- | ---- | -------- |
| POST | /v1/webhook | Вход для SmartApp API (Salute) или Яндекс Диалогов (Alice) |
| GET | /v1/health | Проверка состояния сервера |
| GET | /v1/admin/command-feedback | Репорты «исправить команду» (только локальная сеть) |
| GET | /docs | Swagger UI |

Salute: сервис `salute` (:20000). Alice: сервис `alice` (:20002). Роботы подключаются к `robot-gateway` (:50051).

---

## Структура проекта

```
RDS-2P-assistants-skills/
├── app/
│   ├── api/                # Общие роуты (health, admin)
│   ├── platforms/
│   │   ├── salute/         # Webhook Salute
│   │   └── alice/          # Webhook Алисы
│   ├── application/        # Use Cases, DTO
│   ├── domain/
│   ├── infrastructure/     # Redis, CVC, remote gateway client
│   ├── main_salute.py
│   └── main_alice.py
├── gateway/                # robot-gateway (gRPC для роботов + SkillBridge)
├── fake_robot/
├── grpc_proto/
├── tests/
├── docker-compose.yml
├── Dockerfile.salute
├── Dockerfile.alice
├── Dockerfile.gateway
├── Dockerfile.dev
└── ...
```

---

## Тестирование

Используется образ **rds-2p-assistants-skills-dev** (`docker-compose.dev.yml`) — отдельный dev-образ только для линта и тестов, без prod-сервисов:

```bash
docker compose -f docker-compose.dev.yml build dev

# Линт
docker compose -f docker-compose.dev.yml run --rm -T dev ruff check .

# Unit- и интеграционные тесты (Salute + Alice)
docker compose -f docker-compose.dev.yml run --rm dev pytest tests/ -v --tb=short --cov=app --cov-report=term-missing
```

Тесты используют моки и fakeredis, без реального CVC и Redis.

---

## CI/CD

Пайплайны в `.github/workflows/`:

| Workflow | Триггер | Назначение |
| -------- | ------- | ---------- |
| **Deploy** (`deploy.yml`) | Push в `main` или `dev` | Dev-образ, ruff + pytest |
| **Deploy → prerelease** (`deploy.yml`, job `publish-prerelease`) | Push в `dev` с `[prerelease]` в коммите, или ручной запуск с `publish_prerelease` | Публикация gateway/salute/alice с тегом `:prerelease` |
| **Publish** (`publish.yml`) | Успешный Deploy на `main` | Публикация с тегом `:main` |

### Prerelease (тестовое окружение)

По аналогии с `[retrain]` в [CVC](https://github.com/ShiWarai/CVC/blob/main/.github/workflows/deploy.yml): prod-образы публикуются **только по явному запросу**.

1. **Автоматически:** commit в `dev` с меткой `[prerelease]` в сообщении, например:
   ```bash
   git commit -m "feat: alice webhook [prerelease]"
   git push origin dev
   ```
   После успешных тестов в GHCR появятся теги `:prerelease` и `:<sha>`.

2. **Вручную:** GitHub Actions → Deploy → Run workflow → включить `publish_prerelease`.

На тестовом стенде:
```bash
docker pull ghcr.io/shiwarai/rds-2p-assistants-skills-robot-gateway:prerelease
docker pull ghcr.io/shiwarai/rds-2p-assistants-skills-salute:prerelease
docker pull ghcr.io/shiwarai/rds-2p-assistants-skills-alice:prerelease
docker compose -f docker-compose.yml -f docker-compose.prerelease.yml up -d
```

### Публикация stable (main)

- `ghcr.io/shiwarai/rds-2p-assistants-skills-robot-gateway:main`
- `ghcr.io/shiwarai/rds-2p-assistants-skills-salute:main`
- `ghcr.io/shiwarai/rds-2p-assistants-skills-alice:main`

Сборка **linux/amd64** и **linux/arm64**. В k3s: один Deployment для gateway, отдельные для salute и alice; роботы снаружи подключаются к Service gateway.

---

## Лицензия

MIT

*Проект создан с использованием нейросетей.*