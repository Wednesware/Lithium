from json import dumps

from sys import argv

def compile(lithium) -> None:
    with open(argv[1]) as file:
        content: str = file.read()
    parser = lithium.res.parsers.v1.V1Parser(lithium, content)
    parser.parse()
    print(dumps(parser.ast, indent="| "))