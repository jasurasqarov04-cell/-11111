#!/usr/bin/env python3
"""
Telegram бот для генерации Коммерческих Предложений KHOREZM INSULATION GROUP.
Двуязычный (русский / o‘zbekcha): выбор языка при первом /start, далее запоминается.
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
from translations import tr, units_for, SUPPORTED, DEFAULT_LANG
from user_lang import get_lang, set_lang

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _start_render_keepalive() -> None:
    """HTTP-запрос к своему URL каждые ~14 мин — не даёт Render Free засыпать."""
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


# ── Состояния ConversationHandler ────────────────────────────────────────
(
    ASK_LANG,
    ASK_PRODUCT,
    ASK_CUSTOM_NAME,
    ASK_ITEM_THICK,
    ASK_ITEM_UNIT,
    ASK_ITEM_PRICE,
    ASK_ITEM_QTY,
    ASK_MORE,
) = range(8)

DEFAULT_NDS_RATE = 12
COMPANY_BRAND = "Thermo Plus"

PDF_TABLE_DEFAULTS = {
    "show_density": True,
    "show_size": True,
    "show_qty": True,
    "show_unit": True,
    "show_price": True,
    "show_line_total": True,
    "show_total": True,
}


# ── Клавиатуры ───────────────────────────────────────────────────────────

LANG_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("Русский", callback_data="lang_ru")],
    [InlineKeyboardButton("O‘zbekcha", callback_data="lang_uz")],
])

GLANG_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("Русский", callback_data="glang_ru")],
    [InlineKeyboardButton("O‘zbekcha", callback_data="glang_uz")],
])


def unit_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [units_for(lang)],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(tr(lang, "btn_skip"), callback_data="skip"),
    ]])


def more_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(lang, "btn_add_more"), callback_data="add_more")],
        [InlineKeyboardButton(tr(lang, "btn_generate"), callback_data="generate")],
    ])


def product_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Все товары по 2 в ряд; в конце — «Другое» / «Boshqa»."""
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
    rows.append([InlineKeyboardButton(tr(lang, "btn_other"), callback_data="prod_other")])
    return InlineKeyboardMarkup(rows)


# ── Вспомогательное ──────────────────────────────────────────────────────

def fmt_num(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ")


def _lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Текущий язык пользователя: из user_data → из файла → DEFAULT_LANG."""
    if context.user_data.get("lang") in SUPPORTED:
        return context.user_data["lang"]
    if update.effective_user:
        saved = get_lang(update.effective_user.id)
        if saved in SUPPORTED:
            context.user_data["lang"] = saved
            return saved
    return DEFAULT_LANG


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


def item_summary_line(it: dict, idx: int, lang: str) -> str:
    parts = [it["name"]]
    if it.get("density") is not None:
        parts.append(f"ρ {int(it['density'])}")
    if it.get("thickness"):
        parts.append(f"{int(it['thickness'])} {tr(lang, 'mm')}")
    spec = " | ".join(parts)
    cur = tr(lang, "currency")
    return (
        f"{idx}. {spec}\n"
        f"   {it['qty_fmt']} {it['unit']} × {it['price_fmt']} = *{it['total_fmt']} {cur}*"
    )


def items_text(items: list, lang: str) -> str:
    return "\n".join(item_summary_line(it, i, lang) for i, it in enumerate(items, 1))


async def _ask_product(msg, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", DEFAULT_LANG)
    n = len(context.user_data.get("items", [])) + 1
    await msg.reply_text(
        tr(lang, "ask_product", n=n),
        parse_mode="Markdown",
        reply_markup=product_keyboard(lang),
    )
    return ASK_PRODUCT


async def _ask_thickness(msg, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", DEFAULT_LANG)
    name = context.user_data["current_item"]["name"]
    dens = context.user_data["current_item"].get("density")
    dens_line = tr(lang, "density_line", density=int(dens)) if dens is not None else ""
    await msg.reply_text(
        tr(lang, "ask_thickness", name=name, dens_line=dens_line),
        parse_mode="Markdown",
        reply_markup=skip_kb(lang),
    )
    return ASK_ITEM_THICK


async def _ask_unit(msg, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", DEFAULT_LANG)
    await msg.reply_text(
        tr(lang, "ask_unit"),
        parse_mode="Markdown",
        reply_markup=unit_kb(lang),
    )
    return ASK_ITEM_UNIT


# ── Команды ──────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data["items"] = []
    context.user_data["nds_rate"] = DEFAULT_NDS_RATE

    saved = get_lang(update.effective_user.id) if update.effective_user else None
    if saved in SUPPORTED:
        context.user_data["lang"] = saved
        return await _ask_product(update.message, context)

    await update.message.reply_text(
        "Tilni tanlang / Выберите язык:",
        reply_markup=LANG_KB,
    )
    return ASK_LANG


async def step_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    lang = "uz" if q.data == "lang_uz" else "ru"
    context.user_data["lang"] = lang
    if update.effective_user:
        set_lang(update.effective_user.id, lang)
    await q.message.edit_text(tr(lang, "lang_saved"))
    return await _ask_product(q.message, context)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
    context.user_data.clear()
    await update.message.reply_text(
        tr(lang, "cancel"),
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(update, context)
    await update.message.reply_text(tr(lang, "help"), parse_mode="Markdown")


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Tilni tanlang / Выберите язык:",
        reply_markup=GLANG_KB,
    )


async def cb_lang_global(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    lang = "uz" if q.data == "glang_uz" else "ru"
    context.user_data["lang"] = lang
    if update.effective_user:
        set_lang(update.effective_user.id, lang)
    await q.message.edit_text(tr(lang, "lang_saved"))


# ── Шаги диалога ─────────────────────────────────────────────────────────

async def step_product_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(reply_markup=None)
    await q.message.reply_text(tr(lang, "ask_custom_name"), parse_mode="Markdown")
    return ASK_CUSTOM_NAME


async def step_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
    raw = (update.message.text or "").strip()
    name = " ".join(raw.split())
    if not name:
        await update.message.reply_text(tr(lang, "err_name_empty"))
        return ASK_CUSTOM_NAME
    if len(name) > 300:
        await update.message.reply_text(tr(lang, "err_name_long"))
        return ASK_CUSTOM_NAME
    context.user_data["current_item"] = {
        "name": name,
        "density": None,
        "thickness": None,
        "from_catalog": False,
    }
    await update.message.reply_text(tr(lang, "name_accepted", name=name))
    return await _ask_thickness(update.message, context)


async def step_product_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
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
        tr(lang, "product_picked", name=p["name"], density=p["density"]),
        parse_mode="Markdown",
    )
    return await _ask_thickness(q.message, context)


async def step_thick_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
    val = parse_positive_float(update.message.text)
    if val is None:
        await update.message.reply_text(
            tr(lang, "err_thick"),
            parse_mode="Markdown",
            reply_markup=skip_kb(lang),
        )
        return ASK_ITEM_THICK
    context.user_data["current_item"]["thickness"] = val
    return await _ask_unit(update.message, context)


async def step_thick_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(reply_markup=None)
    return await _ask_unit(q.message, context)


async def step_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
    context.user_data["current_item"]["unit"] = update.message.text.strip()
    await update.message.reply_text(
        tr(lang, "ask_price"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_ITEM_PRICE


async def step_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
    val = parse_positive_float(update.message.text)
    if val is None:
        await update.message.reply_text(tr(lang, "err_price"))
        return ASK_ITEM_PRICE
    context.user_data["current_item"]["price"] = val
    await update.message.reply_text(
        tr(lang, "ask_qty", price=fmt_num(val)),
        parse_mode="Markdown",
    )
    return ASK_ITEM_QTY


async def step_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
    val = parse_positive_float(update.message.text)
    if val is None:
        await update.message.reply_text(tr(lang, "err_qty"))
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
    nds_rate = context.user_data.get("nds_rate", DEFAULT_NDS_RATE)
    nds_line = ""
    if nds_rate:
        nds_sum = grand * nds_rate / (100 + nds_rate)
        nds_line = tr(lang, "nds_line", rate=nds_rate, sum=fmt_num(nds_sum))

    await update.message.reply_text(
        tr(
            lang, "position_added",
            items_text=items_text(all_items, lang),
            nds_line=nds_line,
            grand=fmt_num(grand),
        ),
        parse_mode="Markdown",
        reply_markup=more_kb(lang),
    )
    return ASK_MORE


async def step_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update, context)
    q = update.callback_query
    await q.answer()

    if q.data == "add_more":
        return await _ask_product(q.message, context)

    await q.message.edit_reply_markup(reply_markup=None)
    await q.message.reply_text(tr(lang, "generating"))
    await _do_generate(q.message, context)
    return ConversationHandler.END


async def _do_generate(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", DEFAULT_LANG)
    ud = context.user_data
    kp_number = next_kp_number()
    today = date.today().strftime("%d.%m.%Y")
    nds_rate = ud.get("nds_rate", DEFAULT_NDS_RATE)
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
        "lang": lang,
        **PDF_TABLE_DEFAULTS,
        "items": items,
    }

    pdf_name = f"{COMPANY_BRAND} {today}.pdf"
    try:
        pdf_bytes = generate_pdf(data)
        bio = BytesIO(pdf_bytes)
        bio.name = pdf_name
        await message.reply_document(
            document=bio,
            filename=pdf_name,
            caption=tr(lang, "caption", today=today),
        )
    except Exception as e:
        logger.exception("Ошибка генерации PDF")
        await message.reply_text(
            tr(lang, "pdf_error", e=e),
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
            ASK_LANG: [CallbackQueryHandler(step_lang, pattern=r"^lang_(ru|uz)$")],
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
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CallbackQueryHandler(cb_lang_global, pattern=r"^glang_(ru|uz)$"))

    logger.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
