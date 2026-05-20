# Деплой на Render.com

Деплой как **Docker Web Service**: **`Dockerfile`**, **`docker-entrypoint.sh`** — HTTP **200** на порту **`PORT`** (проверки Render) + процесс **`bot.py`** (Telegram **long polling**).

## Бесплатный тариф (Free) и «засыпание»

Render **Free** Web Service может **усыплять** инстанс после ~**15 минут** без **входящего** HTTP. Пока сервис спит, контейнер не работает — бот не опрашивает Telegram.

В **`bot.py`** включён **keepalive**: если задан публичный URL сервиса, бот раз в **14 минут** (по умолчанию) делает **GET** на этот адрес и тем самым имитирует входящий трафик.

- Render часто сам задаёт переменную **`RENDER_EXTERNAL_URL`** (полный URL вида `https://….onrender.com`). Тогда **ничего дополнительно вручную не указывайте** — keepalive стартует автоматически.
- Если **`RENDER_EXTERNAL_URL`** нет в списке переменных, добавьте вручную **`KEEPALIVE_URL`** = тот же URL из вкладки сервиса (**например `https://kp-bot.onrender.com`**), **без** лишнего слэша в конце — не критично, код подправит.
- Интервал: **`KEEPALIVE_INTERVAL_SEC`** (по умолчанию **840** = 14 минут). Держите интервал **меньше ~15 минут**, иначе риск усыпления.

На **локальном ПК**, если не заданы **`RENDER_EXTERNAL_URL`** / **`KEEPALIVE_URL`**, поток keepalive **не запускается**.

> Политика Render может меняться: keepalive не даёт 100% гарантии для всех типов сервисов. Если бот всё равно засыпает — платный план без простоя или другой хостинг надёжнее.

---

## Подготовка

1. Проект **`kp_bot`** в репозитории на **GitHub** (или GitLab/Bitbucket, которые поддерживает Render).
2. Аккаунт на [render.com](https://render.com), вход через GitHub удобнее.
3. Токен бота от [@BotFather](https://t.me/BotFather).

Убедитесь, что в корне есть **`Dockerfile`** и **`docker-entrypoint.sh`** (как в этом репозитории).

---

## Создание Web Service

1. В панели Render: **New → Web Service**.
2. Подключите репозиторий с `kp_bot`, выберите ветку (например `main`).
3. **Language / Runtime:** **Docker** (сборка по `Dockerfile` из корня).
4. **Region** — ближайший к вам (например **Frankfurt**).
5. **Instance type:** для Free включён keepalive в коде — обычно сервис остаётся активным; при сбоях см. логи «Keepalive» или перейдите на платный план.
6. **Environment variables:**
   - **`BOT_TOKEN`** — значение токена (лучше создать как **Secret** в UI).
   - **`KEEPALIVE_URL`** — только если нет автоматической **`RENDER_EXTERNAL_URL`**: укажите публичный URL сервиса `https://….onrender.com`.
   - **`KEEPALIVE_INTERVAL_SEC`** — опционально (по умолчанию **840** = 14 минут).
   - **`PORT`** — **не задавайте вручную**: Render подставит порт сам; `fly_health.py` уже читает `PORT`.
7. Optional: **Health Check Path** = `/` (по умолчанию Render дергает корень — наш сервер отвечает **200**).

8. **Create Web Service** — дождитесь **Live**. В логах должны быть строки **Keepalive** и **Application started** (или аналог от python-telegram-bot).

---

## Поведение после деплоя

- **Логи:** вкладка **Logs** у сервиса — там вывод бота и ошибки PDF.
- **Переменные:** смена `BOT_TOKEN` → **Save** → обычно **автоматический redeploy**.
- **PDF:** в образе стоят зависимости под **WeasyPrint**; при OOM увеличьте тип инстанса (больше RAM).

---

## Файл `render.yaml` (Blueprint, по желанию)

В корень репозитория можно положить `render.yaml` и подключить **Blueprint** на Render — сервис создастся по спецификации. Пример (проверьте актуальный синтаксис в [документации Render Blueprint](https://render.com/docs/blueprint-spec)):

```yaml
services:
  - type: web
    name: kp-bot
    runtime: docker
    dockerfilePath: ./Dockerfile
    plan: starter
    region: frankfurt
    envVars:
      - key: BOT_TOKEN
        sync: false
```

`plan` и `region` замените под себя; **`BOT_TOKEN`** после создания укажите в панели (sync: false — не хранить в yaml).

---

## Краткая сводка проблем

| Симптом | Действие |
|---------|----------|
| Бот молчит на Free | Проверьте в логах **Keepalive** и переменную **`RENDER_EXTERNAL_URL` / `KEEPALIVE_URL`**; убедитесь, что URL совпадает с сервисом. |
| Health check failed | Убедитесь, что контейнер поднимает `fly_health.py` на `$PORT` (см. `docker-entrypoint.sh`). |
| Ошибка PDF | Смотрите логи; при нехватке памяти — больший instance type. |
