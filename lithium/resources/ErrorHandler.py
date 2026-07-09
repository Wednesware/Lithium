import os, sys

from ww.mg.color import Color


class ErrorHandler:
    def __init__(self, interpreter = None) -> None:
        self.interpreter = interpreter
    def throwNoTraceback(self, name: str, message: str, warning: bool = False) -> None:
        print(f"* {Color.tomato}{os.path.basename(self.interpreter.lithium.file_path)}: {name}{Color.reset}")
        print(":")
        print(f"* {Color.tomato}{message.replace('\n', '\n  ')}{Color.reset}")
        if not warning:
            sys.exit(1)
    def throw(self, name: str, message: str, warning: bool = False) -> None:
        print(f"* {Color.tomato}{os.path.basename(self.interpreter.lithium.file_path)}: {name} at line {self.interpreter.current_ast['span']['line']}, col {self.interpreter.current_ast['span']['column']}{Color.reset}")
        print(":")
        print(f"* {Color.tomato}{message.replace('\n', '\n  ')}{Color.reset}")
        parts: tuple[str, str, str] = (
            f"{self.interpreter.lithium.source.splitlines()[self.interpreter.current_ast['span']['line'] - 1][0:self.interpreter.current_ast['span']['column'] - 1]}",
              f"{self.interpreter.lithium.source.splitlines()[self.interpreter.current_ast['span']['line'] - 1][self.interpreter.current_ast['span']['column'] - 1:self.interpreter.current_ast['span']['end_column'] - 1]}",
              f"{self.interpreter.lithium.source.splitlines()[self.interpreter.current_ast['span']['line'] - 1][self.interpreter.current_ast['span']['end_column']:len(self.interpreter.lithium.source)]}"
        )
        print()
        print(f"    {parts[0]}{Color.tomato}{parts[1]}{Color.reset}{parts[2]}")
        print(f"    {Color.gray}{'-' * len(parts[0])}{Color.reset}{Color.tomato}{'~' * len(parts[1])}{Color.reset}{Color.gray}{'-' * len(parts[2])}{Color.reset}")
        if not warning:
            sys.exit(1)
    def throwWithSpan(self, name: str, message: str, span: dict, warning: bool = False) -> None:
        print(f"* {Color.tomato}{os.path.basename(self.interpreter.lithium.file_path)}: {name} at line {span['line']}, col {span['column']}{Color.reset}")
        print(":")
        print(f"* {Color.tomato}{message.replace('\n', '\n  ')}{Color.reset}")
        parts: tuple[str, str, str] = (
            f"{self.interpreter.lithium.source.splitlines()[span['line'] - 1][0:span['column'] - 1]}",
              f"{self.interpreter.lithium.source.splitlines()[span['line'] - 1][span['column'] - 1:span['end_column'] - 1]}",
              f"{self.interpreter.lithium.source.splitlines()[span['line'] - 1][span['end_column']:len(self.interpreter.lithium.source)]}"
        )
        print()
        print(f"    {parts[0]}{Color.tomato}{parts[1]}{Color.reset}{parts[2]}")
        print(f"    {Color.gray}{'-' * len(parts[0])}{Color.reset}{Color.tomato}{'~' * len(parts[1])}{Color.reset}{Color.gray}{'-' * len(parts[2])}{Color.reset}")
        if not warning:
            sys.exit(1)