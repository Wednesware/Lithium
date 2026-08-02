type Token = any

from decimal import Decimal


class Lexer:
    SIMPLE_TOKENS = {
        "(": "LPAREN",
        ")": "RPAREN",
        "{": "LBRACE",
        "}": "RBRACE",
        "[": "LBRACKET",
        "]": "RBRACKET",
        ",": "COMMA",
        ";": "SEMICOLON",
    }

    OPERATOR_CHARS = set("+-*/%=!<>|&^~?.:@$")

    def __init__(self, perkeo, source: str):
        self.perkeo = perkeo
        self.source = source
        self.length = len(source)
        self.index = 0
        self.line = 1
        self.column = 1
        self.eh = self.perkeo.res.ErrorHandler(self)

    def __iter__(self) -> iter:
        return iter(self.tokenize())

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []

        while not self._at_end():
            char = self._peek()

            if char in " \t\f\v":
                self._advance()
                continue

            if char in "\r\n":
                tokens.append(self._newline())
                continue

            if self._starts_with("//"):
                tokens.append(self._line_comment())
                continue

            if self._starts_with("/*"):
                tokens.append(self._block_comment())
                continue

            if self._starts_with("::"):
                tokens.append(self._fixed("DOUBLE_COLON", "::", "::"))
                continue

            if self._starts_with("->"):
                tokens.append(self._fixed("ARROW", "->", "->"))
                continue

            if char in self.SIMPLE_TOKENS:
                tokens.append(self._fixed(self.SIMPLE_TOKENS[char], char, char))
                continue

            if char in ("'", '"'):
                tokens.append(self._string())
                continue

            if char.isdigit():
                tokens.append(self._number())
                continue

            if self._is_identifier_start(char):
                tokens.append(self._identifier())
                continue

            if char in self.OPERATOR_CHARS:
                tokens.append(self._operator())
                continue

            span = self._current_span()
            self.eh.throwWithSpan("unexpectedCharacter", f"unexpected character {char!r}", span)

        tokens.append(
            self.perkeo.res.Token(
                "EOF",
                None,
                "",
                self.index,
                self.index,
                self.line,
                self.column,
                self.line,
                self.column,
            )
        )
        return tokens

    def _at_end(self) -> bool:
        return self.index >= self.length

    def _peek(self, offset: int = 0) -> str:
        position = self.index + offset
        if position >= self.length:
            return ""
        return self.source[position]

    def _starts_with(self, text: str) -> bool:
        return self.source.startswith(text, self.index)

    def _advance(self) -> str:
        char = self.source[self.index]
        self.index += 1
        if char == "\r":
            if self._peek() == "\n":
                self.index += 1
            self.line += 1
            self.column = 1
            return "\n"
        if char == "\n":
            self.line += 1
            self.column = 1
            return char
        self.column += 1
        return char

    def _mark(self) -> tuple[int, int, int]:
        return self.index, self.line, self.column

    def _token(
        self,
        token_type: str,
        value: any,
        start: int,
        line: int,
        column: int,
    ) -> Token:
        return self.perkeo.res.Token(
            token_type,
            value,
            self.source[start:self.index],
            start,
            self.index,
            line,
            column,
            self.line,
            self.column,
        )

    def _fixed(self, token_type: str, value: any, text: str) -> Token:
        start, line, column = self._mark()
        for _ in text:
            self._advance()
        return self._token(token_type, value, start, line, column)

    def _newline(self) -> Token:
        start, line, column = self._mark()
        self._advance()
        return self.perkeo.res.Token(
            "NEWLINE",
            "\n",
            self.source[start:self.index],
            start,
            self.index,
            line,
            column,
            self.line,
            self.column,
        )

    def _line_comment(self) -> Token:
        start, line, column = self._mark()
        self._advance()
        self._advance()
        value_start = self.index
        while not self._at_end() and self._peek() not in "\r\n":
            self._advance()
        value = self.source[value_start:self.index]
        return self._token("COMMENT", {"style": "line", "value": value}, start, line, column)

    def _block_comment(self) -> Token:
        start, line, column = self._mark()
        self._advance()
        self._advance()
        value_start = self.index

        while not self._at_end() and not self._starts_with("*/"):
            self._advance()

        if self._at_end():
            self.eh.throwWithSpan(
                "unterminatedBlockComment",
                "unterminated block comment",
                {
                    "start": start,
                    "end": self.index,
                    "line": line,
                    "column": column,
                    "end_line": self.line,
                    "end_column": self.column,
                },
            )

        value = self.source[value_start:self.index]
        self._advance()
        self._advance()
        return self._token(
            "COMMENT",
            {"style": "block", "value": value},
            start,
            line,
            column,
        )

    def _string(self) -> Token:
        start, line, column = self._mark()
        quote = self._advance()
        chars: list[str] = []

        escapes = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "\\": "\\",
            '"': '"',
            "'": "'",
        }

        while not self._at_end():
            char = self._advance()
            if char == quote:
                return self._token("STRING", "".join(chars), start, line, column)
            if char == "\\":
                if self._at_end():
                    break
                escaped = self._advance()
                chars.append(escapes.get(escaped, escaped))
                continue
            chars.append(char)

        self.eh.throwWithSpan(
            "illegal syntax",
            "unterminated string",
            {
                "start": start,
                "end": self.index,
                "line": line,
                "column": column,
                "end_line": self.line,
                "end_column": self.column,
            },
        )

    def _number(self) -> Token:
        start, line, column = self._mark()
        while self._peek().isdigit():
            self._advance()

        is_float = False
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self._peek().isdigit():
                self._advance()

        text = self.source[start:self.index]
        if is_float:
            return self._token("FLOAT", Decimal(text), start, line, column)
        return self._token("INTEGER", int(text), start, line, column)

    def _identifier(self) -> Token:
        start, line, column = self._mark()
        self._advance()
        while True:
            next_char = self._peek()
            if self._is_identifier_part(next_char):
                self._advance()
                continue
            if next_char == "." and self._is_identifier_start(self._peek(1)):
                self._advance()
                continue
            break
        return self._token(
            "IDENTIFIER",
            self.source[start:self.index],
            start,
            line,
            column,
        )

    def _operator(self) -> Token:
        start, line, column = self._mark()
        while (
            not self._at_end()
            and self._peek() in self.OPERATOR_CHARS
            and not self._starts_with("::")
            and not self._starts_with("->")
            and self._peek() not in "(){}[];"
        ):
            self._advance()
        return self._token(
            "OPERATOR",
            self.source[start:self.index],
            start,
            line,
            column,
        )

    def _is_identifier_start(self, char: str) -> bool:
        return char == "_" or char.isalpha()

    def _is_identifier_part(self, char: str) -> bool:
        return char == "_" or char.isalnum()

    def _current_span(self) -> dict[str, int]:
        return {
            "start": self.index,
            "end": self.index + 1,
            "line": self.line,
            "column": self.column,
            "end_line": self.line,
            "end_column": self.column + 1,
        }