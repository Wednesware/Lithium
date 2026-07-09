import os

from sys import argv


def runpk(lithium) -> None:
    if len(argv) < 2:
        raise SystemExit("Usage: python -m lithium <file.pk> [--ast]")

    lithium.file_path = os.path.abspath(argv[1])

    if not os.path.exists(lithium.file_path):
        raise SystemExit("File not found.")

    with open(lithium.file_path) as file:
        lithium.source = file.read()

    parser = lithium.res.Parser(lithium, lithium.source)
    lithium.full_ast = parser.parse()

    if "--ast" in argv:
        from json import dumps
        print(dumps(lithium.full_ast, indent="| "))
        return

    interpreter = lithium.res.Interpreter(lithium)
    interpreter.runCode()