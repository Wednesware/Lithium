import base64


class Interpreter:
    def __init__(self, lithium) -> None:
        self.lithium = lithium
        self.current_ast: dict | any | None = None
        self.ast_history: list[dict] = []
        self.log = self.lithium.script.log
        self.eh = self.lithium.res.ErrorHandler(self)
        self.scopes: list = [
            self.lithium.res.Scope(self, "global", {
                "print": {
                    "type": "function",
                    "name": "print",
                    "map": {
                        "call": {
                            "type": "data",
                            "source": self.lithium.res.Builtins.print,
                            "span": {}
                        }
                    }
                }
            })
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
        self.log(f"now interpreting: {self.current_ast['type']} at {self.current_ast['span']}").print()
        self.ast_history.append(self.current_ast)
        try:
            result: dict | None = getattr(self, f"interpret{self.current_ast['type'].capitalize()}")()
            if result.get("map"):
                for k, v in result["map"].items():
                    self.current_ast = v
                    result["map"][k] = self.interpret()
        except AttributeError:
            self.eh.throw("faultyAST", f"interpreter does not recognize ast token {self.current_ast['type']!r}")
        self.ast_history.pop()
    def interpretScript(self) -> None:
        for body_item in self.current_ast["body"]:
            self.current_ast = body_item
            self.interpret()
    def interpretLine(self) -> None:
        self.current_ast = self.current_ast["value"]
        self.interpret()
    def interpretCall(self) -> dict:
        #import pprint; pprint.pprint(self.current_ast)
        call = self.current_ast
        self.current_ast = self.current_ast["target"]
        target = self.interpret()
        self.current_ast = call["args"]
        args: dict = self.interpret()
        if target["map"].get("call") and (target["map"]["call"]["type"] == "data"):
            provided_arguments: int = len(call["args"]["map"])
            expected_arguments: int = target["map"]["call"]["source"].__code__.co_argcount - 1
            if provided_arguments > expected_arguments:
                self.eh.throw("tooManyArguments", f"too many arguments provided to {target['name']}. ({provided_arguments} > {expected_arguments})")
            if provided_arguments < expected_arguments:
                self.eh.throw("tooFewArguments", f"too few arguments provided to {target['name']}. ({provided_arguments} < {expected_arguments})")
            return target["map"]["call"]["source"](target, **args)
        else:
            self.eh.throw("callError", f"'{target['name']}' is not callable.")
    def interpretIdentifier(self) -> dict:
        return self.findVariable(self.current_ast["value"])
    def interpretMap(self) -> dict:
        result: dict = {}
        for k, v in self.current_ast["map"].items():
            self.current_ast = v
            result[k] = self.interpret()
        return result
    def interpretString(self) -> dict:
        return self.current_ast