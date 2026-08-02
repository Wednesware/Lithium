from decimal import Decimal


_PKO_UNIT_DEFS = {
    # Length, relative to metres.
    "nm": ("length", Decimal("1e-9")),
    "um": ("length", Decimal("1e-6")),
    "mm": ("length", Decimal("0.001")),
    "cm": ("length", Decimal("0.01")),
    "dm": ("length", Decimal("0.1")),
    "m": ("length", Decimal("1")),
    "dam": ("length", Decimal("10")),
    "hm": ("length", Decimal("100")),
    "km": ("length", Decimal("1000")),
    # Area, relative to square metres.
    "mm2": ("area", Decimal("1e-6")),
    "cm2": ("area", Decimal("1e-4")),
    "m2": ("area", Decimal("1")),
    "km2": ("area", Decimal("1e6")),
    "ha": ("area", Decimal("10000")),
    # Volume, relative to cubic metres.
    "mm3": ("volume", Decimal("1e-9")),
    "cm3": ("volume", Decimal("1e-6")),
    "m3": ("volume", Decimal("1")),
    "L": ("volume", Decimal("0.001")),
    "dL": ("volume", Decimal("0.0001")),
    "cL": ("volume", Decimal("0.00001")),
    "mL": ("volume", Decimal("0.000001")),
    "uL": ("volume", Decimal("1e-9")),
    # Mass, relative to grams.
    "ug": ("mass", Decimal("1e-6")),
    "mg": ("mass", Decimal("0.001")),
    "cg": ("mass", Decimal("0.01")),
    "dg": ("mass", Decimal("0.1")),
    "g": ("mass", Decimal("1")),
    "kg": ("mass", Decimal("1000")),
    "t": ("mass", Decimal("1000000")),
    # Time, relative to seconds.
    "ns": ("time", Decimal("1e-9")),
    "us": ("time", Decimal("1e-6")),
    "ms": ("time", Decimal("0.001")),
    "s": ("time", Decimal("1")),
    "min": ("time", Decimal("60")),
    "h": ("time", Decimal("3600")),
    "day": ("time", Decimal("86400")),
}
