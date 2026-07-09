class Interpreter:
    def __init__(self, lithium) -> None:
        self.lithium = lithium
        self.current_ast: dict | any | None = None
        self.ast_history: dict | None = None
        self.log = self.lithium.script.log
        self.eh = self.lithium.res.ErrorHandler(self)
        self.scopes: list = [
            self.lithium.res.Scope(self, "global")
        ]
    def runCode(self) -> None:
        self.current_ast = self.lithium.full_ast
        self.interpret()
    def findVariable(self, ident: str) -> any:
        for scope in self.scopes:
            if ident in scope.vars:
                return scope.get(ident)
        self.eh.throw("scopeError", f"identifier '{ident}' is not associated with a value in any scope.")
    def interpret(self) -> any | None:
        self.log(f"now interpreting: {self.current_ast['type']} at {self.current_ast['span']}").print()
        self.ast_history.append(self.current_ast)
        try:
            return getattr(self, f"interpret{self.current_ast['type'].capitalize()}")()
        except AttributeError:
            self.eh.throw("syntaxError", f"interpreter does not recognize ast token {self.current_ast['type']!r}")
        self.ast_history.pop()
    def interpretScript(self) -> None:
        for body_item in self.current_ast["body"]:
            self.current_ast = body_item
            self.interpret()
    def interpretLine(self) -> None:
        self.current_ast = self.current_ast["value"]
        self.interpret()
    def interpretCall(self) -> None:
        self.current_ast = self.current_ast["target"]
        target = self.interpret()
        if target["map"].get("call") and (target["map"]["call"]["type"] == "function"):
            ... # TODO
    def interpretIdentifier(self) -> str | any:
        return self.findVariable(self.current_ast["value"])