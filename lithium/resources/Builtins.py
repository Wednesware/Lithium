from concurrent.futures import interpreter
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
    def getASTOf(interpreter, name: str, source_name: str | None = None, source: callable | None = None) -> dict:
        return {
            name: {
                "type": "function",
                "name": name,
                "truthiness": lambda _: True,
                "map": {
                    "call": {
                        "type": "data",
                        "source": source or getattr(Builtins, source_name or name),
                        "span": interpreter.perkeo.res.Token.emptySpan()
                    }
                },
                "span": interpreter.perkeo.res.Token.emptySpan()
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
            "map": {
                "start": Builtins._wrap_number(left_value, value["span"]),
                "end": Builtins._wrap_number(right_value, value["span"])
            },
            "truthiness": lambda x: bool(x["items"]),
            "stringify": lambda x: f"{x['map']['start']['value']}..{x['map']['end']['value']}",
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
            "map": {
                "start": Builtins._wrap_number(left_value, value["span"]),
                "end": Builtins._wrap_number(right_value, value["span"])
            },
            "truthiness": lambda x: bool(x["items"]),
            "stringify": lambda x: f"{x['map']['start']['value']}..={x['map']['end']['value']}",
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
            "truthiness": lambda x: bool(x["map"]["start"]["value"] and x["map"]["end"]["value"]),
            "stringify": lambda x: f"{x['map']['start']['value']}:{x['map']['end']['value']}",
            "span": value["span"],
        }

    @staticmethod
    def print(interpreter, target, value: "any" = None, to: "identifier|array" = None, lib: "identifier|array" = None) -> None: # type: ignore
        print(interpreter.stringifier.stringify(value))
    @staticmethod
    def import_(interpreter, target, value: "identifier|array|string" = None, sheet: "identifier|array|string" = None) -> None: # type: ignore
        if sheet:
            for single_value in (sheet["items"] if sheet["type"] == "array" else [sheet]):
                base_dir: str = os.path.join(interpreter.perkeo.path, "resources", "libpkis") if single_value["value"].startswith("pko:") else os.path.dirname(interpreter.perkeo.file_path)
                file_name: str = f"{single_value["value"].removeprefix("pko:")}.pkis"
                pkis_path: str = os.path.join(base_dir, file_name)
                if not os.path.isfile(pkis_path):
                    interpreter.eh.throw("sheetNotFound", f"could not find import sheet file \"{single_value['value']}.pkis\"")
                with open(pkis_path) as file:
                    content: str = file.read()
                for import_id in content.splitlines():
                    Builtins.import_(interpreter, target, {"type": "identifier", "value": import_id, "map": {}, "span": single_value["span"]})
        if value:
            for single_value in (value["items"] if value["type"] == "array" else [value]):
                parts: list[str] = single_value["value"].split(".")
                try:
                    path: str = os.path.join(interpreter.perkeo.path, "resources", "lib", *parts[1:-2], parts[-2] + ".py") if parts[0] == "pko" else os.path.join(os.path.dirname(interpreter.perkeo.file_path), *parts[:-2], parts[-2] + ".pk")
                except IndexError:
                    interpreter.eh.throw("incompleteImport", "you must provide a specific variable to import from that source.")
                if not os.path.isfile(path):
                    interpreter.eh.throw("sourceNotFound", f"could not find a source file for \"{'.'.join(parts[:-1])}\"")
                match path.split(".")[-1]:
                    case "pk":
                        interpreter = interpreter.perkeo.script.runpk(path)["interpreter"]
                        if parts[-1] == "map":
                            interpreter.scopes[-1].set(parts[-2], {
                                "type": "map",
                                "map": {k.removeprefix("_pko_"): (Builtins.getASTOf(interpreter, k.removeprefix("_pko_"), source=v)[k.removeprefix("_pko_")] if v["type"] == "function" else v) for k, v in interpreter.scopes[-1].items() if k.startswith("_pko_")},
                                "truthiness": lambda x: bool(x["map"]),
                                "span": single_value["span"]
                            })
                            continue
                        result: dict | None = interpreter.findVariable(parts[-1], scopes=["global"], error=False)
                        if not result:
                            interpreter.eh.throw("importScopeError", f"could not find a variable with identifier \"{parts[-1]}\"\nin the global scope from imported source \"{'.'.join(parts[:-1])}\"")
                        interpreter.scopes[-1].set(parts[-1], result[parts[-1]])
                    case "py":
                        spec = importlib.util.spec_from_file_location(parts[-1], path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        if parts[-1] == "map":
                            interpreter.scopes[-1].set(parts[-2], {
                                "type": "map",
                                "map": {k.removeprefix("_pko_"): (Builtins.getASTOf(interpreter, k.removeprefix("_pko_"), source=v)[k.removeprefix("_pko_")] if callable(v) else v) for k, v in vars(module).items() if k.startswith("_pko_")},
                                "truthiness": lambda x: bool(x["map"]),
                                "span": single_value["span"]
                            })
                            continue
                        raw_value = getattr(module, f"_pko_{parts[-1]}", None)
                        if raw_value is None:
                            interpreter.eh.throw("importScopeError", f"could not find a variable with identifier \"{parts[-1]}\"\nin the global scope from imported source \"{'.'.join(parts[:-1])}\"")
                        result: dict = Builtins.getASTOf(interpreter, parts[-1], source=raw_value)
                        interpreter.scopes[-1].set(parts[-1], result[parts[-1]])
        if not value and not sheet:
            interpreter.eh.throw("tooFewArguments", "'import' expects either library or sheet provided.")