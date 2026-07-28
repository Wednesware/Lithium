import copy
import importlib
import importlib.util
import os
import sys
from decimal import Decimal


class Builtins:
    OPERATOR_BUILTINS = {
        "+": "add",
        "-": "sub",
        "*": "mul",
        "/": "div",
        "%": "mod",
        "^": "exp",
        "%*": "pctof",
        "=": "eq",
        "!": "ne",
        ">": "gt",
        ">=": "gte",
        "<": "lt",
        "<=": "lte",
        "or": "logicor",
        "and": "logicand",
        "at": "at",
        "to": "convertTo",
        "..": "range",
        "..=": "rangeincl",
        ":": "span"
    }

    OPERATOR_PRIORITIES = {
        "or": 1,
        "and": 1,
        "at": 2,
        "to": 2,
        "=": 2,
        "==": 2,
        "!=": 2,
        ">": 2,
        ">=": 2,
        "<": 2,
        "<=": 2,
        ":": 2,
        "..": 2,
        "..=": 2,
        "+": 3,
        "-": 3,
        "*": 4,
        "/": 4,
        "%": 4,
        "^": 4,
        "%*": 4,
    }

    FUNCTION_PRIORITIES = {
        "or": 1,
        "and": 1,
        "at": 2,
        "to": 2,
    }
    UNIT_DEFS: dict[str, tuple[str, "Decimal | None"]] = {
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

    @staticmethod
    def _callablePriority(source: callable | None, default: int | None = None) -> int | None:
        if source is None:
            return default
        for attr_name in ("prio", "_pko_prio"):
            attr_value = getattr(source, attr_name, None)
            if isinstance(attr_value, int):
                return attr_value
        return default

    @staticmethod
    def getASTOf(interpreter, name: str, source_name: str | None = None, source: callable | None = None, fn_name: str | None = None, prio: int | None = None) -> dict:
        resolved_source = source or getattr(Builtins, source_name or name)
        resolved_prio = Builtins._callablePriority(
            resolved_source,
            default=prio if prio is not None else Builtins.FUNCTION_PRIORITIES.get(name),
        )
        function_node: dict = {
            "type": "function",
            "name": name,
            "truthiness": lambda _: True,
            "map": {
                "call": {
                    "type": "data",
                    "source": resolved_source,
                    "span": interpreter.perkeo.res.Token.emptySpan(),
                    "stringify": lambda x: f"<call data at {hex(id(resolved_source))}>"
                }
            },
            "span": interpreter.perkeo.res.Token.emptySpan()
        }
        if resolved_prio is not None:
            function_node["prio"] = resolved_prio
        return function_node

    @staticmethod
    def getOperatorASTOf(interpreter, name: str, source_name: str | None = None, source: callable | None = None, prio: int | None = None) -> dict:
        resolved_source = source or getattr(Builtins, source_name or name)
        resolved_prio = Builtins._callablePriority(
            resolved_source,
            default=prio if prio is not None else Builtins.OPERATOR_PRIORITIES.get(name),
        )
        operator_node: dict = {
            "type": "operator",
            "value": name,
            "truthiness": lambda _: True,
            "map": {
                "call": {
                    "type": "data",
                    "source": resolved_source,
                    "span": interpreter.perkeo.res.Token.emptySpan(),
                    "stringify": lambda x: f"<call data at {hex(id(resolved_source))}>"
                }
            },
            "span": interpreter.perkeo.res.Token.emptySpan()
        }
        if resolved_prio is not None:
            operator_node["prio"] = resolved_prio
        return operator_node

    @staticmethod
    def getUnitASTOf(interpreter, name: str, source_name: str | None = None, source: callable | None = None, prio: int | None = None) -> dict:
        resolved_source = source or getattr(Builtins, source_name or name)
        resolved_prio = Builtins._callablePriority(
            resolved_source,
            default=prio,
        )
        unit_node: dict = {
            "type": "unit",
            "value": name,
            "truthiness": lambda _: True,
            "map": {
                "call": {
                    "type": "data",
                    "source": resolved_source,
                    "span": interpreter.perkeo.res.Token.emptySpan(),
                    "stringify": lambda x: f"<call data at {hex(id(resolved_source))}>"
                }
            },
            "span": interpreter.perkeo.res.Token.emptySpan()
        }
        if resolved_prio is not None:
            unit_node["prio"] = resolved_prio
        return unit_node

    @staticmethod
    def _asIdentifierNodes(value: dict | None) -> list[dict]:
        if value is None:
            return []

        if value.get("type") == "array":
            nodes = value.get("items", [])
        else:
            nodes = [value]

        identifiers: list[dict] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("type") in {"identifier", "string"} and isinstance(node.get("value"), str):
                identifiers.append(node)
        return identifiers

    @staticmethod
    def _nodeFromPythonValue(value, span: dict, interpreter) -> dict:
        if isinstance(value, dict) and value.get("type"):
            return copy.deepcopy(value)
        if isinstance(value, bool):
            return {"type": "boolean", "value": value, "map": {}, "usedalias": str(value).lower(), "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if isinstance(value, int):
            return {"type": "integer", "value": value, "map": {}, "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if isinstance(value, Decimal):
            return {"type": "float", "value": value, "map": {}, "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if isinstance(value, float):
            return {"type": "float", "value": Decimal(str(value)), "map": {}, "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if isinstance(value, str):
            return {"type": "string", "value": value, "map": {}, "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if value is None:
            return {"type": "null", "map": {}, "span": dict(span)}
        if isinstance(value, (list, tuple)):
            return {
                "type": "array",
                "items": [Builtins._nodeFromPythonValue(item, span, interpreter) for item in value],
                "map": {},
                "span": dict(span),
            }
        return {"type": "data", "source": value, "map": {}, "span": dict(span), "stringify": lambda x: f"<function data at {hex(id(value))}>"}

    @staticmethod
    def _loadPkExports(interpreter, path: str, initial_vars: dict | None = None) -> dict[str, dict]:
        resolved_path = os.path.abspath(path)
        import_stack = list(interpreter.perkeo.metadata.get("__import_stack__", []))
        if resolved_path in import_stack:
            cycle = " -> ".join(import_stack + [resolved_path])
            interpreter.eh.throw("circularImport", f"circular import detected: {cycle}")

        child_perkeo = interpreter.perkeo.__class__(interpreter.perkeo.path, "lithium")
        child_perkeo.metadata["__import_stack__"] = import_stack + [resolved_path]
        library_interpreter = interpreter.perkeo.script.runpk(
            resolved_path,
            override_perkeo=child_perkeo,
            initial_vars=initial_vars,
        )["interpreter"]
        library_global_scope = library_interpreter.scopes[0]
        return {
            key: copy.deepcopy(value)
            for key, value in library_global_scope.vars.items()
            if isinstance(value, dict) and value.get("exported")
        }

    @staticmethod
    def _sourceHandlerPath(interpreter, source_type: str) -> str:
        return os.path.join(interpreter.perkeo.path, "resources", "sources", f"{source_type}.src.pk")

    @staticmethod
    def _extractSourceRedirect(exports: dict[str, dict]) -> str | None:
        for key in ("path", "source", "module"):
            node = exports.get(key)
            if not isinstance(node, dict):
                continue
            if node.get("type") == "string" and isinstance(node.get("value"), str):
                return node["value"]
            if node.get("type") == "identifier" and isinstance(node.get("value"), str):
                return node["value"]
        return None

    @staticmethod
    def _load_source_handler_exports(interpreter, src: dict, import_name: str) -> tuple[dict[str, dict] | None, str | None]:
        handler_path = Builtins._sourceHandlerPath(interpreter, src["type"])
        if not os.path.isfile(handler_path):
            return None, None

        request_vars = {
            "source_type": src["type"],
            "source_value": src["value"],
            "source_path": src["value"],
            "source_name": f'{src["type"]}::{src["value"]}',
            "import_name": import_name,
        }
        handler_exports = Builtins._loadPkExports(interpreter, handler_path, initial_vars=request_vars)
        if not handler_exports:
            return handler_exports, None
        return handler_exports, Builtins._extractSourceRedirect(handler_exports)

    @staticmethod
    def _asSourceKwargs(source_kwargs: dict[str, dict] | None) -> list[dict]:
        if not source_kwargs:
            return []

        sources: list[dict] = []
        for source_type, raw in source_kwargs.items():
            for node in Builtins._asIdentifierNodes(raw):
                sources.append({"type": source_type, "value": node["value"], "span": node["span"]})
        return sources

    @staticmethod
    def _loadPyExports(module, span: dict, interpreter) -> dict[str, dict]:
        exports: dict[str, dict] = {}
        for key, value in vars(module).items():
            if not key.startswith("_pko_"):
                continue

            export_name = key.removeprefix("_pko_")
            if callable(value):
                exports[export_name] = Builtins.getASTOf(interpreter, export_name, source=value)
            else:
                exports[export_name] = Builtins._nodeFromPythonValue(value, span, interpreter)
        return exports

    @staticmethod
    def _asNumber(interpreter, node: dict) -> "int | Decimal":
        if node.get("type") not in {"integer", "float"}:
            interpreter.eh.throw("expectedNumber", f"expected numeric literal, got {node.get('type')!r}")
        return node["value"]

    @staticmethod
    def _asDecimal(value: "int | float | Decimal") -> Decimal:
        return value if isinstance(value, Decimal) else Decimal(str(value))

    @staticmethod
    def _wrapNumber(value: "int | float | Decimal", span: dict) -> dict:
        if isinstance(value, Decimal):
            return {"type": "float", "value": value, "map": {}, "span": dict(span), "truthiness": lambda x: bool(x["value"])}
        if isinstance(value, float):
            return {"type": "float", "value": Decimal(str(value)), "map": {}, "span": dict(span), "truthiness": lambda x: bool(x["value"])}
        return {"type": "integer", "value": value, "map": {}, "span": dict(span), "truthiness": lambda x: bool(x["value"])}

    @staticmethod
    def _wrapBoolean(value: int | float, span: dict) -> dict:
        return {"type": "boolean", "value": value, "map": {}, "span": dict(span), "truthiness": lambda x: bool(x["value"]), "usedalias": str(bool(value)).lower()}

    @staticmethod
    def _binaryItems(interpreter, value: dict) -> tuple[dict, dict]:
        if value.get("type") == "array" and "items" in value:
            items = value["items"]
        elif value.get("type") == "map" and value.get("map"):
            nested = value["map"].get("value")
            if nested is None:
                interpreter.eh.throw("expectedBinaryOperands", f"expected binary call operands, got {value.get('type')!r}")
            if nested.get("type") == "array" and "items" in nested:
                items = nested["items"]
            else:
                items = [nested, nested]
        else:
            interpreter.eh.throw("expectedBinaryOperands", f"expected binary call operands, got {value.get('type')!r}")

        if len(items) != 2:
            interpreter.eh.throw("expectedTwoOperands", f"expected 2 operands, got {len(items)}")
        return items[0], items[1]

    @staticmethod
    def integerCall(interpreter, target, value: "array") -> dict: # type: ignore
        if value.get("type") not in {"integer", "float"}:
            interpreter.eh.throw("expectedNumber", f"expected numeric literal, got {value.get('type')!r}")
        print(value)
        return value

    @staticmethod
    def add(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        if left.get("type") == "string" or right.get("type") == "string":
            left_text = interpreter.stringifier.stringify(left)
            right_text = interpreter.stringifier.stringify(right)
            return {
                "type": "string",
                "value": f"{left_text}{right_text}",
                "map": {},
                "truthiness": lambda x: bool(x["value"]),
                "span": value["span"],
            }
        if left.get("type") == "array" and right.get("type") == "array":
            return {
                "type": "array",
                "items": left.get("items", []) + right.get("items", []),
                "map": {},
                "truthiness": lambda x: bool(x["items"]),
                "span": value["span"],
            }
        if left.get("type") == "map" and right.get("type") == "map":
            return {
                "type": "map",
                "map": {**left.get("map", {}), **right.get("map", {})},
                "truthiness": lambda x: bool(x["map"]),
                "span": value["span"],
            }
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapNumber(left_value + right_value, value["span"])

    @staticmethod
    def sub(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapNumber(left_value - right_value, value["span"])

    @staticmethod
    def mul(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        if (left.get("type") == "string" and right.get("type") == "integer") or (left.get("type") == "integer" and right.get("type") == "string"):
            return {
                "type": "string",
                "value": left["value"] * right["value"],
                "map": {},
                "truthiness": lambda x: bool(x["value"]),
                "span": value["span"],
            }
        if (left.get("type") == "array" and right.get("type") == "integer") or (left.get("type") == "integer" and right.get("type") == "array"):
            return {
                "type": "array",
                "items": (left.get("items", []) * right["value"]) if left.get("type") == "array" else (right.get("items", []) * left["value"]),
                "map": {},
                "truthiness": lambda x: bool(x["items"]),
                "span": value["span"],
            }
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapNumber(left_value * right_value, value["span"])

    @staticmethod
    def div(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        if not right_value:
            interpreter.eh.throw("divisionByZero", "division by zero is not allowed, returning nan.", warning=True)
            return {"type": "nan", "map": {}, "span": value["span"], "truthiness": lambda x: False}
        result = Builtins._asDecimal(left_value) / Builtins._asDecimal(right_value)
        return Builtins._wrapNumber(result, value["span"])

    @staticmethod
    def mod(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapNumber(left_value % right_value, value["span"])
    
    @staticmethod
    def exp(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapNumber(left_value ** right_value, value["span"])
    
    @staticmethod
    def pctof(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        result = Builtins._asDecimal(left_value) / Decimal(100) * Builtins._asDecimal(right_value)
        return Builtins._wrapNumber(result, value["span"])

    @staticmethod
    def eq(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapBoolean(left_value == right_value, value["span"])

    @staticmethod
    def ne(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapBoolean(left_value != right_value, value["span"])

    @staticmethod
    def gt(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapBoolean(left_value > right_value, value["span"])

    @staticmethod
    def gte(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapBoolean(left_value >= right_value, value["span"])

    @staticmethod
    def lt(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapBoolean(left_value < right_value, value["span"])

    @staticmethod
    def lte(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return Builtins._wrapBoolean(left_value <= right_value, value["span"])
    
    @staticmethod
    def _isTruthy(node: dict) -> bool:
        if not isinstance(node, dict):
            return bool(node)
        predicate = node.get("truthiness")
        if callable(predicate):
            return bool(predicate(node))
        if "value" in node:
            return bool(node["value"])
        if "items" in node:
            return bool(node["items"])
        if "map" in node:
            return bool(node["map"])
        return True

    @staticmethod
    def logicor(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        return left if Builtins._isTruthy(left) else right
    
    @staticmethod
    def logicand(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        return left if not Builtins._isTruthy(left) else right
    
    @staticmethod
    def at(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        if left.get("type") != "array":
            interpreter.eh.throw("expectedArray", f"expected array for 'at' operator, got {left.get('type')!r}")
        index = Builtins._asNumber(interpreter, right)
        items = left.get("items", [])
        if not isinstance(index, int) or index < 0 or index >= len(items):
            interpreter.eh.throw("indexOutOfBounds", f"index {index} is out of bounds for array of length {len(items)}")
        return items[index]
        
    
    @staticmethod
    def range(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return {
            "type": "array",
            "items": [
                Builtins._wrapNumber(item, value["span"])
                for item in range(left_value, right_value)
            ],
            "map": {
                "start": Builtins._wrapNumber(left_value, value["span"]),
                "end": Builtins._wrapNumber(right_value, value["span"])
            },
            "truthiness": lambda x: bool(x["items"]),
            "stringify": lambda x: f"{x['map']['start']['value']}..{x['map']['end']['value']}",
            "span": value["span"],
        }

    @staticmethod
    def rangeincl(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return {
            "type": "array",
            "items": [
                Builtins._wrapNumber(item, value["span"])
                for item in range(left_value, right_value + 1)
            ],
            "map": {
                "start": Builtins._wrapNumber(left_value, value["span"]),
                "end": Builtins._wrapNumber(right_value, value["span"])
            },
            "truthiness": lambda x: bool(x["items"]),
            "stringify": lambda x: f"{x['map']['start']['value']}..={x['map']['end']['value']}",
            "span": value["span"],
        }
        
    @staticmethod
    def span(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        left_value = Builtins._asNumber(interpreter, left)
        right_value = Builtins._asNumber(interpreter, right)
        return {
            "type": "map",
            "map": {
                "start": Builtins._wrapNumber(left_value, value["span"]),
                "end": Builtins._wrapNumber(right_value, value["span"]),
            },
            "truthiness": lambda x: bool(x["map"]["start"]["value"] and x["map"]["end"]["value"]),
            "stringify": lambda x: f"{x['map']['start']['value']}:{x['map']['end']['value']}",
            "span": value["span"],
        }

    @staticmethod
    def _unitDimension(unit_name: str) -> str | None:
        info = Builtins.UNIT_DEFS.get(unit_name)
        return info[0] if info else None

    @staticmethod
    def _toBaseUnit(dimension: str, unit_name: str, value: Decimal) -> Decimal:
        if dimension == "temperature":
            if unit_name == "C":
                return value
            if unit_name == "F":
                return (value - 32) * Decimal(5) / Decimal(9)
            if unit_name == "K":
                return value - Decimal("273.15")
        factor = Builtins.UNIT_DEFS[unit_name][1]
        return value * factor

    @staticmethod
    def _fromBaseUnit(dimension: str, unit_name: str, base_value: Decimal) -> Decimal:
        if dimension == "temperature":
            if unit_name == "C":
                return base_value
            if unit_name == "F":
                return base_value * Decimal(9) / Decimal(5) + 32
            if unit_name == "K":
                return base_value + Decimal("273.15")
        factor = Builtins.UNIT_DEFS[unit_name][1]
        return base_value / factor

    @staticmethod
    def _makeQuantity(value: "int | Decimal", unit_name: str, span: dict) -> dict:
        return {
            "type": "quantity",
            "value": value,
            "unit": unit_name,
            "map": {},
            "truthiness": lambda x: bool(x["value"]),
            "stringify": lambda x: f"{x['value']}{x['unit']}",
            "span": dict(span),
        }

    @staticmethod
    def _normalizeQuantityValue(value: Decimal) -> "int | Decimal":
        normalized = value.normalize()
        if normalized == normalized.to_integral_value():
            return int(normalized.to_integral_value())
        _, _, exponent = normalized.as_tuple()
        if exponent > 0:
            normalized = normalized.quantize(Decimal(1))
        return normalized

    @staticmethod
    def unitCall(interpreter, target, value: "integer|float") -> dict: # type: ignore
        unit_name = target["value"]
        if unit_name not in Builtins.UNIT_DEFS:
            interpreter.eh.throw("unknownUnit", f"unknown unit '{unit_name}'")
        return Builtins._makeQuantity(value["value"], unit_name, value["span"])

    @staticmethod
    def convertTo(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binaryItems(interpreter, value)
        if left.get("type") != "quantity":
            interpreter.eh.throw("typeError", f"'to' expects a quantity (e.g. 400cm) on the left-hand side, got {left.get('type')!r}")
        if right.get("type") == "unit":
            target_unit = right["value"]
        elif right.get("type") == "quantity":
            target_unit = right["unit"]
        else:
            interpreter.eh.throw("typeError", f"'to' expects a unit on the right-hand side, got {right.get('type')!r}")

        source_unit = left["unit"]
        source_dim = Builtins._unitDimension(source_unit)
        target_dim = Builtins._unitDimension(target_unit)
        if source_dim is None or target_dim is None:
            interpreter.eh.throw("unknownUnit", f"unknown unit in conversion: '{source_unit}' to '{target_unit}'")
        if source_dim != target_dim:
            interpreter.eh.throw("incompatibleUnits", f"cannot convert '{source_unit}' ({source_dim}) to '{target_unit}' ({target_dim})")

        source_value = Builtins._asDecimal(left["value"])
        base_value = Builtins._toBaseUnit(source_dim, source_unit, source_value)
        converted_value = Builtins._fromBaseUnit(target_dim, target_unit, base_value)
        return Builtins._makeQuantity(Builtins._normalizeQuantityValue(converted_value), target_unit, value["span"])


    @staticmethod
    def _classParents(inherits) -> list:
        if inherits is None:
            return []
        if isinstance(inherits, dict) and inherits.get("type") == "array":
            return inherits.get("items", [])
        return [inherits]

    @staticmethod
    def _declaredTypeName(type_ast: dict | None) -> str:
        if not isinstance(type_ast, dict):
            return "any"
        if type_ast.get("type") == "identifier":
            return str(type_ast.get("value", "any"))
        if type_ast.get("type") == "string":
            return str(type_ast.get("value", "any"))
        return "any"

    @staticmethod
    def _valueMatchesDeclaredType(value: dict, declared_type: str) -> bool:
        if declared_type == "any":
            return True
        if declared_type == "idarray":
            if value.get("type") != "array":
                return False
            return all(isinstance(item, dict) and item.get("type") == "identifier" for item in value.get("items", []))
        if "|" in declared_type:
            return any(Builtins._valueMatchesDeclaredType(value, branch.strip()) for branch in declared_type.split("|"))
        return value.get("type") == declared_type

    @staticmethod
    def call(interpreter, target, value: "any", **kwargs) -> dict: # type: ignore
        call_source = value.get("map", {}).get("call", {}).get("source")
        if not callable(call_source):
            interpreter.eh.throw("cannotCall", f"cannot call '{value.get('name', value.get('type'))}', got {type(call_source).__name__}")
        return call_source(interpreter, target, **kwargs)

    @staticmethod
    def fn(interpreter, target, name: "identifier", params: "map", body: "block", **kwargs) -> dict: # type: ignore
        function_name = name["value"]
        declared_params: list[tuple[str, str]] = []
        for param_name, type_ast in params.get("map", {}).items():
            declared_params.append((param_name, Builtins._declaredTypeName(type_ast)))

        def runtime_fn(interpreter, target, **call_kwargs):
            previous_ast = interpreter.current_ast
            function_scope = interpreter.perkeo.res.Scope(interpreter, f"fn:{function_name}", {})

            for param_name, expected_type in declared_params:
                if param_name not in call_kwargs:
                    interpreter.eh.throw("tooFewArguments", f"missing required parameter '{param_name}' for function '{function_name}'.")
                arg_value = call_kwargs[param_name]
                if not isinstance(arg_value, dict):
                    interpreter.eh.throw("typeError", f"parameter '{param_name}' expects '{expected_type}', got non-Perkeo value.")
                if not Builtins._valueMatchesDeclaredType(arg_value, expected_type):
                    interpreter.eh.throw("typeError", f"parameter '{param_name}' expects '{expected_type}', got '{arg_value.get('type')}'.")

            for arg_name, arg_value in call_kwargs.items():
                if isinstance(arg_value, dict):
                    function_scope.set(arg_name, copy.deepcopy(arg_value))

            interpreter.scopes.insert(0, function_scope)
            try:
                result: dict = {"type": "null", "map": {}, "span": body["span"]}
                for body_item in body.get("body", []):
                    interpreter.current_ast = body_item
                    interpreted = interpreter.interpret()
                    if isinstance(interpreted, dict):
                        result = interpreted
                return result
            finally:
                interpreter.scopes.pop(0)
                interpreter.current_ast = previous_ast

        fn_ast = Builtins.getASTOf(interpreter, function_name, source=runtime_fn)
        fn_ast["span"] = name["span"]
        interpreter.scopes[-1].set(function_name, fn_ast)
        return fn_ast

    @staticmethod
    def _asSources(raw) -> list[dict]:
        sources = []
        for node in Builtins._asIdentifierNodes(raw) if raw else []:
            raw_val = node["value"]
            if "::" not in raw_val:
                continue
            s_type, s_path = raw_val.split("::", 1)
            s_path = s_path.strip().strip('"').strip("'")
            sources.append({"type": s_type, "value": s_path, "span": node["span"]})
        return sources

    @staticmethod
    def _resolveSourcePath(interpreter, src: dict) -> str | None:
        s_type, s_path = src["type"], src["value"]

        def _local_to_fs(p: str):
            file_part = p.split(":")[0]
            file_part = file_part.removesuffix(".pk")
            parts = file_part.replace("/", ".").split(".")
            return os.path.join(os.path.dirname(interpreter.perkeo.file_path), *parts) + ".pk"

        if s_type == "source":
            if s_path.startswith("pko."):
                py_path = os.path.join(interpreter.perkeo.path, "resources", "lib", *s_path.removeprefix("pko.").split(".")) + ".py"
                if os.path.isfile(py_path):
                    return py_path
            path = _local_to_fs(s_path)
            return path if os.path.isfile(path) else None

        if s_type == "filesource":
            path = s_path if os.path.isabs(s_path) else os.path.join(os.path.dirname(interpreter.perkeo.file_path), s_path)
            return path if os.path.isfile(path) else None

        if s_type == "ghsource":
            cache_base = os.path.join(os.path.dirname(interpreter.perkeo.file_path), "pk_modules")
            if ":" in s_path:
                repo, file_name = s_path.split(":", 1)
            else:
                repo, file_name = s_path, "mylib.pk"

            branch = "main"
            if "@" in repo:
                repo, branch = repo.split("@", 1)

            file_name = file_name.lstrip("/")
            if not (file_name.endswith(".pk") or file_name.endswith(".py")):
                file_name = f"{file_name}.pk"

            branches = [branch] if "@" in s_path.split(":", 1)[0] else ["main", "master", "trunk", "dev"]
            github_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

            for candidate_branch in branches:
                fs_path = os.path.join(cache_base, "github.com", repo, candidate_branch, file_name)
                if os.path.isfile(fs_path):
                    return fs_path

                url = f"https://raw.githubusercontent.com/{repo}/{candidate_branch}/{file_name}"
                os.makedirs(os.path.dirname(fs_path), exist_ok=True)
                try:
                    import urllib.request
                    request = urllib.request.Request(url)
                    if github_token:
                        request.add_header("Authorization", f"Bearer {github_token}")
                    with urllib.request.urlopen(request) as response, open(fs_path, "wb") as target_file:
                        target_file.write(response.read())
                    return fs_path
                except Exception:
                    continue
            return None

        if s_type == "websource":
            from urllib.parse import urlparse

            normalized_url = s_path if "://" in s_path else f"https://{s_path}"
            parsed = urlparse(normalized_url)
            if not parsed.scheme or not parsed.netloc:
                return None

            relative = parsed.path.lstrip("/")
            if not relative:
                relative = "index.pk"
                normalized_url = normalized_url.rstrip("/") + "/index.pk"
            elif not (relative.endswith(".pk") or relative.endswith(".py")):
                relative = f"{relative}.pk"
                normalized_url = normalized_url.rstrip("/") + ".pk"

            cache_base = os.path.join(os.path.dirname(interpreter.perkeo.file_path), "pk_modules")
            fs_path = os.path.join(cache_base, parsed.netloc, relative)
            if not os.path.isfile(fs_path):
                os.makedirs(os.path.dirname(fs_path), exist_ok=True)
                try:
                    import urllib.request
                    urllib.request.urlretrieve(normalized_url, fs_path)
                except Exception:
                    return None
            return fs_path
        return None

    @staticmethod
    def _loadExportsFromPath(interpreter, path: str, span: dict) -> dict[str, dict]:
        extension = path.rsplit(".", 1)[-1].lower()
        if extension == "pk":
            return Builtins._loadPkExports(interpreter, path)
        if extension == "py":
            module_name = "perkeo_external_module"
            injected_sys_path: str | None = None

            module_dir = os.path.dirname(path)
            package_parts: list[str] = []
            cursor = module_dir
            while os.path.isfile(os.path.join(cursor, "__init__.py")):
                package_parts.insert(0, os.path.basename(cursor))
                parent = os.path.dirname(cursor)
                if parent == cursor:
                    break
                cursor = parent

            if package_parts:
                module_name = ".".join(package_parts + [os.path.splitext(os.path.basename(path))[0]])
                injected_sys_path = cursor
                if injected_sys_path not in sys.path:
                    sys.path.insert(0, injected_sys_path)

            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    interpreter.eh.throw("sourceNotFound", f"could not load python source for path '{path}'")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                try:
                    spec.loader.exec_module(module)
                except ImportError as err:
                    # Standalone remote Python files may contain relative imports
                    # that require package files we did not fetch. In that case,
                    # keep import flow alive and allow module-map fallback.
                    if "attempted relative import with no known parent package" in str(err):
                        return {}
                    raise
                return Builtins._loadPyExports(module, span, interpreter)
            finally:
                if injected_sys_path and injected_sys_path in sys.path:
                    try:
                        sys.path.remove(injected_sys_path)
                    except ValueError:
                        pass
        interpreter.eh.throw("sourceNotFound", f"unsupported source file extension '{extension}' for path '{path}'")

    @staticmethod
    def _importFromExports(interpreter, import_name: str, exports: dict[str, dict], span: dict, module_alias: str | None = None, preserve_pk_merge: bool = False) -> bool:
        import_name_lower = import_name.lower()
        if import_name_lower == "map":
            alias = module_alias or "module"
            interpreter.scopes[-1].set(alias, {
                "type": "map",
                "map": exports,
                "truthiness": lambda x: bool(x["map"]),
                "span": span,
            })
            return True
        if import_name_lower == "all":
            for key, export_value in exports.items():
                interpreter.scopes[-1].set(key, copy.deepcopy(export_value))
            return True
        if import_name not in exports:
            return False
        if preserve_pk_merge:
            for key, export_value in exports.items():
                interpreter.scopes[-1].set(key, copy.deepcopy(export_value))
            return True
        interpreter.scopes[-1].set(import_name, copy.deepcopy(exports[import_name]))
        return True

    @staticmethod
    def _importAsModuleMap(interpreter, import_name: str, exports: dict[str, dict], span: dict) -> None:
        interpreter.scopes[-1].set(import_name, {
            "type": "map",
            "map": copy.deepcopy(exports),
            "truthiness": lambda x: bool(x["map"]),
            "span": span,
        })

    @staticmethod
    def _matchesModuleAlias(import_name: str, module_alias: str | None) -> bool:
        if not module_alias:
            return False
        return import_name in {module_alias, module_alias.strip("_")}
            
    @staticmethod
    def import_(interpreter, target, value: "identifier|array|string" = None, sheet: "identifier|array|string" = None, **sources) -> None: # type: ignore
        if not value and not sheet:
            interpreter.eh.throw("tooFewArguments", "'import' expects either library or sheet provided.")
        target_nodes = Builtins._asIdentifierNodes(value) if value else []
        source_nodes = Builtins._asIdentifierNodes(sheet) if sheet else []
        source_list = (Builtins._asSources(sheet) if sheet else []) + Builtins._asSourceKwargs(sources)
        display_source_list = "[" + " ".join([f"{item.get('type', '?')}::{item.get('value', '')}" for item in source_list]) + "]"
        sheet_nodes = [node for node in source_nodes if "::" not in node["value"]]
        if sheet_nodes:
            for single_value in sheet_nodes:
                sheet_name = single_value["value"]
                base_dir = os.path.join(interpreter.perkeo.path, "resources", "libpkis") if sheet_name.startswith("pko.") else os.path.dirname(interpreter.perkeo.file_path)
                file_name = f"{sheet_name.removeprefix('pko.')}.pkis"
                pkis_path = os.path.join(base_dir, file_name)
                if not os.path.isfile(pkis_path):
                    interpreter.eh.throw("sheetNotFound", f"could not find import sheet file \"{single_value['value']}.pkis\"")
                with open(pkis_path) as file:
                    content = file.read()
                for import_id in content.splitlines():
                    import_name = import_id.strip()
                    if not import_name or import_name.startswith("#"):
                        continue
                    Builtins.import_(
                        interpreter,
                        target,
                        {"type": "identifier", "value": import_name, "map": {}, "span": single_value["span"]},
                    )
        if source_list and not target_nodes:
            interpreter.eh.throw("tooFewArguments", "'import' expects one or more target identifiers when using source sheets.")
        if source_list:
            for t_node in target_nodes:
                import_name = t_node["value"]
                imported = False

                for src in source_list:
                    handler_exports, redirect_path = Builtins._load_source_handler_exports(interpreter, src, import_name)
                    if handler_exports:
                        module_alias = os.path.splitext(os.path.basename(src["value"]))[0]
                        if Builtins._importFromExports(interpreter, import_name, handler_exports, t_node["span"], module_alias=module_alias):
                            imported = True
                            break
                        if redirect_path:
                            handler_path = Builtins._sourceHandlerPath(interpreter, src["type"])
                            resolved_redirect = redirect_path if os.path.isabs(redirect_path) else os.path.join(os.path.dirname(handler_path), redirect_path)
                            if os.path.isfile(resolved_redirect):
                                exports = Builtins._loadExportsFromPath(interpreter, resolved_redirect, t_node["span"])
                                if Builtins._importFromExports(interpreter, import_name, exports, t_node["span"], module_alias=module_alias):
                                    imported = True
                                    break

                    resolved = Builtins._resolve_source_path(interpreter, src)
                    if not resolved:
                        continue

                    exports = Builtins._loadExportsFromPath(interpreter, resolved, t_node["span"])
                    module_alias = os.path.splitext(os.path.basename(resolved))[0]
                    if Builtins._importFromExports(interpreter, import_name, exports, t_node["span"], module_alias=module_alias):
                        imported = True
                        break
                    if Builtins._matchesModuleAlias(import_name, module_alias):
                        Builtins._importAsModuleMap(interpreter, import_name, exports, t_node["span"])
                        imported = True
                        break

                if not imported:
                    interpreter.eh.throw("sourceNotFound", f"could not find \"{import_name}\" in any of {display_source_list}")
            return
        if target_nodes:
            for single_value in target_nodes:
                parts = single_value["value"].split(".")
                if len(parts) < 2:
                    interpreter.eh.throw("incompleteImport", "you must provide a specific variable to import from that source.")

                source_parts = parts[:-1]
                import_name = parts[-1]
                source_name = ".".join(source_parts)

                if parts[0] == "pko":
                    if len(parts) < 3:
                        interpreter.eh.throw("incompleteImport", "you must provide a specific variable to import from that source.")
                    path = os.path.join(interpreter.perkeo.path, "resources", "lib", *parts[1:-1]) + ".py"
                else:
                    handler_type = source_name
                    handler_path = Builtins._sourceHandlerPath(interpreter, handler_type)
                    if os.path.isfile(handler_path):
                        handler_exports, redirect_path = Builtins._load_source_handler_exports(
                            interpreter,
                                {"type": handler_type, "value": import_name, "span": single_value["span"]},
                            import_name,
                        )
                        if handler_exports:
                            module_alias = source_parts[-1]
                            imported = Builtins._importFromExports(
                                interpreter,
                                import_name,
                                handler_exports,
                                single_value["span"],
                                module_alias=module_alias,
                            )
                            if not imported and redirect_path:
                                resolved_redirect = redirect_path if os.path.isabs(redirect_path) else os.path.join(os.path.dirname(handler_path), redirect_path)
                                if os.path.isfile(resolved_redirect):
                                    exports = Builtins._loadExportsFromPath(interpreter, resolved_redirect, single_value["span"])
                                    imported = Builtins._importFromExports(
                                        interpreter,
                                        import_name,
                                        exports,
                                        single_value["span"],
                                        module_alias=module_alias,
                                        preserve_pk_merge=resolved_redirect.endswith(".pk"),
                                    )
                            if imported:
                                continue

                    path = os.path.join(os.path.dirname(interpreter.perkeo.file_path), *parts[:-1]) + ".pk"

                if not os.path.isfile(path):
                    interpreter.eh.throw("sourceNotFound", f"could not find a source file for \"{source_name}\"")

                exports = Builtins._loadExportsFromPath(interpreter, path, single_value["span"])
                module_alias = source_parts[-1]
                imported = Builtins._importFromExports(
                    interpreter,
                    import_name,
                    exports,
                    single_value["span"],
                    module_alias=module_alias,
                    preserve_pk_merge=path.endswith(".pk"),
                )

                if not imported:
                    if path.endswith(".pk"):
                        interpreter.eh.throw("importScopeError", f"could not find exported identifier \"{import_name}\" in source \"{source_name}\"")
                    interpreter.eh.throw("importScopeError", f"could not find a variable with identifier \"{import_name}\"\nin the global scope from imported source \"{source_name}\"")

    @staticmethod
    def export_(interpreter, target, value: "identifier|array" = None) -> None: # type: ignore
        identifiers = Builtins._asIdentifierNodes(value)
        if not identifiers:
            interpreter.eh.throw("tooFewArguments", "'export' expects one or more identifiers.")

        for identifier in identifiers:
            export_name = identifier["value"]
            ast = interpreter.findVariable(export_name, scopes=["global"], error=False)
            if ast is None:
                interpreter.eh.throw("scopeError", f"identifier '{export_name}' is not associated with a value in the global scope.")
            if isinstance(ast, dict):
                ast["exported"] = True