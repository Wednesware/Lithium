import copy
import inspect, os
from decimal import Decimal


class Interpreter:
    def __init__(self, perkeo) -> None:
        self.perkeo = perkeo
        self.current_ast: dict | None = None
        self.current_call: dict | None = None
        self.current_call_target: dict | None = None
        self.ast_history: list[dict] = []
        self._suppress_base_level: bool = False
        self.eh = self.perkeo.res.ErrorHandler(self)
        self.stringifier = self.perkeo.res.Stringifier(self)
        self.outputs: list[str] = ["terminal"]
        self.posts: list[str] = []
        builtins = {
            "import": self.perkeo.res.Builtins.getASTOf(self, "import", "import_"),
            "export": self.perkeo.res.Builtins.getASTOf(self, "export", "export_"),
            "call": self.perkeo.res.Builtins.getASTOf(self, "call"),
            "fn": self.perkeo.res.Builtins.getASTOf(self, "fn"),
            "true": {"type": "boolean", "value": True, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": "true", "truthiness": lambda x: bool(x["value"])},
            "on": {"type": "boolean", "value": True, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": "on", "truthiness": lambda x: bool(x["value"])},
            "enabled": {"type": "boolean", "value": True, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": "enabled", "truthiness": lambda x: bool(x["value"])},
            "yes": {"type": "boolean", "value": True, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": "yes", "truthiness": lambda x: bool(x["value"])},
            "false": {"type": "boolean", "value": False, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": "false", "truthiness": lambda x: bool(x["value"])},
            "off": {"type": "boolean", "value": False, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": "off", "truthiness": lambda x: bool(x["value"])},
            "disabled": {"type": "boolean", "value": False, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": "disabled", "truthiness": lambda x: bool(x["value"])},
            "no": {"type": "boolean", "value": False, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": "no", "truthiness": lambda x: bool(x["value"])},
            "null": {"type": "null", "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "nan": {"type": "nan", "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}}
        }
        for operator_name, source_name in self.perkeo.res.Builtins.OPERATOR_BUILTINS.items():
            builtins[operator_name] = self.perkeo.res.Builtins.getOperatorASTOf(self, operator_name, source_name)
        for unit_name in self.perkeo.res.Builtins.UNIT_DEFS:
            builtins[unit_name] = self.perkeo.res.Builtins.getUnitASTOf(self, unit_name, source=self.perkeo.res.Builtins.unitCall)
        self.scopes: list = [
            self.perkeo.res.Scope(self, "global", builtins)
        ]
    def _isBaseLevel(self) -> bool:
        return not self._suppress_base_level and self.ast_history[-2]["type"] == "line"
    def runCode(self) -> None:
        self.current_ast = self.perkeo.full_ast
        self.interpret()
    def findVariable(self, ident: str, scopes: list[str] | None = None, error: bool = True) -> any:
        for scope in self.scopes:
            if scopes is not None and scope.name not in scopes:
                continue
            if ident in scope.vars:
                return scope.get(ident)
        if error:
            self.eh.throw("scopeError", f"identifier '{ident}' is not associated with a value in any scope.")
    def _instanceScopeForCallTarget(self, target_ast: dict):
        # Methods are stored as plain function values inside a class/instance
        # map and don't carry an implicit "self" binding. When a call target
        # is a dotted identifier (e.g. `fido.speak`), expose the owning
        # instance/class's fields as an extra scope for the duration of the
        # call so bare identifiers in the method body (e.g. `sound`) resolve
        # to the instance's own fields via the existing dynamic-scoping rules.
        if not isinstance(target_ast, dict) or target_ast.get("type") != "identifier":
            return None
        ident = str(target_ast.get("value", ""))
        if "." not in ident:
            return None
        parts = ident.split(".")
        owner = self.findVariable(parts[0], error=False)
        for part in parts[1:-1]:
            if not isinstance(owner, dict):
                return None
            owner = owner.get("map", {}).get(part)
        if not isinstance(owner, dict) or not isinstance(owner.get("map"), dict):
            return None
        return self.perkeo.res.Scope(self, "instance", owner["map"])
    def _assignDottedIdentifier(self, ident: str, value: dict) -> None:
        parts = ident.split(".")
        owner = self.findVariable(parts[0], error=False)
        if owner is None:
            self.eh.throw("scopeError", f"identifier '{parts[0]}' is not associated with a value in any scope.")
        for part in parts[1:-1]:
            if not isinstance(owner, dict):
                self.eh.throw("scopeError", f"identifier '{ident}' cannot access member '{part}' on non-object value.")
            owner_map = owner.get("map")
            if not isinstance(owner_map, dict) or part not in owner_map:
                self.eh.throw("scopeError", f"identifier '{ident}' has no member '{part}'.")
            owner = owner_map[part]
        if not isinstance(owner, dict) or not isinstance(owner.get("map"), dict):
            self.eh.throw("scopeError", f"identifier '{ident}' cannot assign a member on a non-object value.")
        owner["map"][parts[-1]] = value
    def _resolve_dotted_identifier(self, ident: str) -> dict | None:
        if "." not in ident:
            return None

        parts = ident.split(".")
        base = self.findVariable(parts[0], error=False)
        if base is None:
            return None

        current = base
        for index, part in enumerate(parts[1:], start=1):
            if not isinstance(current, dict):
                self.eh.throw("scopeError", f"identifier '{ident}' cannot access member '{part}' on non-object value.")
            current_map = current.get("map")
            if not isinstance(current_map, dict):
                self.eh.throw("scopeError", f"identifier '{ident}' cannot access member '{part}' on non-object value.")
            if part not in current_map:
                owner_path = ".".join(parts[:index])
                self.eh.throw("scopeError", f"identifier '{owner_path}' has no member '{part}'.")
            current = current_map[part]

        return current
    def _expected_types_for_parameter(self, parameter: inspect.Parameter) -> list[str]:
        annotation = parameter.annotation
        if annotation is inspect.Parameter.empty:
            exp_types: list[str] = ["any"]
        elif isinstance(annotation, str):
            exp_types = self._split_annotation_variants(annotation)
        else:
            exp_types = [str(annotation)]

        if not exp_types:
            exp_types = ["any"]
        if ("idarray" in exp_types) and ("array" not in exp_types):
            exp_types.append("array")
        return exp_types

    def _split_annotation_variants(self, annotation: str) -> list[str]:
        variants: list[str] = []
        current: list[str] = []
        depth = 0

        for char in annotation:
            if char == "[":
                depth += 1
                current.append(char)
                continue
            if char == "]":
                depth = max(0, depth - 1)
                current.append(char)
                continue
            if char == "|" and depth == 0:
                token = "".join(current).strip()
                if token:
                    variants.append(token)
                current = []
                continue
            current.append(char)

        token = "".join(current).strip()
        if token:
            variants.append(token)
        return variants

    def _parse_array_annotation_item_types(self, annotation: str) -> set[str] | None:
        normalized = annotation.strip()
        if not (normalized.startswith("array[") and normalized.endswith("]")):
            return None

        inner = normalized[6:-1].strip()
        if not inner:
            return set()

        allowed: set[str] = set()
        token: list[str] = []
        for char in inner:
            if char in {" ", "\t", "\n", ",", "|"}:
                candidate = "".join(token).strip()
                if candidate:
                    allowed.add(candidate)
                token = []
                continue
            token.append(char)

        candidate = "".join(token).strip()
        if candidate:
            allowed.add(candidate)
        return allowed

    def _matches_expected_type(self, value: any, expected_type: str) -> bool:
        if expected_type == "any":
            return True

        value_type = self._value_type_name(value)
        if expected_type == "idarray":
            if value_type != "array" or not isinstance(value, dict):
                return False
            return all(isinstance(item, dict) and item.get("type") == "identifier" for item in value.get("items", []))

        array_item_types = self._parse_array_annotation_item_types(expected_type)
        if array_item_types is not None:
            if value_type != "array" or not isinstance(value, dict):
                return False
            if not array_item_types:
                return True
            for item in value.get("items", []):
                if self._value_type_name(item) not in array_item_types:
                    return False
            return True

        return value_type == expected_type

    def _array_annotation_accepts_identifier_items(self, expected_types: list[str]) -> bool:
        for expected_type in expected_types:
            item_types = self._parse_array_annotation_item_types(expected_type)
            if item_types is None:
                continue
            if "identifier" in item_types:
                return True
        return False
    def _value_type_name(self, value: any) -> str:
        if isinstance(value, dict):
            return value.get("type", "map")
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, (float, Decimal)):
            return "float"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if value is None:
            return "null"
        return type(value).__name__
    def interpret(self) -> dict | None:
        self.ast_history.append(self.current_ast)
        try:
            interpret_function: callable = getattr(self, f"interpret{self.current_ast['type'].capitalize()}")
        except AttributeError:
            self.eh.throw("invalidToken", f"interpreter does not recognize ast token {self.current_ast['type']!r}")
        if self.perkeo.getsetting("verbose"):
            print(f"{os.path.basename(self.perkeo.file_path)}: now interpreting: {self.current_ast['type']} at {', '.join(f'{key}={value}' for key, value in self.current_ast.get('span', {}).items()) if 'span' in self.current_ast else '(unknown)'}")
            print(f"  { {key: value for key, value in self.current_ast.items() if key not in ['span', 'type']} }")
            print(f"  {interpret_function.__name__}()")
        result: dict | None = interpret_function()
        if isinstance(result, dict) and result.get("map") and result.get("type") != "map":
            # This recursion re-runs interpret() for each nested value purely to
            # wire up lazy call metadata (e.g. interpretInteger's integerCall).
            # It isn't itself a bare top-level statement, so make sure nested
            # values (e.g. a class/instance's string fields) don't trigger
            # interpretString's base-level auto-print side effect.
            previous_suppress = self._suppress_base_level
            self._suppress_base_level = True
            try:
                for k, v in result["map"].items():
                    if isinstance(v, dict) and v.get("type"):
                        self.current_ast = v
                        result["map"][k] = self.interpret()
            finally:
                self._suppress_base_level = previous_suppress
        self.ast_history.pop()
        return result
    def interpretScript(self) -> None:
        for body_item in self.current_ast["body"]:
            self.current_ast = body_item
            self.interpret()
    def interpretLine(self) -> dict | None:
        line_value = self.current_ast["value"]
        self.current_ast = line_value
        result = self.interpret()

        # A bare identifier on its own line implicitly calls zero-argument functions.
        if (
            line_value.get("type") == "identifier"
            and isinstance(result, dict)
            and result.get("type") == "function"
        ):
            self.current_ast = {
                "type": "call",
                "target": line_value,
                "args": {
                    "type": "map",
                    "map": {},
                    "span": line_value["span"],
                },
                "current_interp_arg": None,
                "span": line_value["span"],
            }
            result = self.interpret()
        return result
    def interpretCall(self) -> dict:
        call = self.current_ast
        raw_args = copy.deepcopy(call["args"])
        self.current_call = call
        self.current_ast = self.current_ast["target"]
        target = self.interpret()
        self.current_call_target = target
        self.current_ast = call["args"]
        args: dict = self.interpret()
        self.current_call = None
        self.current_call_target = None
        if target.get("type") == "operator" and not call.get("operator_syntax", False):
            self.eh.throw("notCallable", "operator values are not directly callable.")
        if target.get("type") == "unit" and not call.get("unit_syntax", False):
            self.eh.throw("notCallable", "unit values are not directly callable.")
        if call.get("unit_syntax", False) and target.get("type") != "unit":
            self.eh.throw("notCallable", f"postfix unit syntax requires a unit target, not {target.get('type')!r}.")
        if target["map"].get("call") and (target["map"]["call"]["type"] == "data"):
            signature = inspect.signature(target["map"]["call"]["source"])
            provided_arguments: int = len(call["args"]["map"])
            parameters = list(signature.parameters.values())
            runtime_parameters = parameters[2:]
            accepts_var_keyword = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in runtime_parameters)
            accepts_var_positional = any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in runtime_parameters)
            expected_arguments: int = sum(
                1
                for parameter in runtime_parameters
                if parameter.kind in {
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                }
            )
            required_arguments: int = sum(
                1
                for parameter in runtime_parameters
                if parameter.kind in {
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                }
                and parameter.default is inspect.Parameter.empty
            )
            for k, v in args["map"].items():
                if v is None:
                    continue
                if isinstance(v, dict):
                    self.current_ast = v
                try:
                    parameter = signature.parameters[k]
                except KeyError:
                    if accepts_var_keyword:
                        continue
                    self.eh.throw("noMatchingParameter", f"'{target['name']}' does not have a parameter matching '{k}'")

                exp_types = self._expected_types_for_parameter(parameter)
                value_type: str = self._value_type_name(v)
                if not any(self._matches_expected_type(v, expected_type) for expected_type in exp_types):
                    self.eh.throw("typeError", f"parameter '{k}' expects one of these types: [{' '.join(exp_types)}], not {value_type}.")
            if not accepts_var_keyword and not accepts_var_positional and provided_arguments > expected_arguments:
                self.eh.throw("tooManyArguments", f"too many arguments provided to {target['name']}. ({provided_arguments} prov. vs max of {expected_arguments} expected)")
            if provided_arguments < required_arguments:
                self.eh.throw("tooFewArguments", f"too few arguments provided to {target['name']}. ({provided_arguments} prov. vs min of {required_arguments} required)")
            previous_raw_call_args = getattr(self, "current_raw_call_args", None)
            self.current_raw_call_args = raw_args
            instance_scope = self._instanceScopeForCallTarget(call["target"])
            if instance_scope is not None:
                self.scopes.insert(0, instance_scope)
            try:
                return_value: dict | None = target["map"]["call"]["source"](self, target, **args["map"])
            finally:
                if instance_scope is not None:
                    self.scopes.pop(0)
                self.current_raw_call_args = previous_raw_call_args
            return {"type": "null", "map": {}, "span": call["span"]} if return_value is None else return_value
        else:
            self.eh.throw("notCallable", f"object of type '{target['type']}' is not callable.")
    def interpretIdentifier(self) -> dict:
        if self.current_call_target and self.current_call and self.current_call.get("current_interp_arg") is not None:
            if self.current_call_target["map"].get("call"):
                signature = inspect.signature(self.current_call_target["map"]["call"]["source"])
                accepts_var_keyword = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
                try:
                    parameter = signature.parameters[self.current_call["current_interp_arg"]]
                    accepted_types = self._expected_types_for_parameter(parameter)
                    if "identifier" in accepted_types or "idarray" in accepted_types:
                        return self.current_ast
                except KeyError:
                    if accepts_var_keyword:
                        return self.current_ast
                    self.eh.throw("noMatchingParameter", f"'{self.current_call_target['name']}' does not have a parameter matching '{self.current_call['current_interp_arg']}'")
        dotted_match = self._resolve_dotted_identifier(self.current_ast["value"])
        if dotted_match is not None:
            return dotted_match
        match = self.findVariable(self.current_ast["value"])
        return match
    def interpretOperator(self) -> dict:
        match = self.findVariable(self.current_ast["value"], error=False)
        if match is not None:
            return match
        return self.current_ast
    def interpretMap(self) -> dict:
        map: dict = self.current_ast
        result: dict = {}
        for k, v in map["map"].items():
            if self.current_call:
                self.current_call["current_interp_arg"] = k
            self.current_ast = v
            result[k] = self.interpret()
        map["map"] = result
        if self._isBaseLevel():
            if map["map"] and "value" not in map["map"]:
                for k, v in map["map"].items():
                    if "." in k:
                        self._assignDottedIdentifier(k, v)
                    else:
                        self.scopes[-1].set(k, v)
        return map
    def interpretString(self) -> dict:
        if self._isBaseLevel():
            for output in self.outputs:
                if output == "terminal":
                    print(self.current_ast["value"])
                else:
                    if os.path.exists(output):
                        with open(output, "a") as file:
                            file.write(f"{self.current_ast['value']}\n")
        return self.current_ast
    def interpretInteger(self) -> dict:
        self.current_ast["name"] = "integerCall"
        self.current_ast["map"]["call"] = {
            "type": "data",
            "source": self.perkeo.res.Builtins.integerCall,
            "span": self.current_ast["span"]
        }
        self.current_ast["prio"] = 2
        return self.current_ast
    def interpretFloat(self) -> dict:
        return self.current_ast
    def interpretUnit(self) -> dict:
        match = self.findVariable(self.current_ast["value"], error=False)
        if match is not None:
            return match
        return self.current_ast
    def interpretArray(self) -> dict:
        array: dict = self.current_ast
        result: list = []
        preserve_identifiers = False
        if self.current_call_target and self.current_call and self.current_call.get("current_interp_arg") is not None:
            if self.current_call_target["map"].get("call"):
                signature = inspect.signature(self.current_call_target["map"]["call"]["source"])
                accepts_var_keyword = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
                try:
                    parameter = signature.parameters[self.current_call["current_interp_arg"]]
                    accepted_types = self._expected_types_for_parameter(parameter)
                    preserve_identifiers = "idarray" in accepted_types or self._array_annotation_accepts_identifier_items(accepted_types)
                except KeyError:
                    if accepts_var_keyword:
                        preserve_identifiers = True
                    else:
                        self.eh.throw("noMatchingParameter", f"'{self.current_call_target.get('name', 'object of type ' + self.current_call_target.get('type'))}' does not have a parameter matching '{self.current_call['current_interp_arg']}'")
        for item in self.current_ast["items"]:
            if preserve_identifiers and item.get("type") == "identifier":
                result.append(item)
                continue
            self.current_ast = item
            result.append(self.interpret())
        array["items"] = result
        return array
    def interpretFunction(self) -> dict:
        return self.current_ast
    def interpretGroup(self) -> dict:
        group: dict = self.current_ast
        if group.get("value") is None:
            return group
        self.current_ast = group["value"]
        evaluated = self.interpret()
        group["value"] = evaluated
        return evaluated
    def interpretBlock(self) -> dict:
        self.scopes.append(self.perkeo.res.Scope(self, "local", {}))
        return self.current_ast
    def interpretData(self) -> dict:
        return self.current_ast
    def interpretQuantity(self) -> dict:
        return self.current_ast
    def interpretClass(self) -> dict:
        return self.current_ast
    def interpretInstance(self) -> dict:
        return self.current_ast
    def interpretNull(self) -> dict:
        return self.current_ast
    def interpretNan(self) -> dict:
        return self.current_ast
    def interpretComment(self) -> dict:
        return {"type": "null", "map": {}, "span": self.current_ast["span"]}