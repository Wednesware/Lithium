# Not functional

from ww.mg.lists import ListNav
from ww.mg.groups import Group

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
            while len(self.layers) > 2:
                self.layers.pop()

            parent = self.layers[-2]
            new_line = {
                "label": "line",
                "value": current["value"] + 1,
                "members": []
            }
            parent["members"].append(new_line)
            self.layers[-1] = new_line
            return

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
        
        if self.char.isdigit():
            node = {
                "label": "integer",
                "value": self.char
            }

            current["members"].append(node)
            self.layers.append(node)
            return

    def parse_identifier(self):
        node = self.layers[-1]

        if self.char.isalnum() or self.char == "_":
            node["value"] += self.char
            return

        if self.char.isspace():
            node["label"] = "call"
            self.layers.pop()
            self.pos -= 1
            return

        if self.char == ":" and self.pos + 1 < len(self.content) and self.content[self.pos + 1] == ":":
            node["label"] = "argument"
            self.layers.pop()
            self.pos += 1
            return

        if self.char == "*":
            node["label"] = "mappedcall"
            self.layers.pop()
            return

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
            node.pop("quote", None)
            self.layers.pop()
            return

        node["value"] += self.char

    def parse_integer(self):
        node = self.layers[-1]

        if self.char.isdigit():
            node["value"] += self.char
            return

        if self.char == "." and "." not in node["value"]:
            node["label"] = "float"
            node["value"] += self.char
            return

        if self.char.isspace() or self.char == "\n":
            node["label"] = "integer"
            self.layers.pop()
            self.pos -= 1
            return

        self.layers.pop()
        self.pos -= 1