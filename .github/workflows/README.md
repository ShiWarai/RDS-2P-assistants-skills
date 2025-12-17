# GitHub Actions Workflows

## Test Robot Commands

Этот workflow тестирует отправку HTTP запросов для управления роботом.

### Триггеры:

1. **repository_dispatch** - можно вызвать через API GitHub:
   ```bash
   curl -X POST https://api.github.com/repos/OWNER/REPO/dispatches \
     -H "Accept: application/vnd.github.v3+json" \
     -H "Authorization: token YOUR_TOKEN" \
     -d '{"event_type":"robot-command","client_payload":{"action":"attention"}}'
   ```

2. **workflow_dispatch** - можно запустить вручную через GitHub UI, выбрав команду

3. **push** - автоматически запускается при изменении `src/main.sc` или `caila_import.json`

### Настройка:

1. Добавьте секрет `ROBOT_WEBHOOK_URL` в настройках репозитория (Settings → Secrets)
2. Или используйте webhook.site для тестирования - получите URL и замените `your-webhook-id` в workflow файле

### Использование:

- Для тестирования через webhook.site: получите уникальный URL на https://webhook.site и используйте его
- Для реального робота: настройте URL эндпоинта в секретах GitHub

