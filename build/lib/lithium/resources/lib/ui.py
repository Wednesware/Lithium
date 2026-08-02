from decimal import Decimal


_PKO_UNIT_DEFS = {
    # Typography and CSS-like display lengths, relative to CSS pixels.
    "px": ("display_length", Decimal("1")),
    "dp": ("display_length", Decimal("1")),
    "sp": ("display_length", Decimal("1")),
    "em": ("display_length", Decimal("16")),
    "rem": ("display_length", Decimal("16")),
    "csspt": ("display_length", Decimal("1.333333333333333333333333333")),
    "pc": ("display_length", Decimal("16")),
    "cssin": ("display_length", Decimal("96")),
    # Resolution and pixel-count measures.
    "ppi": ("pixel_density", Decimal("1")),
    "dpi": ("pixel_density", Decimal("1")),
    "dppx": ("pixel_density", Decimal("96")),
    "mp": ("pixel_count", Decimal("1000000")),
    "megapixel": ("pixel_count", Decimal("1000000")),
}
