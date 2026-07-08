from sys import argv

def runpk(lithium) -> None:
    if len(argv) < 2:
        raise SystemExit("Usage: python -m lithium <file.pk> [--ast]")

    with open(argv[1]) as file:
        content: str = file.read()

    parser = lithium.res.Parser(lithium, content)
    ast = parser.parse()

    if "--ast" in argv:
        from json import dumps
        print(dumps(ast, indent="| "))
        return

    interpreter = lithium.res.Interpreter(lithium, ast)
    interpreter.run_code()