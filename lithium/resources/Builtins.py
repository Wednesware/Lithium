class Builtins:
    @staticmethod
    def getASTOf(interpreter, name: str) -> dict:
        return {
            name: {
                "type": "function",
                "name": name,
                "map": {
                    "call": {
                        "type": "data",
                        "source": getattr(Builtins, name),
                        "span": interpreter.lithium.res.Token.emptySpan()
                    }
                }
            }
        }
    @staticmethod
    def integerCall(interpreter, target, value: "integer|float") -> None: # type: ignore
        print(value["items"])
    @staticmethod
    def print(interpreter, target, value: "any", to: "identifier" = None) -> None: # type: ignore
        print(interpreter.stringifier.stringify(value))