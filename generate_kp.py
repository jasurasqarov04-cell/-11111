"""
Модуль генерации PDF коммерческого предложения.
Использует Jinja2 для рендера HTML и конвертацию в PDF
(WeasyPrint → Chrome headless → xhtml2pdf).
"""

import base64
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from catalog import format_product_name
from translations import pdf_dict, DEFAULT_LANG

# Путь к папке с шаблоном
TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = "template.html"


def _format_unit_display(unit: str) -> str:
    """Формат единицы как в образце PDF: «1 m³»."""
    u = (unit or "").strip()
    superscript = {"м³": "³", "m³": "³", "м²": "²", "m²": "²"}
    for key, sup in superscript.items():
        if u == key:
            base = "m" if key.startswith("m") else "м"
            return f"1 {base}{sup}"
    return u or "—"


def _chrome_paths() -> list[str]:
    """Пути к Chrome/Chromium: CHROME_PATH, затем типичные для ОС."""
    seen: set[str] = set()
    out: list[str] = []

    def add(path: str) -> None:
        p = (path or "").strip()
        if p and os.path.isfile(p) and p not in seen:
            seen.add(p)
            out.append(p)

    add(os.environ.get("CHROME_PATH", ""))

    if os.name == "nt":
        for p in (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ):
            add(p)
    else:
        for name in (
            "google-chrome-stable",
            "google-chrome",
            "chromium",
            "chromium-browser",
            "microsoft-edge-stable",
            "microsoft-edge",
        ):
            w = shutil.which(name)
            if w:
                add(w)
    return out


def _pdf_via_chrome(html_path: str, pdf_path: str) -> bytes:
    html_uri = Path(html_path).resolve().as_uri()
    last_err = None
    for chrome in _chrome_paths():
        try:
            subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    f"--print-to-pdf={pdf_path}",
                    "--print-to-pdf-no-header",
                    html_uri,
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            with open(pdf_path, "rb") as f:
                return f.read()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            last_err = exc
    raise RuntimeError(f"Chrome/Edge headless не смог создать PDF: {last_err}")


def _inline_assets(html_content: str) -> str:
    assets_dir = os.path.join(TEMPLATE_DIR, "assets")
    if not os.path.isdir(assets_dir):
        return html_content
    for name in os.listdir(assets_dir):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            continue
        path = os.path.join(assets_dir, name)
        with open(path, "rb") as img:
            b64 = base64.b64encode(img.read()).decode("ascii")
        ext = name.rsplit(".", 1)[-1].lower()
        mime = "jpeg" if ext in ("jpg", "jpeg") else ext
        data_uri = f"data:image/{mime};base64,{b64}"
        html_content = html_content.replace(f'assets/{name}', data_uri)
    return html_content


def _cell(value, show: bool) -> str:
    if not show:
        return "—"
    if value is None or value == "":
        return "—"
    return str(value)


def _prepare_items(items: list, table_opts: dict | None = None) -> list:
    opts = table_opts or {}
    show_density = opts.get("show_density", True)
    show_size = opts.get("show_size", True)
    show_qty = opts.get("show_qty", True)
    show_unit = opts.get("show_unit", True)
    show_price = opts.get("show_price", True)
    show_line_total = opts.get("show_line_total", True)

    prepared = []
    for item in items:
        row = dict(item)
        if row.get("name"):
            if item.get("from_catalog", True):
                row["name"] = format_product_name(str(row["name"]))
            else:
                row["name"] = " ".join(str(row["name"]).split())
        density = item.get("density")
        thickness = item.get("thickness")
        qty_fmt = item.get("qty_fmt")
        unit = row.get("unit", "")

        row["density_display"] = _cell(
            int(density) if density is not None else None, show_density
        )
        row["size_display"] = _cell(
            int(thickness) if thickness is not None else None, show_size
        )
        row["qty_display"] = _cell(qty_fmt, show_qty)
        row["unit_display"] = _cell(
            _format_unit_display(unit) if unit else None, show_unit
        )
        row["price_display"] = _cell(item.get("price_fmt"), show_price)
        row["line_total_display"] = _cell(item.get("total_fmt"), show_line_total)
        prepared.append(row)
    return prepared


def generate_pdf(data: dict) -> bytes:
    """
    Принимает словарь с данными КП и возвращает PDF в байтах.

    Обязательные ключи data:
      kp_number      — номер КП, напр. "KIG-0001"
      date           — дата КП, напр. "01.06.2025"
      client_name    — название клиента
      valid_until    — срок действия КП, напр. "15.06.2025"
      nds_rate       — ставка НДС (0 или 12)
      nds_amount     — сумма НДС (float)
      nds_fmt        — строка НДС или None
      subtotal_fmt   — строка итого без НДС
      grand_total_fmt — строка итого к оплате
      items          — список позиций:
                        [{"name", "unit", "qty", "price_fmt", "total_fmt"}, ...]
    """
    # Загружаем и рендерим шаблон
    render_data = dict(data)
    table_opts = {
        "show_density": data.get("show_density", True),
        "show_size": data.get("show_size", True),
        "show_qty": data.get("show_qty", True),
        "show_unit": data.get("show_unit", True),
        "show_price": data.get("show_price", True),
        "show_line_total": data.get("show_line_total", True),
    }
    render_data.update(table_opts)
    render_data["show_total"] = data.get("show_total", True)
    render_data["items"] = _prepare_items(data.get("items", []), table_opts)

    lang = data.get("lang") or DEFAULT_LANG
    t = pdf_dict(lang)
    t["total_label"] = t.get("total", "Сумма: {grand}").format(
        grand=data.get("grand_total_fmt", "")
    )
    render_data["t"] = t
    render_data["lang"] = lang

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(TEMPLATE_FILE)
    html_content = _inline_assets(template.render(**render_data))

    # WeasyPrint (Linux / macOS / Windows + GTK)
    try:
        from weasyprint import HTML
        return HTML(string=html_content, base_url=TEMPLATE_DIR).write_pdf()
    except (ImportError, OSError):
        pass

    # Chrome / Edge headless (Windows без GTK)
    with tempfile.TemporaryDirectory() as tmp:
        html_path = os.path.join(tmp, "kp.html")
        pdf_path = os.path.join(tmp, "kp.pdf")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        if _chrome_paths():
            return _pdf_via_chrome(html_path, pdf_path)

    # xhtml2pdf (запасной вариант)
    try:
        from io import BytesIO
        from xhtml2pdf import pisa

        result = BytesIO()
        status = pisa.CreatePDF(
            html_content,
            dest=result,
            encoding="utf-8",
            link_callback=lambda uri, rel: os.path.join(
                TEMPLATE_DIR, uri.replace("/", os.sep)
            ),
        )
        if status.err:
            raise RuntimeError(f"xhtml2pdf: {status.err} ошибок при генерации")
        return result.getvalue()
    except ImportError as exc:
        raise RuntimeError(
            "Не удалось создать PDF. Установите Google Chrome "
            "или weasyprint (+ GTK на Windows)."
        ) from exc


def generate_pdf_from_file(data: dict, output_path: str) -> str:
    """
    Сохраняет PDF в файл и возвращает путь.
    Удобно для тестирования вне Telegram.
    """
    pdf_bytes = generate_pdf(data)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return output_path


# ── Тест (запуск напрямую) ───────────────────────────────────────────────
if __name__ == "__main__":
    test_data = {
        "kp_number": "KIG-0001",
        "date": "20.05.2025",
        "client_name": 'ООО "Тестовая Компания"',
        "valid_until": "20.06.2025",
        "nds_rate": 12,
        "nds_amount": 188_019,
        "nds_fmt": "188 019",
        "subtotal_fmt": "1 566 831",
        "grand_total_fmt": "1 283 400 000",
        "show_density": True,
        "show_size": True,
        "show_qty": True,
        "show_unit": True,
        "show_price": True,
        "show_line_total": True,
        "show_total": True,
        "lang": "ru",
        "items": [
            {
                "name": "Thermo Vent Pro",
                "density": 80,
                "thickness": 50,
                "unit": "м²",
                "qty": 40000,
                "qty_fmt": "40 000",
                "price_fmt": "32 085",
                "total": 1_283_400_000,
                "total_fmt": "1 283 400 000",
            },
        ],
    }

    out = os.path.join(TEMPLATE_DIR, "test_kp.pdf")
    path = generate_pdf_from_file(test_data, out)
    print(f"PDF saved: {path}")
