require: slotfilling/slotFilling.sc
  module = sys.zb-common
theme: /

    state: Start
        q!: $regex</start>
        a: Начнём.

    state: Приветствие
        intent!: /привет
        a: Привет привет

    state: Прощание
        intent!: /пока
        a: Пока пока

    state: Равняйсь
        intent!: /равняйсь
        script:
            try {
                var robotUrl = $jsapi.context().getVar("ROBOT_URL") || "https://webhook.site/your-webhook-id";
                var requestData = {
                    action: "attention"
                };
                var response = $http.post(robotUrl, JSON.stringify(requestData), {
                    "Content-Type": "application/json"
                });
                if (response && (response.status === 200 || response.statusCode === 200)) {
                    $jsapi.context().setVar("lastCommand", "равняйсь");
                    $jsapi.context().setVar("commandSuccess", true);
                    $jsapi.context().setVar("errorMessage", "");
                } else {
                    $jsapi.context().setVar("commandSuccess", false);
                    $jsapi.context().setVar("errorMessage", response ? ("Статус: " + (response.status || response.statusCode || "неизвестно")) : "Нет ответа от сервера");
                }
            } catch (e) {
                $jsapi.context().setVar("commandSuccess", false);
                $jsapi.context().setVar("errorMessage", "Ошибка: " + (e.message || e.toString()));
            }
        a: {{$jsapi.context().getVar("commandSuccess") ? "Команда 'равняйсь' выполнена!" : "Ошибка отправки команды: " + ($jsapi.context().getVar("errorMessage") || "неизвестная ошибка") + ". Попробуйте позже."}}

    state: Лежать
        intent!: /лежать
        script:
            try {
                var robotUrl = $jsapi.context().getVar("ROBOT_URL") || "https://webhook.site/your-webhook-id";
                var requestData = {
                    action: "lie_down"
                };
                var response = $http.post(robotUrl, JSON.stringify(requestData), {
                    "Content-Type": "application/json"
                });
                if (response && (response.status === 200 || response.statusCode === 200)) {
                    $jsapi.context().setVar("lastCommand", "лежать");
                    $jsapi.context().setVar("commandSuccess", true);
                    $jsapi.context().setVar("errorMessage", "");
                } else {
                    $jsapi.context().setVar("commandSuccess", false);
                    $jsapi.context().setVar("errorMessage", response ? ("Статус: " + (response.status || response.statusCode || "неизвестно")) : "Нет ответа от сервера");
                }
            } catch (e) {
                $jsapi.context().setVar("commandSuccess", false);
                $jsapi.context().setVar("errorMessage", "Ошибка: " + (e.message || e.toString()));
            }
        a: {{$jsapi.context().getVar("commandSuccess") ? "Команда 'лежать' выполнена!" : "Ошибка отправки команды: " + ($jsapi.context().getVar("errorMessage") || "неизвестная ошибка") + ". Попробуйте позже."}}

    state: Вставай
        intent!: /вставай
        script:
            try {
                var robotUrl = $jsapi.context().getVar("ROBOT_URL") || "https://webhook.site/your-webhook-id";
                var requestData = {
                    action: "stand_up"
                };
                var response = $http.post(robotUrl, JSON.stringify(requestData), {
                    "Content-Type": "application/json"
                });
                if (response && (response.status === 200 || response.statusCode === 200)) {
                    $jsapi.context().setVar("lastCommand", "вставай");
                    $jsapi.context().setVar("commandSuccess", true);
                    $jsapi.context().setVar("errorMessage", "");
                } else {
                    $jsapi.context().setVar("commandSuccess", false);
                    $jsapi.context().setVar("errorMessage", response ? ("Статус: " + (response.status || response.statusCode || "неизвестно")) : "Нет ответа от сервера");
                }
            } catch (e) {
                $jsapi.context().setVar("commandSuccess", false);
                $jsapi.context().setVar("errorMessage", "Ошибка: " + (e.message || e.toString()));
            }
        a: {{$jsapi.context().getVar("commandSuccess") ? "Команда 'вставай' выполнена!" : "Ошибка отправки команды: " + ($jsapi.context().getVar("errorMessage") || "неизвестная ошибка") + ". Попробуйте позже."}}

    state: Fallback
        event!: noMatch
        a: Я не понял. Вы сказали: {{$request.query}}

