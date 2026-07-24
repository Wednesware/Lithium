import copy
import importlib
import importlib.util
import os


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

    OPERATOR_PRIORITIES = {
        "|": 1,
        "&": 1,
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
    }

    @staticmethod
    def _callable_priority(source: callable | None, default: int | None = None) -> int | None:
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
        resolved_prio = Builtins._callable_priority(
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
                    "span": interpreter.perkeo.res.Token.emptySpan()
                }
            },
            "span": interpreter.perkeo.res.Token.emptySpan()
        }
        if resolved_prio is not None:
            function_node["prio"] = resolved_prio
        return {
            name: function_node
        }

    @staticmethod
    def getOperatorASTOf(interpreter, name: str, source_name: str | None = None, source: callable | None = None, prio: int | None = None) -> dict:
        resolved_source = source or getattr(Builtins, source_name or name)
        resolved_prio = Builtins._callable_priority(
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
                    "span": interpreter.perkeo.res.Token.emptySpan()
                }
            },
            "span": interpreter.perkeo.res.Token.emptySpan()
        }
        if resolved_prio is not None:
            operator_node["prio"] = resolved_prio
        return {
            name: operator_node
        }

    @staticmethod
    def getUnitASTOf(interpreter, name: str, source_name: str | None = None, source: callable | None = None, prio: int | None = None) -> dict:
        resolved_source = source or getattr(Builtins, source_name or name)
        resolved_prio = Builtins._callable_priority(
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
                    "span": interpreter.perkeo.res.Token.emptySpan()
                }
            },
            "span": interpreter.perkeo.res.Token.emptySpan()
        }
        if resolved_prio is not None:
            unit_node["prio"] = resolved_prio
        return {name: unit_node}

    @staticmethod
    def _as_identifier_nodes(value: dict | None) -> list[dict]:
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
    def _node_from_python_value(value, span: dict, interpreter) -> dict:
        if isinstance(value, dict) and value.get("type"):
            return copy.deepcopy(value)
        if isinstance(value, bool):
            return {"type": "boolean", "value": value, "map": {}, "usedalias": str(value).lower(), "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if isinstance(value, int):
            return {"type": "integer", "value": value, "map": {}, "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if isinstance(value, float):
            return {"type": "float", "value": value, "map": {}, "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if isinstance(value, str):
            return {"type": "string", "value": value, "map": {}, "truthiness": lambda x: bool(x["value"]), "span": dict(span)}
        if value is None:
            return {"type": "null", "map": {}, "span": dict(span)}
        if isinstance(value, (list, tuple)):
            return {
                "type": "array",
                "items": [Builtins._node_from_python_value(item, span, interpreter) for item in value],
                "map": {},
                "span": dict(span),
            }
        return {"type": "data", "source": value, "map": {}, "span": dict(span)}

    @staticmethod
    def _load_pk_exports(interpreter, path: str) -> dict[str, dict]:
        library_interpreter = interpreter.perkeo.script.runpk(
            path,
            override_perkeo=interpreter.perkeo.__class__(interpreter.perkeo.path, "lithium"),
        )["interpreter"]
        library_global_scope = library_interpreter.scopes[0]
        return {
            key: copy.deepcopy(value)
            for key, value in library_global_scope.vars.items()
            if isinstance(value, dict) and value.get("exported")
        }

    @staticmethod
    def _load_py_exports(module, span: dict, interpreter) -> dict[str, dict]:
        exports: dict[str, dict] = {}
        for key, value in vars(module).items():
            if not key.startswith("_pko_"):
                continue

            export_name = key.removeprefix("_pko_")
            if callable(value):
                exports[export_name] = Builtins.getASTOf(interpreter, export_name, source=value)[export_name]
            else:
                exports[export_name] = Builtins._node_from_python_value(value, span, interpreter)
        return exports

    @staticmethod
    def _as_number(node: dict) -> int | float:
        if node.get("type") not in {"integer", "float"}:
            raise TypeError(f"expected numeric literal, got {node.get('type')!r}")
        return node["value"]

    @staticmethod
    def _wrap_number(value: int | float, span: dict) -> dict:
        if isinstance(value, float):
            return {"type": "float", "value": value, "map": {}, "span": dict(span), "truthiness": lambda x: bool(x["value"])}
        return {"type": "integer", "value": value, "map": {}, "span": dict(span), "truthiness": lambda x: bool(x["value"])}

    @staticmethod
    def _wrap_boolean(value: int | float, span: dict) -> dict:
        return {"type": "boolean", "value": value, "map": {}, "span": dict(span), "truthiness": lambda x: bool(x["value"]), "usedalias": str(bool(value)).lower()}

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
    def integerCall(interpreter, target, value: "array") -> dict: # type: ignore
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
        if not right_value:
            interpreter.eh.throw("divisionByZero", "division by zero is not allowed, returning nan.", warning=True)
            return {"type": "nan", "map": {}, "span": value["span"], "truthiness": lambda x: False}
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
        return Builtins._wrap_boolean(left_value == right_value, value["span"])

    @staticmethod
    def ne(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_boolean(left_value != right_value, value["span"])

    @staticmethod
    def gt(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_boolean(left_value > right_value, value["span"])

    @staticmethod
    def gte(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_boolean(left_value >= right_value, value["span"])

    @staticmethod
    def lt(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_boolean(left_value < right_value, value["span"])

    @staticmethod
    def lte(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        left_value = Builtins._as_number(left)
        right_value = Builtins._as_number(right)
        return Builtins._wrap_boolean(left_value <= right_value, value["span"])
    
    @staticmethod
    def logicor(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        return Builtins._wrap_number(left["value"] if left["truthiness"](left) else right["value"], value["span"])
    
    @staticmethod
    def logicand(interpreter, target, value: "array") -> dict: # type: ignore
        left, right = Builtins._binary_items(value)
        return Builtins._wrap_number(left["value"] if not left["truthiness"](left) else right["value"], value["span"])
    
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
            for single_value in Builtins._as_identifier_nodes(sheet):
                sheet_name = single_value["value"]
                base_dir: str = os.path.join(interpreter.perkeo.path, "resources", "libpkis") if sheet_name.startswith("pko.") else os.path.dirname(interpreter.perkeo.file_path)
                file_name: str = f"{sheet_name.removeprefix('pko.')}.pkis"
                pkis_path: str = os.path.join(base_dir, file_name)
                if not os.path.isfile(pkis_path):
                    interpreter.eh.throw("sheetNotFound", f"could not find import sheet file \"{single_value['value']}.pkis\"")
                with open(pkis_path) as file:
                    content: str = file.read()
                for import_id in content.splitlines():
                    import_name = import_id.strip()
                    if not import_name or import_name.startswith("#"):
                        continue
                    Builtins.import_(interpreter, target, {"type": "identifier", "value": import_name, "map": {}, "span": single_value["span"]})
        if value:
            for single_value in Builtins._as_identifier_nodes(value):
                parts: list[str] = single_value["value"].split(".")
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
                    path = os.path.join(os.path.dirname(interpreter.perkeo.file_path), *parts[:-1]) + ".pk"

                if not os.path.isfile(path):
                    interpreter.eh.throw("sourceNotFound", f"could not find a source file for \"{source_name}\"")

                match path.split(".")[-1]:
                    case "pk":
                        exports = Builtins._load_pk_exports(interpreter, path)
                        if import_name == "map":
                            interpreter.scopes[-1].set(source_parts[-1], {
                                "type": "map",
                                "map": exports,
                                "truthiness": lambda x: bool(x["map"]),
                                "span": single_value["span"]
                            })
                            continue
                        elif import_name == "merge":
                            for key, export_value in exports.items():
                                interpreter.scopes[-1].set(key, export_value)
                            continue
                        if import_name not in exports:
                            interpreter.eh.throw("importScopeError", f"could not find exported identifier \"{import_name}\" in source \"{source_name}\"")
                        # Importing a specific symbol from a .pk module also makes
                        # the module's exported values available in caller scope.
                        for key, export_value in exports.items():
                            interpreter.scopes[-1].set(key, copy.deepcopy(export_value))
                    case "py":
                        spec = importlib.util.spec_from_file_location(source_parts[-1], path)
                        if spec is None or spec.loader is None:
                            interpreter.eh.throw("sourceNotFound", f"could not load python source for \"{source_name}\"")
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        exports = Builtins._load_py_exports(module, single_value["span"], interpreter)
                        if import_name == "map":
                            interpreter.scopes[-1].set(source_parts[-1], {
                                "type": "map",
                                "map": exports,
                                "truthiness": lambda x: bool(x["map"]),
                                "span": single_value["span"]
                            })
                            continue
                        elif import_name == "merge":
                            for key, export_value in exports.items():
                                interpreter.scopes[-1].set(key, export_value)
                            continue

                        if import_name not in exports:
                            interpreter.eh.throw("importScopeError", f"could not find a variable with identifier \"{import_name}\"\nin the global scope from imported source \"{source_name}\"")
                        interpreter.scopes[-1].set(import_name, exports[import_name])
        if not value and not sheet:
            interpreter.eh.throw("tooFewArguments", "'import' expects either library or sheet provided.")

    @staticmethod
    def export_(interpreter, target, value: "identifier|array" = None) -> None: # type: ignore
        identifiers = Builtins._as_identifier_nodes(value)
        if not identifiers:
            interpreter.eh.throw("tooFewArguments", "'export' expects one or more identifiers.")

        for identifier in identifiers:
            export_name = identifier["value"]
            ast = interpreter.findVariable(export_name, scopes=["global"], error=False)
            if ast is None:
                interpreter.eh.throw("scopeError", f"identifier '{export_name}' is not associated with a value in the global scope.")
            if isinstance(ast, dict):
                ast["exported"] = True
