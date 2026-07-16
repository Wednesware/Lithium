import os, sys

from ww.mg.color import Color


class ErrorHandler:
    def __init__(self, interpreter = None) -> None:
        self.interpreter = interpreter
    def throwNoTraceback(self, name: str, message: str, warning: bool = False) -> None:
        print(f"* {Color.tomato}{os.path.basename(self.interpreter.perkeo.file_path)}: {name}{Color.reset}")
        print(":")
        print(f"* {Color.tomato}{message.replace('\n', '\n  ')}{Color.reset}")
        if not warning:
            sys.exit(1)
    def getParts(self, span: dict) -> tuple[str, str, str]:
        line: str = ""
        if len(self.interpreter.perkeo.source.splitlines()):
            lines: str = self.interpreter.perkeo.source.splitlines()[span['line'] - 1]
        return (
            f"{line[0:span['column'] - 1]}",
            f"{line[span['column'] - 1:span['end_column'] - 1]}",
            f"{line[span['end_column'] - 1:len(line)]}"
        )
    def throw(self, name: str, message: str, warning: bool = False) -> None:
        print(f"* {Color.tomato}{os.path.basename(self.interpreter.perkeo.file_path)}: {name} at line {self.interpreter.current_ast['span']['line']}, col {self.interpreter.current_ast['span']['column']}{Color.reset}")
        print(":")
        print(f"* {Color.tomato}{message.replace('\n', '\n  ')}{Color.reset}")
        parts: tuple[str, str, str] = self.getParts(self.interpreter.current_ast["span"])
        print()
        print(f"    {parts[0]}{Color.tomato}{parts[1]}{Color.reset}{parts[2]}")
        print(f"    {Color.gray}{'-' * len(parts[0])}{Color.reset}{Color.tomato}{'~' * len(parts[1])}{Color.reset}{Color.gray}{'-' * len(parts[2])}{Color.reset}")
        if not warning:
            sys.exit(1)
    def throwWithSpan(self, name: str, message: str, span: dict, warning: bool = False) -> None:
        print(f"* {Color.tomato}{os.path.basename(self.interpreter.perkeo.file_path)}: {name} at line {span['line']}, col {span['column']}{Color.reset}")
        print(":")
        print(f"* {Color.tomato}{message.replace('\n', '\n  ')}{Color.reset}")
        parts: tuple[str, str, str] = self.getParts(span)
        print()
        print(f"    {parts[0]}{Color.tomato}{parts[1]}{Color.reset}{parts[2]}")
        print(f"    {Color.gray}{'-' * len(parts[0])}{Color.reset}{Color.tomato}{'~' * len(parts[1])}{Color.reset}{Color.gray}{'-' * len(parts[2])}{Color.reset}")
        if not warning:
            sys.exit(1)