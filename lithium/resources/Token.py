from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    type: str
    value: any
    text: str
    start: int
    end: int
    line: int
    column: int
    end_line: int
    end_column: int

    @property
    def span(self) -> dict[str, int]:
        return {
            "start": self.start,
            "end": self.end,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }
    @staticmethod
    def emptySpan() -> dict[str, int]:
        return {
            "start": 0,
            "end": 0,
            "line": 0,
            "column": 0,
            "end_line": 0,
            "end_column": 0,
        }