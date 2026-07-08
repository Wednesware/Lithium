from json import dumps

from sys import argv

def runpk(lithium) -> None:
    with open(argv[1]) as file:
        content: str = file.read()
    parser = lithium.res.parsers.V2Parser(lithium, content)
    ast = parser.parse()
    print(dumps(ast, indent="| "))
    #interpreter = lithium.res.interpreters.V1Interpreter(parser)
    #interpreter.run_code()