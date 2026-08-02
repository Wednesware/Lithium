from decimal import Decimal


_PKO_UNIT_DEFS = {
    # Length, relative to metres.
    "in": ("length", Decimal("0.0254")),
    "inch": ("length", Decimal("0.0254")),
    "ft": ("length", Decimal("0.3048")),
    "yd": ("length", Decimal("0.9144")),
    "mi": ("length", Decimal("1609.344")),
    "mile": ("length", Decimal("1609.344")),
    "miles": ("length", Decimal("1609.344")),
    "furlong": ("length", Decimal("201.168")),
    "league": ("length", Decimal("4828.032")),
    "in2": ("area", Decimal("0.00064516")),
    "ft2": ("area", Decimal("0.09290304")),
    "yd2": ("area", Decimal("0.83612736")),
    "acre": ("area", Decimal("4046.8564224")),
    "mi2": ("area", Decimal("2589988.110336")),
    "in3": ("volume", Decimal("0.000016387064")),
    "ft3": ("volume", Decimal("0.028316846592")),
    "yd3": ("volume", Decimal("0.764554857984")),
    "floz": ("volume", Decimal("0.0000295735295625")),
    "pt": ("volume", Decimal("0.000473176473")),
    "qt": ("volume", Decimal("0.000946352946")),
    "gal": ("volume", Decimal("0.003785411784")),
    "oz": ("mass", Decimal("28.349523125")),
    "lb": ("mass", Decimal("453.59237")),
    "stone": ("mass", Decimal("6350.29318")),
    "ton": ("mass", Decimal("907184.74")),
}
