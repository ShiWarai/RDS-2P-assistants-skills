# RDS-2P-Salute - Управление робособакой через виртуального ассистента

Этот проект создан для работы на основе https://developers.sber.ru/docs/ru/va/code/overview

## Описание

Виртуальный ассистент для управления робособакой через голосовые команды. Бот распознает команды и отправляет HTTP запросы на управление роботом.

## Команды управления

- **"равняйсь"** (также: "равняйся", "внимание", "смирно") - отправляет действие `{"action": "attention"}`
- **"лежать"** (также: "ляг", "лечь", "приляг") - отправляет действие `{"action": "lie_down"}`
- **"вставай"** (также: "встань", "поднимайся", "поднимись") - отправляет действие `{"action": "stand_up"}`

## Настройка

### 1. Настройка URL эндпоинта

URL для отправки команд настраивается через переменную `ROBOT_URL` в контексте бота или через файл `config.json`.

Для тестирования можно использовать:
- **webhook.site** - получите уникальный URL на https://webhook.site
- **GitHub Actions** - настройте workflow для приема команд

### 2. Конфигурация GitHub Actions

1. Добавьте секрет `ROBOT_WEBHOOK_URL` в настройках репозитория (Settings → Secrets)
2. Или отредактируйте `.github/workflows/test-robot-commands.yml` и замените `your-webhook-id` на ваш webhook URL

### 3. Запуск тестов

Workflow автоматически запускается при:
- Push в ветку `main` (при изменении `src/main.sc` или `caila_import.json`)
- Ручном запуске через GitHub UI (Actions → Test Robot Commands → Run workflow)
- Вызове через API `repository_dispatch`

## Структура проекта

- `src/main.sc` - основной скрипт бота с состояниями для команд
- `caila_import.json` - конфигурация интентов для распознавания команд
- `chatbot.yaml` - конфигурация SmartApp Brain
- `test/test.xml` - тестовые сценарии
- `config.json` - конфигурация URL эндпоинтов
- `.github/workflows/` - GitHub Actions workflows для тестирования

## Формат HTTP запросов

Все команды отправляются как POST запросы с JSON телом:

```json
{
  "action": "attention" | "lie_down" | "stand_up"
}
```

Заголовки:
```
Content-Type: application/json
```

## Разработка

Проект использует:
- SmartApp DSL для логики бота
- CAILA для классификации интентов
- HTTP API для отправки команд роботу
- GitHub Actions для тестирования
