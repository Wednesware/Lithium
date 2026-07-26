import os

from sys import argv


def _node_from_python_value(value) -> dict:
    if isinstance(value, dict) and value.get("type"):
        return value
    if isinstance(value, bool):
        return {"type": "boolean", "value": value, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "usedalias": str(value).lower(), "truthiness": lambda x: bool(x["value"])}
    if isinstance(value, int):
        return {"type": "integer", "value": value, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "truthiness": lambda x: bool(x["value"])}
    if isinstance(value, float):
        return {"type": "float", "value": value, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "truthiness": lambda x: bool(x["value"])}
    if isinstance(value, str):
        return {"type": "string", "value": value, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}, "truthiness": lambda x: bool(x["value"])}
    if value is None:
        return {"type": "null", "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}}
    if isinstance(value, (list, tuple)):
        return {
            "type": "array",
            "items": [_node_from_python_value(item) for item in value],
            "map": {},
            "span": {"line": 0, "column": 0, "end_column": 0},
        }
    return {"type": "data", "source": value, "map": {}, "span": {"line": 0, "column": 0, "end_column": 0}}


def runpk(perkeo, path: str | None = None, override_perkeo: str | None = None, initial_vars: dict | None = None) -> dict:
    perkeo = override_perkeo or perkeo
    if path is None:
        if len(argv) < 2:
            raise SystemExit("Usage: pko <file.pk>")
        path = argv[1]

    perkeo.file_path = os.path.abspath(path)

    if not os.path.exists(perkeo.file_path):
        raise SystemExit("File not found.")

    with open(perkeo.file_path) as file:
        perkeo.source = file.read()

    parser = perkeo.res.Parser(perkeo, perkeo.source)
    perkeo.full_ast = parser.parse()

    #if "--ast" in argv:
    #    from json import dumps
    #    print(dumps(perkeo.full_ast, indent="| ", default=str))
    #    return

    interpreter = perkeo.res.Interpreter(perkeo)
    if initial_vars:
        interpreter.scopes[0].vars.update({key: _node_from_python_value(value) for key, value in initial_vars.items()})
    interpreter.runCode()
    return {
        "perkeo": perkeo,
        "parser": parser,
        "interpreter": interpreter,
    }