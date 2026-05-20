"""Каталог продукции Thermo."""

PRODUCTS = [
    {"name": "Thermo Lite", "density": 30},
    {"name": "Thermo Acoustic", "density": 40},
    {"name": "Thermo Universal", "density": 50},
    {"name": "Thermo Standart", "density": 60},
    {"name": "Thermo Vent Facade", "density": 70},
    {"name": "Thermo Vent Pro", "density": 80},
    {"name": "Thermo Roof L", "density": 100},
    {"name": "Thermo Facade", "density": 100},
    {"name": "Thermo Roof L Prof", "density": 120},
    {"name": "Thermo Facade Comfort", "density": 120},
    {"name": "Thermo Roof Standart", "density": 140},
    {"name": "Thermo Floor", "density": 140},
    {"name": "Thermo Facade Pro", "density": 140},
    {"name": "Thermo Floor Standart", "density": 150},
    {"name": "Thermo Facade Premium", "density": 160},
    {"name": "Thermo Roof U", "density": 170},
    {"name": "Thermo Floor Pro", "density": 170},
    {"name": "Thermo Roof U Prof", "density": 190},
]

# Все позиции на одном экране (2 колонки)
PRODUCTS_PER_PAGE = len(PRODUCTS)


def format_product_name(name: str) -> str:
    """Thermo Vent Pro — первая буква каждого слова заглавная."""
    return " ".join(
        word[:1].upper() + word[1:].lower() if word else ""
        for word in name.split()
    )
