from decimal import Decimal


_PKO_UNIT_DEFS = {
	"mm": ("length", Decimal("0.001")),
	"cm": ("length", Decimal("0.01")),
	"dm": ("length", Decimal("0.1")),
	"m": ("length", Decimal("1")),
	"km": ("length", Decimal("1000")),
	"mg": ("mass", Decimal("0.001")),
	"g": ("mass", Decimal("1")),
	"kg": ("mass", Decimal("1000")),
	"ms": ("time", Decimal("0.001")),
	"s": ("time", Decimal("1")),
	"min": ("time", Decimal("60")),
	"h": ("time", Decimal("3600")),
	"C": ("temperature", None),
	"F": ("temperature", None),
	"K": ("temperature", None),
}


_pko_unit = {
	"type": "class",
	"value": "unit",
	"map": {
		"__class_kind__": {
			"type": "string",
			"value": "unit",
			"map": {},
			"span": {"line": 0, "column": 0, "end_column": 0},
		},
	},
	"truthiness": lambda _: True,
	"span": {"line": 0, "column": 0, "end_column": 0},
}
