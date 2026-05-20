# Telegram-бот: генератор коммерческих предложений (KHOREZM INSULATION GROUP)

Бот принимает данные о товарах через Telegram-диалог и генерирует готовое
коммерческое предложение в формате PDF.

---

## Структура проекта

```
kp_bot/
├── bot.py           ← главный файл бота (запускать этот)
├── generate_kp.py   ← модуль генерации PDF
├── template.html    ← HTML-шаблон КП
├── requirements.txt ← зависимости Python
└── README.md        ← эта инструкция
```

---

## Установка и запуск

### 1. Получить токен бота

1. Откройте Telegram, найдите **@BotFather**
2. Напишите `/newbot`, дайте имя и username боту
3. Скопируйте полученный токен (вида `123456:ABC-DEF...`)

### 2. Установить Python (если нет)

Скачайте Python 3.10+ с https://python.org

### 3. Установить зависимости

```bash
cd kp_bot
pip install -r requirements.txt
```

> WeasyPrint на Windows может потребовать дополнительных пакетов.
> Инструкция: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html

### 4. Запустить бота

**Windows (cmd):**
```cmd
set BOT_TOKEN=ВАШ_ТОКЕН_ЗДЕСЬ
python bot.py
```

**Linux / Mac:**
```bash
export BOT_TOKEN="ВАШ_ТОКЕН_ЗДЕСЬ"
python bot.py
```

---

## Как работает бот

```
/start
  └→ НДС (да / нет)
       └→ Выбор товара из каталога
            └→ Размер (толщина)
                 └→ Единица измерения
                      └→ Цена
                           └→ Количество
                                └→ Добавить позицию или создать PDF
                                     └→ PDF отправлен в чат
```

---

## Что можно изменить в шаблоне

Откройте `template.html` и отредактируйте:

| Что менять | Где искать |
|---|---|
| Реквизиты компании | Блок с реквизитами |
| Описание продукции | Блок intro / список преимуществ |
| Условия оплаты/доставки | Блок conditions |
| Контактные данные | Футер (фон, QR) |
| Цвет шапки таблицы | CSS: `#e3000e` |

---

## Запуск на сервере (круглосуточно)

**Render.com** (Docker): пошагово в [deploy/render.md](deploy/render.md). Переменные: [.env.example](.env.example) и секреты в панели Render.

### systemd на Linux (свой VPS, без Docker)

Создайте файл `/etc/systemd/system/kp-bot.service`:

```ini
[Unit]
Description=KP Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/kp_bot
Environment=BOT_TOKEN=ВАШ_ТОКЕН
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl enable kp-bot
sudo systemctl start kp-bot
```

---

## Частые проблемы

**WeasyPrint не устанавливается на Windows:**
```bash
pip install weasyprint --pre
```
Или установите GTK Runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer

**Бот не отвечает:**
- Проверьте правильность BOT_TOKEN
- Убедитесь, что скрипт запущен (`python bot.py`)

**Ошибка шрифтов в PDF:**
- Откройте `template.html`, при необходимости укажите fallback-шрифты в CSS

---

## Поддержка

При необходимости обратитесь к разработчику.
