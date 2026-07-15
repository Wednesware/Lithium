import os

from sys import argv


def runpk(perkeo) -> None:
    if len(argv) < 2:
        raise SystemExit("Usage: python -m perkeo <file.pk> [--ast]")

    perkeo.file_path = os.path.abspath(argv[1])

    if not os.path.exists(perkeo.file_path):
        raise SystemExit("File not found.")

    with open(perkeo.file_path) as file:
        perkeo.source = file.read()

    parser = perkeo.res.Parser(perkeo, perkeo.source)
    perkeo.full_ast = parser.parse()

    if "--ast" in argv:
        from json import dumps
        print(dumps(perkeo.full_ast, indent="| "))
        return

    interpreter = perkeo.res.Interpreter(perkeo)
    interpreter.runCode()