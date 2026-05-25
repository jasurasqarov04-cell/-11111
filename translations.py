"""
Тексты бота и PDF на русском и узбекском.
Использование:
    from translations import tr, MESSAGES
    tr("ru", "ask_unit")
    tr(lang, "ask_qty", price="32 085")
Для PDF используется ключ-набор pdf_* — собирается в dict t в generate_kp.
"""

SUPPORTED = ("ru", "uz")
DEFAULT_LANG = "ru"

MESSAGES: dict = {
    "ru": {
        # --- Бот ---
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "lang_saved": "Язык: Русский",
        "cancel": (
            "Создание коммерческого предложения отменено.\n"
            "Чтобы начать заново, отправьте команду /start."
        ),
        "help": (
            "*Команды:*\n"
            "/start — новое КП\n"
            "/cancel — отмена\n"
            "/lang — сменить язык\n\n"
            "Товар — из каталога или вручную (кнопка «Другое»).\n"
            "Кнопка «Создать КП (PDF)» — сразу формирует документ."
        ),
        "btn_skip": "Пропустить",
        "btn_other": "Другое",
        "btn_add_more": "Добавить позицию",
        "btn_generate": "Создать КП (PDF)",
        "ask_product": (
            "*Позиция {n}.* Выберите товар из каталога или *Другое*, "
            "чтобы ввести наименование вручную:"
        ),
        "density_line": "*Плотность:* {density} кг/м³\n",
        "ask_thickness": (
            "*{name}*\n{dens_line}\n"
            "*Размер* (толщина, мм), например: `50` или `100`.\n"
            "_При отсутствии данных нажмите «Пропустить»._"
        ),
        "err_thick": "Введите число в мм или нажмите «Пропустить».",
        "ask_unit": "Выберите *единицу измерения*:",
        "units": ["м³", "м²", "шт"],
        "ask_price": "*Цена за единицу* (сум, с НДС).\nНапример: `32085`",
        "err_price": "Введите корректную цену (положительное число).",
        "ask_qty": "Цена: *{price} сум*\n\n*Количество*:",
        "err_qty": "Введите количество (положительное число).",
        "product_picked": "*{name}*, плотность {density} кг/м³",
        "ask_custom_name": (
            "Введите *наименование товара* одним сообщением "
            "(до 300 символов). Плотность в каталог не подставляется."
        ),
        "err_name_empty": "Наименование не может быть пустым. Введите текст.",
        "err_name_long": (
            "Слишком длинное наименование (макс. 300 символов). "
            "Сократите и отправьте снова."
        ),
        "name_accepted": "Принято:\n{name}",
        "nds_line": "НДС {rate}%: *{sum} сум*\n",
        "position_added": (
            "*Позиция добавлена.*\n\n"
            "{items_text}\n\n"
            "———————————————————\n"
            "{nds_line}"
            "*Итого: {grand} сум*\n\n"
            "Выберите действие:"
        ),
        "generating": "Формируется PDF-документ…",
        "pdf_error": "*Ошибка при создании PDF:*\n`{e}`",
        "caption": "{today}\n\n/start — новое предложение",
        "currency": "сум",
        "mm": "мм",

        # --- PDF ---
        "pdf_company_title": "СП ООО «KHOREZM INSULATION GROUP»",
        "pdf_address": "Республика Узбекистан, Хорезмская область, г. Урганч, ул. Саноатчилар дом № 1.",
        "pdf_bank1": "ИНН: 308 351 049, р/с: 20 208 000 505 368 522 001, USD: 20208 840 505 368 522 005,",
        "pdf_bank2": 'Банк: АКБ "Узпромстройбанк" головной офис, МФО: 00440; ОКЕД: 23990; SWIFT: ULSIUZ22',
        "pdf_vat_num": "РЕГИСТРАЦИОННЫЙ НОМЕР НДС: - 333010177397",
        "pdf_intro": (
            "Компания KHOREZM INSULATION GROUP предлагает надежную и экологичную "
            "базальтовую теплоизоляцию для широкого спектра строительных и промышленных "
            "задач. Мы специализируемся на производстве и поставках базальтовой ваты, которая:"
        ),
        "pdf_intro_list": [
            "Эффективно сохраняет тепло, снижая энергозатраты зданий.",
            "Обладает высокой огнестойкостью и не поддерживает горение.",
            "Поглощает шум, улучшая звукоизоляцию помещений.",
            "Устойчива к воздействию влаги, плесени и микроорганизмов.",
            "Обеспечивает долговечность и экологическую безопасность строительных решений.",
        ],
        "pdf_col_name": "Наименование",
        "pdf_col_density": "Плотность",
        "pdf_col_size": "Размер",
        "pdf_col_qty": "Кол-во",
        "pdf_col_unit": "Ед.изм",
        "pdf_col_price": "Цена с НДС",
        "pdf_col_sum": "Сумма",
        "pdf_total": "Сумма: {grand}",
        "pdf_conditions": [
            "• Условия оплаты: 100% предоплата;",
            "• Страна производителя: Республика Узбекистан;",
            "• Условия доставки: Самовывоз или доставка до объекта покупателя;",
        ],
    },

    "uz": {
        # --- Bot ---
        "choose_lang": "Tilni tanlang / Выберите язык:",
        "lang_saved": "Til: O‘zbekcha",
        "cancel": (
            "Tijorat taklifini yaratish bekor qilindi.\n"
            "Qaytadan boshlash uchun /start buyrug‘ini yuboring."
        ),
        "help": (
            "*Buyruqlar:*\n"
            "/start — yangi tijorat taklifi\n"
            "/cancel — bekor qilish\n"
            "/lang — tilni o‘zgartirish\n\n"
            "Mahsulot — katalogdan yoki qo‘lda («Boshqa» tugmasi).\n"
            "«Tijorat taklifini yaratish (PDF)» tugmasi hujjatni darhol shakllantiradi."
        ),
        "btn_skip": "O‘tkazib yuborish",
        "btn_other": "Boshqa",
        "btn_add_more": "Pozitsiya qo‘shish",
        "btn_generate": "Tijorat taklifini yaratish (PDF)",
        "ask_product": (
            "*{n}-pozitsiya.* Katalogdan mahsulot tanlang yoki nomini qo‘lda kiritish uchun "
            "*Boshqa* tugmasini bosing:"
        ),
        "density_line": "*Zichligi:* {density} kg/m³\n",
        "ask_thickness": (
            "*{name}*\n{dens_line}\n"
            "*Qalinligi* (mm), masalan: `50` yoki `100`.\n"
            "_Ma'lumot bo‘lmasa «O‘tkazib yuborish» tugmasini bosing._"
        ),
        "err_thick": "Mm da son kiriting yoki «O‘tkazib yuborish» tugmasini bosing.",
        "ask_unit": "*O‘lchov birligini* tanlang:",
        "units": ["m³", "m²", "dona"],
        "ask_price": "*Birlik narxi* (so‘m, QQS bilan).\nMasalan: `32085`",
        "err_price": "To‘g‘ri narx kiriting (musbat son).",
        "ask_qty": "Narx: *{price} so‘m*\n\n*Miqdori*:",
        "err_qty": "Miqdorni kiriting (musbat son).",
        "product_picked": "*{name}*, zichligi {density} kg/m³",
        "ask_custom_name": (
            "*Mahsulot nomini* bitta xabarda kiriting (300 belgigacha). "
            "Zichlik katalogdan olinmaydi."
        ),
        "err_name_empty": "Nomi bo‘sh bo‘lishi mumkin emas. Matn kiriting.",
        "err_name_long": (
            "Nomi juda uzun (maks. 300 belgi). Qisqartirib qayta yuboring."
        ),
        "name_accepted": "Qabul qilindi:\n{name}",
        "nds_line": "QQS {rate}%: *{sum} so‘m*\n",
        "position_added": (
            "*Pozitsiya qo‘shildi.*\n\n"
            "{items_text}\n\n"
            "———————————————————\n"
            "{nds_line}"
            "*Jami: {grand} so‘m*\n\n"
            "Amalni tanlang:"
        ),
        "generating": "PDF hujjat shakllantirilmoqda…",
        "pdf_error": "*PDF yaratishda xatolik:*\n`{e}`",
        "caption": "{today}\n\n/start — yangi tijorat taklifi",
        "currency": "so‘m",
        "mm": "mm",

        # --- PDF ---
        "pdf_company_title": "СП ООО «KHOREZM INSULATION GROUP»",
        "pdf_address": "O‘zbekiston Respublikasi, Xorazm viloyati, Urganch shahri, Sanoatchilar ko‘chasi, 1-uy.",
        "pdf_bank1": "STIR: 308 351 049, h/r: 20 208 000 505 368 522 001, USD: 20208 840 505 368 522 005,",
        "pdf_bank2": 'Bank: «O‘zsanoatqurilishbank» ATB bosh ofisi, MFO: 00440; XXTUT: 23990; SWIFT: ULSIUZ22',
        "pdf_vat_num": "QQS RO‘YXATGA OLISH RAQAMI: - 333010177397",
        "pdf_intro": (
            "KHOREZM INSULATION GROUP kompaniyasi qurilish va sanoat sohalarining keng "
            "doiradagi ehtiyojlari uchun ishonchli va ekologik toza bazalt issiqlik "
            "izolyatsiyasini taklif etadi. Biz quyidagi xususiyatlarga ega bazalt paxtani "
            "ishlab chiqarish va yetkazib berish bilan shug‘ullanamiz:"
        ),
        "pdf_intro_list": [
            "Issiqlikni samarali saqlab, binolarning energiya sarfini kamaytiradi.",
            "Yuqori olovbardoshlikka ega va yonishni qo‘llab-quvvatlamaydi.",
            "Shovqinni yutib, xonalarning tovush izolyatsiyasini yaxshilaydi.",
            "Namlik, mog‘or va mikroorganizmlarga chidamli.",
            "Qurilish yechimlarining uzoq xizmat muddatini va ekologik xavfsizligini ta'minlaydi.",
        ],
        "pdf_col_name": "Nomi",
        "pdf_col_density": "Zichligi",
        "pdf_col_size": "Qalinligi",
        "pdf_col_qty": "Soni",
        "pdf_col_unit": "O‘lchov b.",
        "pdf_col_price": "QQS bilan narxi",
        "pdf_col_sum": "Summa",
        "pdf_total": "Summa: {grand}",
        "pdf_conditions": [
            "• To‘lov shartlari: 100% oldindan to‘lov;",
            "• Ishlab chiqaruvchi mamlakat: O‘zbekiston Respublikasi;",
            "• Yetkazib berish shartlari: O‘zi olib ketish yoki xaridor obyektigacha yetkazib berish;",
        ],
    },
}


def tr(lang: str, key: str, **kwargs) -> str:
    """Возвращает локализованную строку. Если ключа нет в выбранном языке — берёт из RU."""
    lang = lang if lang in MESSAGES else DEFAULT_LANG
    text = MESSAGES[lang].get(key)
    if text is None:
        text = MESSAGES[DEFAULT_LANG].get(key, key)
    if kwargs and isinstance(text, str):
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def units_for(lang: str) -> list:
    return list(tr(lang, "units"))


def pdf_dict(lang: str) -> dict:
    """Все pdf_* ключи без префикса, удобно для шаблона: {{ t.col_name }}."""
    src = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    out = {}
    for k, v in src.items():
        if k.startswith("pdf_"):
            out[k[len("pdf_"):]] = v
    return out
