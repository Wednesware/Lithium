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
    def print(interpreter, target, value) -> None:
        print(interpreter.stringifier.stringify(value))