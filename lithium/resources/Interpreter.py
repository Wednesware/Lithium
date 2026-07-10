import inspect


class Interpreter:
    def __init__(self, lithium) -> None:
        self.lithium = lithium
        self.current_ast: dict | None = None
        self.current_call: dict | None = None
        self.current_call_target: dict | None = None
        self.ast_history: list[dict] = []
        self.eh = self.lithium.res.ErrorHandler(self)
        self.stringifier = self.lithium.res.Stringifier(self)
        self.scopes: list = [
            self.lithium.res.Scope(self, "global",
                self.lithium.res.Builtins.getASTOf(self, "print")  
            )
        ]
    def runCode(self) -> None:
        self.current_ast = self.lithium.full_ast
        self.interpret()
    def findVariable(self, ident: str) -> any:
        for scope in self.scopes:
            if ident in scope.vars:
                return scope.get(ident)
        self.eh.throw("scopeError", f"identifier '{ident}' is not associated with a value in any scope.")
    def interpret(self) -> dict | None:
        if self.lithium.getsetting("verbose"):
            print(f"now interpreting: {self.current_ast['type']} at {self.current_ast['span']}")
        self.ast_history.append(self.current_ast)
        try:
            interpret_function: callable = getattr(self, f"interpret{self.current_ast['type'].capitalize()}")
        except AttributeError:
            self.eh.throw("outdatedInterpreter", f"interpreter does not recognize ast token {self.current_ast['type']!r}.\nperhaps your interpreter is outdated?")
        result: dict | None = interpret_function()
        if isinstance(result, dict) and result.get("map"):
            for k, v in result["map"].items():
                self.current_ast = v
                print(v)
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
                self.current_ast = v
                exp_types: list[str] = [t.strip() for t in inspect.signature(target["map"]["call"]["source"]).parameters[k].annotation.split("|")]
                if v["type"] not in exp_types and "any" not in exp_types:
                    self.eh.throw("typeError", f"parameter '{k}' expects one of these types: [{' '.join(exp_types)}], not {v['type']}.")
            if provided_arguments > expected_arguments:
                self.eh.throw("tooManyArguments", f"too many arguments provided to {target['name']}. ({provided_arguments} > {expected_arguments})")
            if provided_arguments < required_arguments:
                self.eh.throw("tooFewArguments", f"too few arguments provided to {target['name']}. ({provided_arguments} < {expected_arguments})")
            return target["map"]["call"]["source"](self, target, **args["map"])
        else:
            self.eh.throw("notCallable", f"object of type '{target['type']}' is not callable.")
    def interpretIdentifier(self) -> dict:
        try:
            if self.current_call_target and inspect.signature(self.current_call_target["map"]["call"]["source"]).parameters[self.current_call["current_interp_arg"]].annotation == "identifier":
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
        return map
    def interpretString(self) -> dict:
        return self.current_ast
    def interpretInteger(self) -> dict:
        self.current_ast["map"]["call"] = self.lithium.res.Builtins.getASTOf(self, "integerCall")
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
    def interpretData(self) -> dict:
        return self.current_ast