from dataclasses import dataclass


@dataclass(frozen=True)
class V2Token:
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