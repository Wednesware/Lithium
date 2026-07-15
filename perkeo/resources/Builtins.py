import os, importlib, importlib.util


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
        "|": "logicor",
        "&": "logicand",
        "..": "range",
        "..=": "rangeincl",
        ":": "span"
    }

    @staticmethod
    def getASTOf(interpreter, name: str, source_name: str | None = None) -> dict:
        return {
            name: {
                "type": "function",
                "name": name,
                "truthiness": lambda _: True,
                "map": {
                    "call": {
                        "type": "data",
                        "source": getattr(Builtins, source_name or name),
                        "span": interpreter.perkeo.res.Token.emptySpan()
                    }
                }
            }
        }

    @staticmethod
    def _as_number(node: dict) -> int | float:
        if node.get("type") not in {"integer", "float"}:
            raise TypeError(f"expected numeric literal, got {node.get('type')!r}")
        return node["value"]

    @staticmethod
    def _wrap_number(value: int | float, span: dict) -> dict:
        if isinstance(value, float):
            return {"type": "float", "value": value, "map": {}, "span": dict(span)}
        return {"type": "integer", "value": value, "map": {}, "span": dict(span)}

    @staticmethod
    def _binary_items(value: dict) -> tuple[dict, dict]:
        if value.get("type") == "array" and "items" in value:
            items = value["items"]
        elif value.get("type") == "map" and value.get("map"):
            nested = value["map"].get("value")
            if nested is None:
                raise TypeError(f"expected binary call operands, got {value.get('type')!r}")
            if nested.get("type") == "array" and "items" in nested:
                items = nested["items"]
            else:
                items = [nested, nested]
        else:
            raise TypeError(f"expected binary call operands, got {value.get('type')!r}")

        if len(items) != 2:
            raise TypeError(f"expected 2 operands, got {len(items)}")
        return items[0], items[1]

    @staticmethod
    def integerCall(interpreter, target, value: "integer|float") -> dict: # type: ignore
        if value.get("type") not in {"integer", "float"}:
            raise TypeError(f"expected numeric literal, got {value.get('type')!r}")
        return value

    @staticmethod
    def add(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value + right_value, value["span"])

    @staticmethod
    def sub(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value - right_value, value["span"])

    @staticmethod
    def mul(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value * right_value, value["span"])

    @staticmethod
    def div(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value / right_value, value["span"])

    @staticmethod
    def mod(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value % right_value, value["span"])
    
    @staticmethod
    def exp(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value ** right_value, value["span"])
    
    @staticmethod
    def pctof(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value / 100 * right_value, value["span"])

    @staticmethod
    def eq(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(1 if left_value == right_value else 0, value["span"])

    @staticmethod
    def ne(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(1 if left_value != right_value else 0, value["span"])

    @staticmethod
    def gt(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(1 if left_value > right_value else 0, value["span"])

    @staticmethod
    def gte(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(1 if left_value >= right_value else 0, value["span"])

    @staticmethod
    def lt(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(1 if left_value < right_value else 0, value["span"])

    @staticmethod
    def lte(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(1 if left_value <= right_value else 0, value["span"])
    
    @staticmethod
    def logicor(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value if left["truthiness"](left) else right_value, value["span"])
    
    @staticmethod
    def logicand(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_number(left_value if not left["truthiness"](left) else right_value, value["span"])
    
    @staticmethod
    def range(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return {
            "type": "array",
            "items": [
                Builtins._wrap_number(item, value["span"])
                for item in range(left_value, right_value)
            ],
            "map": {},
            "truthiness": lambda x: bool(x["items"]),
            "span": value["span"],
        }

    @staticmethod
    def rangeincl(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return {
            "type": "array",
            "items": [
                Builtins._wrap_number(item, value["span"])
                for item in range(left_value, right_value + 1)
            ],
            "map": {},
            "truthiness": lambda x: bool(x["items"]),
            "span": value["span"],
        }
        
    @staticmethod
    def span(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return {
            "type": "map",
            "map": {
                "start": Builtins._wrap_number(left_value, value["span"]),
                "end": Builtins._wrap_number(right_value, value["span"]),
            },
            "truthiness": lambda x: bool(x["map"]),
            "span": value["span"],
        }

    @staticmethod
    def print(interpreter, target, value: "any" = None, to: "identifier|array" = None, lib: "identifier|array" = None) -> None: # type: ignore
        print(interpreter.stringifier.stringify(value))
    @staticmethod
    def import_(interpreter, target, value: "identifier") -> dict | None: # type: ignore
        parts: list[str] = value["value"].split(".")
        path: str = os.path.join(interpreter.perkeo.path, "lib", *parts[1:-2], parts[-1] + ".py") if parts[0] == "pko" else os.path.join(interpreter.perkeo.getsetting("current_directory"), *parts[:-1])
        spec: any = importlib.util.spec_from_file_location(value["value"], path)
        module: any = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except FileNotFoundError:
            interpreter.eh.throw("sourceNotFound", f"could not find a source file for \"{'.'.join(parts[:-1])}\".\nare you sure you spelled the name correctly?")