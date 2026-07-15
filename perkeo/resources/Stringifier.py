from ww.mg.color import Color


class Stringifier:
    def __init__(self, interpreter) -> None:
        self.interpreter = interpreter
        self.eh = self.interpreter.perkeo.res.ErrorHandler(self.interpreter)
    def stringify(self, ast: dict) -> str:
        if not isinstance(ast, dict):
            self.eh.throw("cannotStringify", "passed invalid ast to stringifier. returning simple string conversion instead of stringifying.", warning=True)
            return str(ast)
        if self.interpreter.perkeo.getsetting("verbose"):
            print(f"now stringifying: {ast['type']} at {ast['span']}")
        try:
            stringify_function: callable = getattr(self, f"stringify{ast['type'].capitalize()}")
        except AttributeError:
            self.eh.throw("invalidToken", f"stringifier does not recognize ast token {ast['type']!r}")
        return stringify_function(ast)
    def stringifyScript(self, ast: dict) -> str:
        return self.interpreter.perkeo.source
    def stringifyLine(self, ast: dict) -> str:
        return self.interpreter.perkeo.source.splitlines()[ast["span"]["line"] - 1]
    def stringifyIdentifier(self, ast: dict) -> str:
        return ast["value"]
    def stringifyMap(self, ast: dict) -> str:
        result: dict = {}
        for k, v in ast["map"].items():
            if v["type"] == "string":
                result[k] = Stringifier._quote(v["value"])
            else:
                result[k] = self.stringify(v)
        return f"{{{' '.join([((k + '::' + v) if k != 'value' else v) for k, v in result.items()])}}}"
    def stringifyString(self, ast: dict) -> str:
        return ast["value"]
    def stringifyInteger(self, ast: dict) -> str:
        return str(ast["value"])
    def stringifyFloat(self, ast: dict) -> str:
        return str(ast["value"])
    def stringifyArray(self, ast: dict) -> str:
        result: list = []
        for item in ast["items"]:
            if item["type"] == "string":
                result.append(Stringifier._quote(item["value"]))
            else:
                result.append(self.stringify(item))
        return f"[{' '.join(result)}]"
    def stringifyData(self, ast: dict) -> str:
        return str(ast["source"])
    def stringifyNull(self, ast: dict) -> str:
        return "null"
    def stringifyGroup(self, ast: dict) -> str:
        return self.interpreter.perkeo.source.splitlines()[ast["span"]["line"] - 1][ast["span"]["column"] - 1:ast["span"]["end_column"] - 1]
    @staticmethod
    def _quote(s: str) -> str:
        return f"\"{s}\""