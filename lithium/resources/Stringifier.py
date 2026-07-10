class Stringifier:
    def __init__(self, interpreter) -> None:
        self.interpreter = interpreter
        self.eh = self.interpreter.lithium.res.ErrorHandler(self.interpreter)
    def stringify(self, ast: dict) -> str:
        if self.interpreter.lithium.getsetting("verbose"):
            print(f"now stringifying: {ast['type']} at {ast['span']}")
        try:
            stringify_function: callable = getattr(self, f"stringify{ast['type'].capitalize()}")
        except AttributeError:
            self.eh.throw("invalidToken", f"stringifier does not recognize ast token {ast['type']!r}")
        return stringify_function(ast)
    def stringifyScript(self, ast: dict) -> str:
        return self.interpreter.lithium.source
    def stringifyLine(self, ast: dict) -> str:
        return self.interpreter.lithium.source.splitlines()[ast["span"]["line"] - 1]
    def stringifyIdentifier(self, ast: dict) -> dict:
        return ast["value"]
    def stringifyMap(self, ast: dict) -> dict:
        result: dict = {}
        for k, v in ast["map"].items():
            result[k] = self.stringify(v)
        return str(result)
    def stringifyString(self, ast: dict) -> dict:
        return ast["value"]
    def stringifyInteger(self, ast: dict) -> dict:
        return ast["value"]
    def stringifyFloat(self, ast: dict) -> dict:
        return ast["value"]
    def stringifyArray(self, ast: dict) -> dict:
        result: list = []
        for item in ast["items"]:
            result.append(self.stringify(item))
        return f"[{' '.join([("\"" + item + "\"" if isinstance(item, str) else str(item)) for item in result])}]"
    def stringifyData(self, ast: dict) -> dict:
        return str(ast["source"])
    def stringifyGroup(self, ast: dict) -> dict:
        return self.interpreter.lithium.source.splitlines()[ast["span"]["line"] - 1][ast["span"]["column"] - 1:ast["span"]["end_column"] - 1]