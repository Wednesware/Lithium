class Scope:
    def __init__(self, interpreter, name: str) -> None:
        self.interpreter = interpreter
        self.name: str = name
        self.vars: dict[str, dict] = {}
    def get(self, ident: str) -> dict:
        try:
            return self.vars[ident]
        except KeyError:
            self.interpreter.eh.throw("scopeError", f"identifier '{ident}' is not associated with a value in the '{self.name}' scope.")