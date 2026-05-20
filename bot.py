#!/usr/bin/env python3
"""
Telegram бот для генерации Коммерческих Предложений
KHOREZM INSULATION GROUP — каталог, настройка колонок таблицы
"""

import os

try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import logging
import ssl
import threading
import urllib.error
import urllib.request
from datetime import date, timedelta
from io import BytesIO

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from catalog import PRODUCTS, format_product_name
from generate_kp import generate_pdf

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _start_render_keepalive() -> None:
    """
    HTTP-запрос к своему URL каждые ~14 мин — сбрасывает таймер «сна» Free Web Service на Render
    (засыпание обычно ~15 мин без входящего трафика). Без RENDER_EXTERNAL_URL / KEEPALIVE_URL поток не стартует.
    """
    url = (os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("KEEPALIVE_URL") or "").strip()
    if not url:
        return
    url = url.rstrip("/")
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url

    try:
        interval = int(os.environ.get("KEEPALIVE_INTERVAL_SEC", "840"))
    except ValueError:
        interval = 840
    if interval < 60:
        interval = 60

    def _ssl_context():
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def ping():
        try:
            req = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(req, timeout=45, context=_ssl_context())
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            logger.warning("Keepalive: не удалось достучаться до %s: %s", url, exc)

    def loop():
        import time
        ping()
        while True:
            time.sleep(interval)
            ping()

    threading.Thread(target=loop, daemon=True, name="render-keepalive").start()
    logger.info("Keepalive (Render и др.): GET %s каждые %s с", url, interval)


(
    ASK_NDS,
    ASK_PRODUCT,
    ASK_CUSTOM_NAME,
    ASK_ITEM_THICK,
    ASK_ITEM_UNIT,
    ASK_ITEM_PRICE,
    ASK_ITEM_QTY,
    ASK_MORE,
    ASK_COL_SETTING,
) = range(9)

COL_SETTINGS = [
    ("show_density", "колонку «Плотность»"),
    ("show_size", "колонку «Размер»"),
    ("show_qty", "колонку «Кол-во»"),
    ("show_unit", "колонку «Ед.изм»"),
    ("show_price", "колонку «Цена с НДС»"),
    ("show_line_total", "колонку «Сумма» по позициям"),
    ("show_total", "строку «Сумма» под таблицей"),
]

UNIT_KEYBOARD = ReplyKeyboardMarkup(
    [["м³", "м²", "шт"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

SKIP_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("Пропустить", callback_data="skip"),
]])

YES_SKIP_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Показывать", callback_data="col_yes"),
        InlineKeyboardButton("Пропустить", callback_data="col_skip"),
    ],
])

NDS_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("Да — НДС 12%", callback_data="nds_12")],
    [InlineKeyboardButton("Нет (без НДС)", callback_data="nds_0")],
])

MORE_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("Добавить позицию", callback_data="add_more")],
    [InlineKeyboardButton("Создать КП (PDF)", callback_data="generate")],
])


def fmt_num(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ")


def _kp_counter_file() -> str:
    return os.path.join(os.path.dirname(__file__), ".kp_counter")


def next_kp_number() -> str:
    try:
        with open(_kp_counter_file()) as f:
            n = int(f.read().strip()) + 1
    except (FileNotFoundError, ValueError):
        n = 1
    with open(_kp_counter_file(), "w") as f:
        f.write(str(n))
    return f"KIG-{n:04d}"


def parse_positive_float(text: str):
    try:
        v = float(text.strip().replace(",", ".").replace(" ", "").replace("\u202f", ""))
        return v if v > 0 else None
    except ValueError:
        return None


def product_keyboard() -> InlineKeyboardMarkup:
    """Все товары сразу, по 2 в ряд; в конце — «Другое»."""
    rows = []
    for i in range(0, len(PRODUCTS), 2):
        row = []
        for j in range(2):
            idx = i + j
            if idx >= len(PRODUCTS):
                break
            p = PRODUCTS[idx]
            label = f"{p['name']} ({p['density']})"
            if len(label) > 64:
                short = p["name"]
                if len(short) > 40:
                    short = short[:39] + "…"
                label = f"{short} ({p['density']})"
            row.append(InlineKeyboardButton(label, callback_data=f"prod_{idx}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("Другое", callback_data="prod_other")])
    return InlineKeyboardMarkup(rows)


def item_summary_line(it: dict, idx: int) -> str:
    parts = [it["name"]]
    if it.get("density") is not None:
        parts.append(f"ρ {int(it['density'])}")
    if it.get("thickness"):
        parts.append(f"{int(it['thickness'])} мм")
    spec = " | ".join(parts)
    return (
        f"{idx}. {spec}\n"
        f"   {it['qty_fmt']} {it['unit']} × {it['price_fmt']} = *{it['total_fmt']} сум*"
    )


def items_text(items: list) -> str:
    return "\n".join(item_summary_line(it, i) for i, it in enumerate(items, 1))


async def _ask_product(msg, context) -> int:
    n = len(context.user_data.get("items", [])) + 1
    await msg.reply_text(
        f"*Позиция {n}.* Выберите товар из каталога или *Другое*, "
        "чтобы ввести наименование вручную:",
        parse_mode="Markdown",
        reply_markup=product_keyboard(),
    )
    return ASK_PRODUCT


async def _ask_thickness(msg, context) -> int:
    name = context.user_data["current_item"]["name"]
    dens = context.user_data["current_item"].get("density")
    dens_line = f"*Плотность:* {int(dens)} кг/м³\n" if dens is not None else ""
    await msg.reply_text(
        f"*{name}*\n{dens_line}\n"
        "*Размер* (толщина, мм), например: `50` или `100`.\n"
        "_При отсутствии данных нажмите «Пропустить»._",
        parse_mode="Markdown",
        reply_markup=SKIP_KB,
    )
    return ASK_ITEM_THICK


# ── Команды ──────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data["items"] = []
    await update.message.reply_text(
        "*Коммерческое предложение*\n"
        "_KHOREZM INSULATION GROUP_\n\n"
        "Учитывать *НДС* в расчёте?",
        parse_mode="Markdown",
        reply_markup=NDS_KB,
    )
    return ASK_NDS


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Создание коммерческого предложения отменено.\n"
        "Чтобы начать заново, отправьте команду /start.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*Команды:*\n"
        "/start — новое КП\n"
        "/cancel — отмена\n\n"
        "Товар — из каталога или вручную (кнопка «Другое»).\n"
        "Перед PDF — настройка колонок таблицы (показать / пропустить).\n"
        "Пропустить = в PDF будет «—».",
        parse_mode="Markdown",
    )


async def step_nds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data["nds_rate"] = 12 if q.data == "nds_12" else 0
    label = "12%" if context.user_data["nds_rate"] else "без НДС"
    await q.message.edit_text(f"НДС: *{label}*", parse_mode="Markdown")
    return await _ask_product(q.message, context)


async def step_product_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(reply_markup=None)
    await q.message.reply_text(
        "Введите *наименование товара* одним сообщением "
        "(до 300 символов). Плотность в каталог не подставляется — при необходимости колонку можно скрыть в PDF.",
        parse_mode="Markdown",
    )
    return ASK_CUSTOM_NAME


async def step_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.message.text or "").strip()
    name = " ".join(raw.split())
    if not name:
        await update.message.reply_text("Наименование не может быть пустым. Введите текст.")
        return ASK_CUSTOM_NAME
    if len(name) > 300:
        await update.message.reply_text("Слишком длинное наименование (макс. 300 символов). Сократите и отправьте снова.")
        return ASK_CUSTOM_NAME
    context.user_data["current_item"] = {
        "name": name,
        "density": None,
        "thickness": None,
        "from_catalog": False,
    }
    await update.message.reply_text(f"Принято:\n{name}")
    return await _ask_thickness(update.message, context)


async def step_product_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("_")[1])
    p = PRODUCTS[idx]
    context.user_data["current_item"] = {
        "name": format_product_name(p["name"]),
        "density": p["density"],
        "thickness": None,
        "from_catalog": True,
    }
    await q.message.edit_reply_markup(reply_markup=None)
    await q.message.reply_text(
        f"*{p['name']}*, плотность {p['density']} кг/м³",
        parse_mode="Markdown",
    )
    return await _ask_thickness(q.message, context)


async def step_thick_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = parse_positive_float(update.message.text)
    if val is None:
        await update.message.reply_text(
            "Введите число в мм или нажмите «Пропустить».",
            parse_mode="Markdown",
            reply_markup=SKIP_KB,
        )
        return ASK_ITEM_THICK
    context.user_data["current_item"]["thickness"] = val
    return await _ask_unit(update.message, context)


async def step_thick_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(reply_markup=None)
    return await _ask_unit(q.message, context)


async def _ask_unit(msg, context) -> int:
    await msg.reply_text(
        "Выберите *единицу измерения*:",
        parse_mode="Markdown",
        reply_markup=UNIT_KEYBOARD,
    )
    return ASK_ITEM_UNIT


async def step_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["current_item"]["unit"] = update.message.text.strip()
    await update.message.reply_text(
        "*Цена за единицу* (сум, с НДС).\n"
        "Например: `32085`",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_ITEM_PRICE


async def step_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = parse_positive_float(update.message.text)
    if val is None:
        await update.message.reply_text("Введите корректную цену (положительное число).")
        return ASK_ITEM_PRICE
    context.user_data["current_item"]["price"] = val
    await update.message.reply_text(
        f"Цена: *{fmt_num(val)} сум*\n\n"
        "*Количество*:",
        parse_mode="Markdown",
    )
    return ASK_ITEM_QTY


async def step_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = parse_positive_float(update.message.text)
    if val is None:
        await update.message.reply_text("Введите количество (положительное число).")
        return ASK_ITEM_QTY

    item = context.user_data["current_item"]
    item["qty"] = val
    item["total"] = item["price"] * val
    item["price_fmt"] = fmt_num(item["price"])
    item["total_fmt"] = fmt_num(item["total"])
    item["qty_fmt"] = str(int(val)) if val == int(val) else str(val)

    context.user_data["items"].append(item)
    context.user_data["current_item"] = {}

    all_items = context.user_data["items"]
    grand = sum(i["total"] for i in all_items)
    nds_rate = context.user_data.get("nds_rate", 0)
    nds_line = ""
    if nds_rate:
        nds_sum = grand * nds_rate / (100 + nds_rate)
        nds_line = f"НДС {nds_rate}%: *{fmt_num(nds_sum)} сум*\n"

    await update.message.reply_text(
        f"*Позиция добавлена.*\n\n"
        f"{items_text(all_items)}\n\n"
        f"———————————————————\n"
        f"{nds_line}"
        f"*Итого: {fmt_num(grand)} сум*\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=MORE_KB,
    )
    return ASK_MORE


async def step_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    if q.data == "add_more":
        return await _ask_product(q.message, context)

    await q.message.edit_reply_markup(reply_markup=None)
    context.user_data["_col_step"] = 0
    key, label = COL_SETTINGS[0]
    await q.message.reply_text(
        "*Настройка таблицы в PDF*\n\n"
        f"Показывать {label}?\n"
        "_Пропустить — в ячейках будет «—»_",
        parse_mode="Markdown",
        reply_markup=YES_SKIP_KB,
    )
    return ASK_COL_SETTING


async def step_col_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    step = context.user_data.get("_col_step", 0)
    key, label = COL_SETTINGS[step]
    context.user_data[key] = q.data == "col_yes"

    step += 1
    if step >= len(COL_SETTINGS):
        await q.message.edit_reply_markup(reply_markup=None)
        await q.message.reply_text("Формируется PDF-документ…")
        await _do_generate(q.message, context)
        return ConversationHandler.END

    context.user_data["_col_step"] = step
    _, next_label = COL_SETTINGS[step]
    await q.message.edit_text(
        f"Показывать {next_label}?\n_Пропустить — «—» в PDF_",
        parse_mode="Markdown",
        reply_markup=YES_SKIP_KB,
    )
    return ASK_COL_SETTING


async def _do_generate(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = context.user_data
    kp_number = next_kp_number()
    today = date.today().strftime("%d.%m.%Y")
    nds_rate = ud.get("nds_rate", 0)
    items = ud["items"]

    grand = sum(i["total"] for i in items)
    if nds_rate:
        nds_amount = grand * nds_rate / (100 + nds_rate)
        subtotal = grand - nds_amount
    else:
        nds_amount = 0
        subtotal = grand

    data = {
        "kp_number": kp_number,
        "date": today,
        "client_name": ud.get("client_name", "—"),
        "valid_until": (date.today() + timedelta(days=30)).strftime("%d.%m.%Y"),
        "nds_rate": nds_rate,
        "nds_amount": nds_amount,
        "nds_fmt": fmt_num(nds_amount) if nds_amount else None,
        "subtotal_fmt": fmt_num(subtotal),
        "grand_total_fmt": fmt_num(grand),
        "show_density": ud.get("show_density", True),
        "show_size": ud.get("show_size", True),
        "show_qty": ud.get("show_qty", True),
        "show_unit": ud.get("show_unit", True),
        "show_price": ud.get("show_price", True),
        "show_line_total": ud.get("show_line_total", True),
        "show_total": ud.get("show_total", True),
        "items": items,
    }

    try:
        pdf_bytes = generate_pdf(data)
        bio = BytesIO(pdf_bytes)
        bio.name = f"KP_{kp_number}.pdf"
        total_note = f"Сумма в PDF: *{fmt_num(grand)} сум*" if ud.get("show_total") else "Сумма под таблицей скрыта"
        await message.reply_document(
            document=bio,
            filename=f"KP_{kp_number}.pdf",
            caption=(
                f"*Коммерческое предложение сформировано.*\n"
                f"Номер: `{kp_number}`\n"
                f"Позиций: {len(items)}. {total_note}\n\n"
                f"/start — новое предложение"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("Ошибка генерации PDF")
        await message.reply_text(
            f"*Ошибка при создании PDF:*\n`{e}`",
            parse_mode="Markdown",
        )


def main() -> None:
    import asyncio

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("Установите переменную окружения BOT_TOKEN")

    _start_render_keepalive()

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            ASK_NDS: [CallbackQueryHandler(step_nds, pattern="^nds_")],
            ASK_PRODUCT: [
                CallbackQueryHandler(step_product_pick, pattern=r"^prod_\d+$"),
                CallbackQueryHandler(step_product_other, pattern="^prod_other$"),
            ],
            ASK_CUSTOM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, step_custom_name),
            ],
            ASK_ITEM_THICK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, step_thick_text),
                CallbackQueryHandler(step_thick_skip, pattern="^skip$"),
            ],
            ASK_ITEM_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_unit)],
            ASK_ITEM_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_price)],
            ASK_ITEM_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_qty)],
            ASK_MORE: [CallbackQueryHandler(step_more, pattern="^(add_more|generate)$")],
            ASK_COL_SETTING: [
                CallbackQueryHandler(step_col_setting, pattern="^col_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("help", cmd_help))

    logger.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
