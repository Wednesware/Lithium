import inspect, os


class Interpreter:
    def __init__(self, perkeo) -> None:
        self.perkeo = perkeo
        self.current_ast: dict | None = None
        self.current_call: dict | None = None
        self.current_call_target: dict | None = None
        self.ast_history: list[dict] = []
        self.eh = self.perkeo.res.ErrorHandler(self)
        self.stringifier = self.perkeo.res.Stringifier(self)
        self.outputs: list[str] = ["terminal"]
        self.posts: list[str] = []
        builtins = self.perkeo.res.Builtins.getASTOf(self, "import", "import_") | {
            "true": {"type": "boolean", "value": True, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "on": {"type": "boolean", "value": True, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "enabled": {"type": "boolean", "value": True, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "yes": {"type": "boolean", "value": True, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "false": {"type": "boolean", "value": False, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "off": {"type": "boolean", "value": False, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "disabled": {"type": "boolean", "value": False, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "no": {"type": "boolean", "value": False, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
            "null": {"type": "null", "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}},
        }
        for operator_name, source_name in self.perkeo.res.Builtins.OPERATOR_BUILTINS.items():
            builtins.update(self.perkeo.res.Builtins.getASTOf(self, operator_name, source_name))
        self.scopes: list = [
            self.perkeo.res.Scope(self, "global", builtins)
        ]
    def _isBaseLevel(self) -> bool:
        return self.ast_history[-2]["type"] == "line"
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
            for k, v in result["map"].items():
                if isinstance(v, dict) and v.get("type"):
                    self.current_ast = v
                    result["map"][k] = self.interpret()
        self.ast_history.pop()
        return result
    def interpretScript(self) -> None:
        for body_item in self.current_ast["body"]:
            self.current_ast = body_item
            self.interpret()
    def interpretLine(self) -> None:
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
            self.interpret()
    def interpretCall(self) -> dict:
        call = self.current_ast
        self.current_call = call
        self.current_ast = self.current_ast["target"]
        target = self.interpret()
        self.current_call_target = target
        self.current_ast = call["args"]
        args: dict = self.interpret()
        self.current_call = None
        self.current_call_target = None
        if target["map"].get("call") and (target["map"]["call"]["type"] == "data"):
            signature = inspect.signature(target["map"]["call"]["source"])
            provided_arguments: int = len(call["args"]["map"])
            expected_arguments: int = target["map"]["call"]["source"].__code__.co_argcount - 2
            required_arguments: int = sum(
                p.default is inspect.Parameter.empty
                for p in signature.parameters.values()
            ) - 2
            for k, v in args["map"].items():
                if v is None:
                    continue
                if isinstance(v, dict):
                    self.current_ast = v
                try:
                    parameter = signature.parameters[k]
                except KeyError:
                    self.eh.throw("noMatchingParameter", f"'{target['name']}' does not have a parameter matching '{k}'")

                annotation = parameter.annotation
                if annotation is inspect.Parameter.empty:
                    exp_types: list[str] = ["any"]
                elif isinstance(annotation, str):
                    exp_types = [t.strip() for t in annotation.split("|")]
                else:
                    exp_types = [str(annotation)]

                if ("idarray" in exp_types) and ("array" not in exp_types):
                    exp_types.append("array")

                if isinstance(v, dict):
                    value_type: str = v.get("type", "map")
                elif isinstance(v, bool):
                    value_type = "boolean"
                elif isinstance(v, int):
                    value_type = "integer"
                elif isinstance(v, float):
                    value_type = "float"
                elif isinstance(v, str):
                    value_type = "string"
                elif isinstance(v, list):
                    value_type = "array"
                elif v is None:
                    value_type = "null"
                else:
                    value_type = type(v).__name__

                if value_type not in exp_types and "any" not in exp_types:
                    self.eh.throw("typeError", f"parameter '{k}' expects one of these types: [{' '.join(exp_types)}], not {value_type}.")
            if provided_arguments > expected_arguments:
                self.eh.throw("tooManyArguments", f"too many arguments provided to {target['name']}. ({provided_arguments} prov. vs max of {expected_arguments} expected)")
            if provided_arguments < required_arguments:
                self.eh.throw("tooFewArguments", f"too few arguments provided to {target['name']}. ({provided_arguments} prov. vs min of {required_arguments} required)")
            return_value: dict | None = target["map"]["call"]["source"](self, target, **args["map"])
            return {"type": "null", "map": {}, "span": call["span"]} if return_value is None else return_value
        else:
            self.eh.throw("notCallable", f"object of type '{target['type']}' is not callable.")
    def interpretIdentifier(self) -> dict:
        if self.current_call_target and self.current_call and self.current_call.get("current_interp_arg") is not None:
            try:
                parameter = inspect.signature(self.current_call_target["map"]["call"]["source"]).parameters[self.current_call["current_interp_arg"]]
                accepted_types = [item.strip() for item in parameter.annotation.split("|")]
                if "identifier" in accepted_types or "idarray" in accepted_types:
                    return self.current_ast
            except KeyError:
                self.eh.throw("noMatchingParameter", f"'{self.current_call_target['name']}' does not have a parameter matching '{self.current_call['current_interp_arg']}'")
        dotted_match = self._resolve_dotted_identifier(self.current_ast["value"])
        if dotted_match is not None:
            return dotted_match
        match = self.findVariable(self.current_ast["value"])
        return match
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
        return self.current_ast
    def interpretFloat(self) -> dict:
        return self.current_ast
    def interpretArray(self) -> dict:
        array: dict = self.current_ast
        result: list = []
        preserve_identifiers = False
        if self.current_call_target and self.current_call and self.current_call.get("current_interp_arg") is not None:
            try:
                parameter = inspect.signature(self.current_call_target["map"]["call"]["source"]).parameters[self.current_call["current_interp_arg"]]
                accepted_types = [item.strip() for item in parameter.annotation.split("|")]
                preserve_identifiers = "idarray" in accepted_types
            except KeyError:
                self.eh.throw("noMatchingParameter", f"'{self.current_call_target['name']}' does not have a parameter matching '{self.current_call['current_interp_arg']}'")
        for item in self.current_ast["items"]:
            if preserve_identifiers and item.get("type") == "identifier":
                result.append(item)
                continue
            self.current_ast = item
            result.append(self.interpret())
        array["items"] = result
        return array
    def interpretGroup(self) -> dict:
        group: dict = self.current_ast
        if group.get("value") is None:
            return group
        self.current_ast = group["value"]
        evaluated = self.interpret()
        group["value"] = evaluated
        return evaluated
    def interpretBlock(self) -> dict:
        # Blocks are first-class values and are executed by control-flow builtins.
        return self.current_ast
    def interpretData(self) -> dict:
        return self.current_ast
    def interpretNull(self) -> dict:
        return self.current_ast