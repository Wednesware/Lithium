from decimal import Decimal


_PKO_UNIT_DEFS = {
    # Information, relative to bits. Lowercase prefixes are decimal; Ki/Mi/Gi/Ti
    # are binary multiples.
    "bit": ("information", Decimal("1")),
    "bits": ("information", Decimal("1")),
    "b": ("information", Decimal("1")),
    "byte": ("information", Decimal("8")),
    "bytes": ("information", Decimal("8")),
    "B": ("information", Decimal("8")),
    "kb": ("information", Decimal("1000")),
    "kbit": ("information", Decimal("1000")),
    "kB": ("information", Decimal("8000")),
    "KB": ("information", Decimal("8000")),
    "MB": ("information", Decimal("8000000")),
    "GB": ("information", Decimal("8000000000")),
    "TB": ("information", Decimal("8000000000000")),
    "terabyte": ("information", Decimal("8000000000000")),
    "terabytes": ("information", Decimal("8000000000000")),
    "terrabyte": ("information", Decimal("8000000000000")),
    "terrabytes": ("information", Decimal("8000000000000")),
    "Kib": ("information", Decimal("1024")),
    "Mib": ("information", Decimal("1048576")),
    "Gib": ("information", Decimal("1073741824")),
    "Tib": ("information", Decimal("1099511627776")),
    "KiB": ("information", Decimal("8192")),
    "MiB": ("information", Decimal("8388608")),
    "GiB": ("information", Decimal("8589934592")),
    "TiB": ("information", Decimal("8796093022208")),
}
