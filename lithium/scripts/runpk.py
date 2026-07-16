import os

from sys import argv


def runpk(perkeo, path: str | None = None) -> dict:
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
    interpreter.runCode()
    return {
        "perkeo": perkeo,
        "parser": parser,
        "interpreter": interpreter,
    }