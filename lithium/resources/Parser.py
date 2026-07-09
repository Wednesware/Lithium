from __future__ import annotations

type Token = any

class Parser:
    VALUE_STARTERS = {
        "IDENTIFIER",
        "INTEGER",
        "FLOAT",
        "STRING",
        "LPAREN",
        "LBRACE",
        "LBRACKET",
    }

    LINE_ENDERS = {"NEWLINE", "SEMICOLON", "EOF"}

    def __init__(
        self,
        lithium: any = None,
        content: str | list[Token] = "",
        preserve_comments: bool = True,
    ):
        self.lithium = lithium
        self.content = ""
        self._tokens: list[Token] = []
        if self._is_token_list(content):
            self._tokens = list(content)
        else:
            self.content = "" if content is None else str(content)
        self.preserve_comments = preserve_comments
        self.index = 0
        self.last_tokens: list[Token] = self._tokens
        self.last_ast: dict[str, any] | None = None

    def parse(self) -> dict[str, any]:
        self._ensure_tokens()
        self.index = 0
        self._log("Parsing AST")
        self.last_ast = self.parse_script()
        self._log("Parsed AST")
        return self.last_ast

    def tokens(self) -> list[Token]:
        if not self._tokens or self.content:
            self._log("Lexing source")
            self._tokens = self.lithium.res.Lexer(self.lithium, self.content).tokenize()
            self.last_tokens = self._tokens
            self._log(f"Lexed {len(self._tokens)} tokens")
        return self._tokens

    def __call__(self) -> dict[str, any]:
        return self.parse()

    def _ensure_tokens(self) -> None:
        if self._tokens:
            self.last_tokens = self._tokens
            return
        self.tokens()

    def _log(self, message: str) -> None:
        logger = getattr(self.lithium, "logger", None)
        if logger is not None and hasattr(logger, "debug"):
            logger.debug(message)
            return
        log = getattr(self.lithium, "log", None)
        if callable(log):
            log(message)

    def _is_token_list(self, value: any) -> bool:
        return isinstance(value, list) and (
            not value or all(hasattr(token, "type") and hasattr(token, "span") for token in value)
        )

    def parse_script(self) -> dict[str, any]:
        self._ensure_tokens()
        start = self._peek()
        body: list[dict[str, any]] = []

        while not self._check("EOF"):
            if self._match("NEWLINE", "SEMICOLON"):
                continue
            if self._check("COMMENT"):
                comment = self._comment()
                if comment is not None:
                    body.append(comment)
                continue
            body.append(self.parse_line(stop={"EOF"}))
            self._consume_line_enders()

        end = self._peek()
        return self._node("script", self._span_between(start, end), body=body)

    def parse_line(self, stop: set[str] | None = None) -> dict[str, any]:
        stop = set(stop or ()) | self.LINE_ENDERS
        start = self._peek()

        if self._looks_like_kwarg():
            value = self._parse_argument_map(stop)
        else:
            value = self.parse_expression(stop=stop, allow_implicit_call=True)

        return self._node("line", self._span_from_nodes(start, value), value=value)

    def parse_expression(
        self,
        stop: set[str] | None = None,
        allow_implicit_call: bool = False,
    ) -> dict[str, any]:
        stop = set(stop or ())
        value = self._parse_operator_call(stop)

        if (
            allow_implicit_call
            and self._can_be_implicit_callee(value)
            and self._starts_argument(stop)
        ):
            args = self._parse_argument_map(stop)
            value = self._call(value, args)

        return value

    def _parse_operator_call(self, stop: set[str]) -> dict[str, any]:
        target = self._parse_postfix(stop)
        items: list[dict[str, any]] = []
        first_operator: Token | None = None

        while not self._at_stop(stop) and self._check("OPERATOR"):
            operator_token = self._advance()
            first_operator = first_operator or operator_token
            items.append(
                self._node(
                    "operator",
                    operator_token.span,
                    value=operator_token.value,
                    text=operator_token.text,
                )
            )
            if self._at_stop(stop) or not self._starts_value():
                raise self.lithium.res.errors.LithiumSyntaxError(
                    f"Expected value after operator {operator_token.text!r}",
                    operator_token.span,
                )
            items.append(self._parse_postfix(stop))

        if not items:
            return target

        args_span = self._span_from_node_list(first_operator, items[-1])
        args = self._new_map(args_span)
        args["value"] = self._node("array", args_span, items=items)
        return self._call(target, args)

    def _parse_postfix(self, stop: set[str]) -> dict[str, any]:
        value = self._parse_primary(stop)

        while not self._at_stop(stop) and self._check("LPAREN"):
            open_token = self._advance()
            args = self._parse_argument_map(stop={"RPAREN"})
            close_token = self._consume("RPAREN", "Expected ')' after call arguments")
            args["span"] = self._span_between(open_token, close_token)
            value = self._call(value, args, close_token)

        return value

    def _parse_primary(self, stop: set[str]) -> dict[str, any]:
        token = self._peek()

        if token.type in stop:
            raise self.lithium.res.errors.LithiumSyntaxError("Expected value", token.span)

        if self._match("INTEGER"):
            return self._node("integer", token.span, value=token.value)
        if self._match("FLOAT"):
            return self._node("float", token.span, value=token.value)
        if self._match("STRING"):
            return self._node("string", token.span, value=token.value, text=token.text)
        if self._match("IDENTIFIER"):
            return self._node("identifier", token.span, value=token.value)
        if self._check("LPAREN"):
            return self._parse_group()
        if self._check("LBRACKET"):
            return self._parse_array()
        if self._check("LBRACE"):
            return self._parse_map()
        if self._check("COMMENT"):
            comment = self._comment()
            if comment is not None:
                return comment

        raise self.lithium.res.errors.LithiumSyntaxError(f"Expected value, got {token.type}", token.span)

    def _parse_group(self) -> dict[str, any]:
        open_token = self._consume("LPAREN", "Expected '('")
        self._consume_inline_separators()
        if self._check("RPAREN"):
            close_token = self._advance()
            return self._node("group", self._span_between(open_token, close_token), value=None)
        value = self.parse_expression(
            stop={"RPAREN", "EOF"},
            allow_implicit_call=True,
        )
        self._consume_inline_separators()
        close_token = self._consume("RPAREN", "Expected ')' after group")
        return self._node("group", self._span_between(open_token, close_token), value=value)

    def _parse_array(self) -> dict[str, any]:
        open_token = self._consume("LBRACKET", "Expected '['")
        items: list[dict[str, any]] = []

        while not self._check("RBRACKET", "EOF"):
            if self._match("NEWLINE", "SEMICOLON"):
                continue
            if self._check("COMMENT"):
                comment = self._comment()
                if comment is not None:
                    items.append(comment)
                continue
            items.append(
                self.parse_expression(
                    stop={"NEWLINE", "SEMICOLON", "RBRACKET", "EOF"},
                    allow_implicit_call=True,
                )
            )

        close_token = self._consume("RBRACKET", "Expected ']' after array")
        return self._node("array", self._span_between(open_token, close_token), items=items)

    def _parse_map(self) -> dict[str, any]:
        open_token = self._consume("LBRACE", "Expected '{'")
        result = self._new_map(open_token.span)

        while not self._check("RBRACE", "EOF"):
            if self._match("NEWLINE", "SEMICOLON"):
                continue
            if self._check("COMMENT"):
                self._add_comment(result, self._comment())
                continue
            if self._looks_like_kwarg():
                self._parse_kwarg_into(result, stop={"NEWLINE", "SEMICOLON", "RBRACE", "EOF"})
                continue
            if self._check("ARROW"):
                self._add_positional(result, self._parse_arrow_block())
                continue

            value = self.parse_expression(
                stop={"NEWLINE", "SEMICOLON", "RBRACE", "EOF"},
                allow_implicit_call=True,
            )
            self._add_positional(result, value)

        close_token = self._consume("RBRACE", "Expected '}' after map")
        result["span"] = self._span_between(open_token, close_token)
        return result

    def _parse_argument_map(self, stop: set[str]) -> dict[str, any]:
        start = self._peek()
        result = self._new_map(start.span)

        while not self._at_stop(stop):
            if self._match("NEWLINE", "SEMICOLON"):
                if "NEWLINE" in stop or "SEMICOLON" in stop:
                    self.index -= 1
                    break
                continue
            if self._check("COMMENT"):
                self._add_comment(result, self._comment())
                continue
            if self._looks_like_kwarg():
                self._parse_kwarg_into(result, stop=stop)
                continue
            if self._check("ARROW"):
                self._add_positional(result, self._parse_arrow_block())
                continue
            if not self._starts_value():
                break

            value = self.parse_expression(stop=stop | {"ARROW"}, allow_implicit_call=True)
            self._add_positional(result, value)

        if not result["map"] and not result.get("comments"):
            result["span"] = start.span
        else:
            last = self._previous()
            result["span"] = self._span_between(start, last)
        return result

    def _parse_kwarg_into(self, result: dict[str, any], stop: set[str]) -> None:
        key_token = self._advance()
        self._consume("DOUBLE_COLON", "Expected '::' after map key")
        if self._at_stop(stop) or not self._starts_value():
            raise self.lithium.res.errors.LithiumSyntaxError("Expected value after '::'", self._peek().span)
        value = self.parse_expression(stop=stop, allow_implicit_call=True)
        self._add_map_item(result, str(key_token.value), value)

    def _parse_arrow_block(self) -> dict[str, any]:
        arrow = self._consume("ARROW", "Expected '->'")

        if self._check("LBRACE"):
            self._advance()
            body: list[dict[str, any]] = []

            while not self._check("RBRACE", "EOF"):
                if self._match("NEWLINE", "SEMICOLON"):
                    continue
                if self._check("COMMENT"):
                    comment = self._comment()
                    if comment is not None:
                        body.append(comment)
                    continue
                body.append(self.parse_line(stop={"RBRACE", "EOF"}))
                self._consume_line_enders()

            close_token = self._consume("RBRACE", "Expected '}' after block")
            return self._node("block", self._span_between(arrow, close_token), body=body)

        while self._match("NEWLINE"):
            pass

        if self._check("COMMENT"):
            comment = self._comment()
            body = [] if comment is None else [comment]
            return self._node(
                "block",
                self._span_from_node_list(arrow, body[-1] if body else arrow),
                body=body,
            )

        line = self.parse_line(stop={"NEWLINE", "SEMICOLON", "EOF", "RBRACE"})
        return self._node("block", self._span_from_node_list(arrow, line), body=[line])

    def _call(
        self,
        target: dict[str, any],
        args: dict[str, any],
        end_token: Token | None = None,
    ) -> dict[str, any]:
        span_end = end_token if end_token is not None else args
        return self._node(
            "call",
            self._span_from_node_list(target, span_end),
            target=target,
            args=args,
        )

    def _new_map(self, span: dict[str, int]) -> dict[str, any]:
        result: dict[str, any] = {
            "type": "map",
            "map": {},
            "span": dict(span),
        }
        if self.preserve_comments:
            result["comments"] = []
        return result

    def _add_positional(self, result: dict[str, any], value: dict[str, any]) -> None:
        if "value" not in result["map"]:
            result["map"]["value"] = value
        elif result["map"]["value"]["type"] == "array":
            result["map"]["value"]["items"].append(value)
            result["map"]["value"]["span"] = self._merge_spans(result["value"]["span"], value["span"])
        else:
            result["map"]["value"] = self._node(
                "array",
                self._merge_spans(result["map"]["value"]["span"], value["span"]),
                items=[result["map"]["value"], value],
            )
        result["span"] = self._merge_spans(result["span"], value["span"])

    def _add_map_item(self, result: dict[str, any], key: str, value: dict[str, any]) -> None:
        map = result["map"]
        if key not in map:
            map[key] = value
        elif map[key]["type"] == "array":
            map[key]["items"].append(value)
            map[key]["span"] = self._merge_spans(map[key]["span"], value["span"])
        else:
            map[key] = self._node(
                "array",
                self._merge_spans(map[key]["span"], value["span"]),
                items=[map[key], value],
            )
        result["span"] = self._merge_spans(result["span"], value["span"])

    def _add_comment(self, result: dict[str, any], comment: dict[str, any] | None) -> None:
        if comment is None:
            return
        result.setdefault("comments", []).append(comment)
        result["span"] = self._merge_spans(result["span"], comment["span"])

    def _comment(self) -> dict[str, any] | None:
        token = self._consume("COMMENT", "Expected comment")
        if not self.preserve_comments:
            return None
        return self._node(
            "comment",
            token.span,
            value=token.value["value"],
            style=token.value["style"],
            text=token.text,
        )

    def _looks_like_kwarg(self) -> bool:
        return self._peek().type in {"IDENTIFIER", "STRING", "INTEGER", "FLOAT"} and self._peek(1).type == "DOUBLE_COLON"

    def _starts_value(self) -> bool:
        return self._peek().type in self.VALUE_STARTERS or self._check("COMMENT")

    def _starts_argument(self, stop: set[str]) -> bool:
        if self._at_stop(stop):
            return False
        return self._starts_value() or self._looks_like_kwarg() or self._check("ARROW")

    def _can_be_implicit_callee(self, value: dict[str, any]) -> bool:
        return value["type"] == "identifier"

    def _consume_inline_separators(self) -> None:
        while self._match("NEWLINE", "SEMICOLON"):
            pass

    def _consume_line_enders(self) -> None:
        while self._match("NEWLINE", "SEMICOLON"):
            pass

    def _at_stop(self, stop: set[str]) -> bool:
        return self._peek().type in stop or self._check("EOF")

    def _match(self, *types: str) -> bool:
        if self._check(*types):
            self._advance()
            return True
        return False

    def _check(self, *types: str) -> bool:
        return self._peek().type in types

    def _consume(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise self.lithium.res.errors.LithiumSyntaxError(message, self._peek().span)

    def _advance(self) -> Token:
        token = self._peek()
        if not self._check("EOF"):
            self.index += 1
        return token

    def _peek(self, offset: int = 0) -> Token:
        position = min(self.index + offset, len(self._tokens) - 1)
        return self._tokens[position]

    def _previous(self) -> Token:
        return self._tokens[max(0, self.index - 1)]

    def _node(self, node_type: str, span: dict[str, int], **fields: any) -> dict[str, any]:
        return {"type": node_type, **fields, "map": {}, "span": dict(span)}

    def _span_between(
        self,
        start: Token | dict[str, any],
        end: Token | dict[str, any],
    ) -> dict[str, int]:
        start_span = start["span"] if isinstance(start, dict) else start.span
        end_span = end["span"] if isinstance(end, dict) else end.span
        return {
            "start": start_span["start"],
            "end": end_span["end"],
            "line": start_span["line"],
            "column": start_span["column"],
            "end_line": end_span["end_line"],
            "end_column": end_span["end_column"],
        }

    def _span_from_nodes(
        self,
        start: Token | dict[str, any],
        end: Token | dict[str, any],
    ) -> dict[str, int]:
        return self._span_between(start, end)

    def _span_from_node_list(
        self,
        start: Token | dict[str, any],
        end: Token | dict[str, any],
    ) -> dict[str, int]:
        return self._span_between(start, end)

    def _merge_spans(self, first: dict[str, int], second: dict[str, int]) -> dict[str, int]:
        return {
            "start": min(first["start"], second["start"]),
            "end": max(first["end"], second["end"]),
            "line": first["line"] if first["start"] <= second["start"] else second["line"],
            "column": first["column"] if first["start"] <= second["start"] else second["column"],
            "end_line": first["end_line"] if first["end"] >= second["end"] else second["end_line"],
            "end_column": first["end_column"] if first["end"] >= second["end"] else second["end_column"],
        }

def parse_lithium(
    content: str,
    preserve_comments: bool = True,
    lithium: any = None,
) -> dict[str, any]:
    return Parser(lithium, content, preserve_comments=preserve_comments).parse()
