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
    def interpret(self) -> dict | None:
        self.ast_history.append(self.current_ast)
        if self.perkeo.getsetting("verbose"):
            print(f"{os.path.basename(self.perkeo.file_path)}: now interpreting: {self.current_ast['type']} at {self.current_ast.get('span', '(unknown)')}")
        try:
            interpret_function: callable = getattr(self, f"interpret{self.current_ast['type'].capitalize()}")
        except AttributeError:
            self.eh.throw("invalidToken", f"interpreter does not recognize ast token {self.current_ast['type']!r}")
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
        self.current_ast = self.current_ast["value"]
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
            provided_arguments: int = len(call["args"]["map"])
            expected_arguments: int = target["map"]["call"]["source"].__code__.co_argcount - 2
            required_arguments: int = sum(
                p.default is inspect.Parameter.empty
                for p in inspect.signature(target["map"]["call"]["source"]).parameters.values()
            ) - 2
            for k, v in args["map"].items():
                if v is None:
                    continue
                self.current_ast = v
                exp_types: list[str] = [t.strip() for t in inspect.signature(target["map"]["call"]["source"]).parameters[k].annotation.split("|")]
                if v["type"] not in exp_types and "any" not in exp_types:
                    self.eh.throw("typeError", f"parameter '{k}' expects one of these types: [{' '.join(exp_types)}], not {v['type']}.")
            if provided_arguments > expected_arguments:
                self.eh.throw("tooManyArguments", f"too many arguments provided to {target['fnname']}. ({provided_arguments} prov. vs max of {expected_arguments} expected)")
            if provided_arguments < required_arguments:
                self.eh.throw("tooFewArguments", f"too few arguments provided to {target['fnname']}. ({provided_arguments} prov. vs min of {required_arguments} required)")
            return_value: dict | None = target["map"]["call"]["source"](self, target, **args["map"])
            return {"type": "null", "map": {}, "span": call["span"]} if return_value is None else return_value
        else:
            self.eh.throw("notCallable", f"object of type '{target['type']}' is not callable.")
    def interpretIdentifier(self) -> dict:
        if self.current_call_target and self.current_call and self.current_call.get("current_interp_arg") is not None:
            try:
                parameter = inspect.signature(self.current_call_target["map"]["call"]["source"]).parameters[self.current_call["current_interp_arg"]]
                accepted_types = [item.strip() for item in parameter.annotation.split("|")]
                if "identifier" in accepted_types or "array" in accepted_types:
                    return self.current_ast
            except KeyError:
                self.eh.throw("noMatchingParameter", f"'{self.current_call_target['name']}' does not have a parameter matching '{self.current_call['current_interp_arg']}'")
        return self.findVariable(self.current_ast["value"])
    def interpretMap(self) -> dict:
        map: dict = self.current_ast
        result: dict = {}
        for k, v in map["map"].items():
            if self.current_call:
                self.current_call["current_interp_arg"] = k
            self.current_ast = v
            result[k] = self.interpret()
        map["map"] = result
        if len(self.ast_history) == 3:
            if "value" in map["map"]:
                if len(map["map"]) > 1:
                    self.eh.throw("illegalSyntax", "this syntax is not valid.")
                if map["map"]["value"].get("type") == "string":
                    for output in self.outputs:
                        if output == "terminal":
                            print(map["map"]["value"]["value"])
                        else:
                            if os.path.exists(output):
                                with open(output, "a") as file:
                                    file.write(f"\n{map['value']['value']}")
            elif map["map"]:
                for k, v in map["map"].items():
                    self.scopes[-1].set(k, v)
        return map
    def interpretString(self) -> dict:
        return self.current_ast
    def interpretInteger(self) -> dict:
        self.current_ast["fnname"] = "integerCall"
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
        for item in self.current_ast["items"]:
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
    def interpretData(self) -> dict:
        return self.current_ast
    def interpretNull(self) -> dict:
        return self.current_ast