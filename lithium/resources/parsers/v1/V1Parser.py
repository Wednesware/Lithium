from ww.mg.lists import listnav
from ww.mg.groups import group

class V1Parser:
    def __init__(self, lithium, content: str):
        self.lithium = lithium
        self.log = lithium.script.log

        self.content = content
        self.pos = 0
        self.char = ""

        self.ast = {
            "label": "script",
            "members": [
                {
                    "label": "line",
                    "value": 1,
                    "members": []
                }
            ]
        }

        self.layers = [self.ast, self.ast["members"][0]]
        
    def parse(self):
        while self.pos < len(self.content):
            self.char = self.content[self.pos]

            getattr(self, f"parse_{self.layers[-1]['label']}", self.parse_line)()

            self.pos += 1

        return self.ast
    
    def parse_line(self):
        current = self.layers[-1]

        if self.char == "\n":
            self.layers.pop()
            new_line = {
                "label": "line",
                "value": current["value"] + 1,
                "members": []
            }
            self.layers[-2]["members"].append(new_line)
            self.layers.append(new_line)

        if self.char.isspace():
            return

        if self.char in "\"'":
            node = {
                "label": "string",
                "quote": self.char,
                "value": ""
            }

            current["members"].append(node)
            self.layers.append(node)
            return

        if self.char.isalpha() or self.char == "_":
            node = {
                "label": "identifier",
                "value": self.char
            }

            current["members"].append(node)
            self.layers.append(node)
            return
        
    def parse_identifier(self):
        node = self.layers[-1]

        if self.char.isalnum() or self.char == "_":
            node["value"] += self.char
        elif self.char.isspace():
            self.layers[-1]["label"] = "call"
        elif self.char == ":" and self.content[self.pos + 1] == ":":
            self.layers[-1]["label"] = "argument"
            self.pos += 1
        elif self.char == "*":
            self.layers[-1]["label"] = "mappedcall"
        else:
            self.layers.pop()
            self.pos -= 1
            
    def parse_string(self):
        node = self.layers[-1]

        if self.char == "\\":
            node.setdefault("escape", True)
            return

        if node.get("escape"):
            node["value"] += self.char
            node["escape"] = False
            return

        if self.char == node["quote"]:
            node.pop("quote")
            self.layers.pop()
            return

        node["value"] += self.char