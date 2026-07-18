import os


class Stringifier:
    def __init__(self, interpreter) -> None:
        self.interpreter = interpreter
    def stringify(self, ast: dict, allow_custom_stringification: bool = True) -> str:
        if not isinstance(ast, dict):
            self.interpreter.eh.throw("cannotStringify", "passed invalid ast to stringifier. returning simple string conversion instead of stringifying.", warning=True)
            return str(ast)
        if self.interpreter.perkeo.getsetting("verbose"):
            print(f"{os.path.basename(self.interpreter.perkeo.file_path)}: now stringifying: {ast['type']} at {self.interpreter.current_ast.get('span', '(unknown)')}")
        if allow_custom_stringification and ast.get("stringify"):
            return ast["stringify"](ast)
        try:
            stringify_function: callable = getattr(self, f"stringify{ast['type'].capitalize()}")
        except AttributeError:
            self.interpreter.eh.throw("invalidToken", f"stringifier does not recognize ast token {ast['type']!r}")
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
    def stringifyFunction(self, ast: dict) -> str:
        return f"<function {ast['name']}>"
    def stringifyData(self, ast: dict) -> str:
        return str(ast["source"])
    def stringifyNull(self, ast: dict) -> str:
        return "null"
    def stringifyGroup(self, ast: dict) -> str:
        return self.interpreter.perkeo.source.splitlines()[ast["span"]["line"] - 1][ast["span"]["column"] - 1:ast["span"]["end_column"] - 1]
    @staticmethod
    def _quote(s: str) -> str:
        return f"\"{s}\""