class V1Interpreter:
    def __init__(self, parser) -> None:
        self.parser = parser
        self.lithium = parser.lithium
        self.ast = parser.ast
        self.log = parser.lithium.script.log

    def run_code(self) -> None:
        for line in self.ast["members"]:
            for node in line["members"]:
                if node["label"] == "string":
                    self.log(node["value"])