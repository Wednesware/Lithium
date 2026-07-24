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
        "OPERATOR",
    }

    LINE_ENDERS = {"NEWLINE", "SEMICOLON", "EOF"}

    DEFAULT_INFIX_PRIORITIES = {
        "or": 1,
        "and": 1,
        "|": 1,
        "&": 1,
        "=": 2,
        "==": 2,
        "!=": 2,
        ">": 2,
        ">=": 2,
        "<": 2,
        "<=": 2,
        ":": 2,
        "..": 2,
        "..=": 2,
        "+": 3,
        "-": 3,
        "*": 4,
        "/": 4,
        "%": 4,
        "^": 4,
        "%*": 4,
    }

    def __init__(
        self,
        perkeo: any = None,
        content: str | list[Token] = "",
        preserve_comments: bool = True,
    ):
        self.perkeo = perkeo
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
        self.infix_priorities = dict(self.DEFAULT_INFIX_PRIORITIES)
        self._load_runtime_priorities()
        self.eh = self.perkeo.res.ErrorHandler(self)

    def parse(self) -> dict[str, any]:
        try:
            self._ensure_tokens()
            self.index = 0
            self._log("Parsing AST")
            self.last_ast = self.parse_script()
            self._log("Parsed AST")
            return self.last_ast
        except Exception as err:
            self.eh.throwNoTraceback("unknownError", f"{err.__class__.__name__}: {err}", warning=self.perkeo.getsetting("verbose"))
            raise err

    def tokens(self) -> list[Token]:
        if not self._tokens or self.content:
            self._log("Lexing source")
            self._tokens = self.perkeo.res.Lexer(self.perkeo, self.content).tokenize()
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
        logger = getattr(self.perkeo, "logger", None)
        if logger is not None and hasattr(logger, "debug"):
            logger.debug(message)
            return
        log = getattr(self.perkeo, "log", None)
        if callable(log):
            log(message)

    def _is_token_list(self, value: any) -> bool:
        return isinstance(value, list) and (
            not value or all(hasattr(token, "type") and hasattr(token, "span") for token in value)
        )

    def _load_runtime_priorities(self) -> None:
        builtins_cls = getattr(getattr(self.perkeo, "res", None), "Builtins", None)
        if builtins_cls is None:
            return

        operator_priorities = getattr(builtins_cls, "OPERATOR_PRIORITIES", None)
        if isinstance(operator_priorities, dict):
            for symbol, prio in operator_priorities.items():
                if isinstance(prio, int):
                    self.infix_priorities[str(symbol)] = prio

        function_priorities = getattr(builtins_cls, "FUNCTION_PRIORITIES", None)
        if isinstance(function_priorities, dict):
            for symbol, prio in function_priorities.items():
                if isinstance(prio, int):
                    self.infix_priorities[str(symbol)] = prio

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

        while self._check("COMMENT"):
            self._comment()

        if not self._at_stop(stop):
            token = self._peek()
            token_text = token.text if token.text else token.type
            self.eh.throwWithSpan(
                "unexpectedTokenAfterExpression",
                f"unexpected token {token_text!r} after expression",
                token.span,
            )

        return self._node("line", self._span_from_nodes(start, value), value=value)

    def parse_expression(
        self,
        stop: set[str] | None = None,
        allow_implicit_call: bool = False,
    ) -> dict[str, any]:
        stop = set(stop or ())
        value = self._parse_comparison(stop)

        if (
            allow_implicit_call
            and self._can_be_implicit_callee(value)
            and self._starts_argument(stop)
        ):
            args = self._parse_argument_map(stop)
            value = self._call(value, args)

        while not self._at_stop(stop) and self._check("ARROW"):
            block = self._parse_arrow_block()
            if value["type"] == "identifier":
                args = self._new_map(self._span_from_node_list(value, block))
                self._add_positional(args, block)
                value = self._call(value, args)
                continue
            if value["type"] == "call":
                self._add_positional(value["args"], block)
                value["span"] = self._merge_spans(value["span"], block["span"])
                continue
            self.eh.throwWithSpan(
                "expectedCallableBeforeArrow",
                "expected callable value before '->'",
                block["span"],
            )

        return value

    def _parse_comparison(self, stop: set[str]) -> dict[str, any]:
        return self._parse_precedence(stop=stop, min_precedence=0)

    def _is_infix_identifier_call(self) -> bool:
        if not self._check("IDENTIFIER"):
            return False
        if self._peek(1).type == "DOUBLE_COLON":
            return False
        if self._peek(1).type in self.LINE_ENDERS | {"EOF", "RPAREN", "RBRACE", "RBRACKET"}:
            return False
        return self._peek(1).type in self.VALUE_STARTERS or self._peek(1).type == "COMMENT"

    def _parse_additive(self, stop: set[str]) -> dict[str, any]:
        return self._parse_precedence(stop=stop, min_precedence=0)

    def _parse_multiplicative(self, stop: set[str]) -> dict[str, any]:
        return self._parse_precedence(stop=stop, min_precedence=0)

    def _parse_operator_call(self, stop: set[str]) -> dict[str, any]:
        return self._parse_precedence(stop=stop, min_precedence=0)
    
    #def _parse_operator_call(self, _) -> dict[str, any]:
    #    token = self._peek()
    #    return self._node("identifier", token.span, value=token.value)

    def _parse_postfix(self, stop: set[str]) -> dict[str, any]:
        value = self._parse_primary(stop)

        while not self._at_stop(stop):
            if self._check("LPAREN"):
                group = self._parse_group()
                args = self._new_map(group["span"])
                if group["value"] is not None:
                    self._add_positional(args, group["value"])
                value = self._call(value, args, group)
                continue

            if self._is_unit_postfix_call(value):
                unit_token = self._advance()
                args = self._new_map(self._span_from_node_list(value, unit_token))
                self._add_positional(args, value)
                value = self._call(
                    self._node("identifier", unit_token.span, value=unit_token.value),
                    args,
                    end_token=unit_token,
                    unit_syntax=True,
                )
                continue

            break

        return value

    def _parse_precedence(self, stop: set[str], min_precedence: int) -> dict[str, any]:
        target = self._parse_postfix(stop)

        while not self._at_stop(stop):
            candidate = self._peek_infix_candidate(target)
            if candidate is None:
                break

            token, precedence, operator_syntax = candidate
            if precedence < min_precedence:
                break

            operator_token = self._advance()
            if self._at_stop(stop) or not self._starts_value():
                self.eh.throwWithSpan(
                    "noValueAfterOperator",
                    f"expected value after operator {operator_token.text!r}",
                    operator_token.span,
                )

            right = self._parse_precedence(stop=stop, min_precedence=precedence + 1)
            args_span = self._span_from_node_list(target, right)
            args = self._new_map(args_span)
            self._add_positional(args, target)
            self._add_positional(args, right)

            target_node_type = "operator" if operator_syntax else "identifier"
            target = self._call(
                self._node(target_node_type, token.span, value=token.value),
                args,
                operator_syntax=operator_syntax,
            )

        return target

    def _peek_infix_candidate(self, current_target: dict[str, any]) -> tuple[Token, int, bool] | None:
        if self._check("OPERATOR"):
            token = self._peek()
            precedence = self._infix_priority_for_symbol(str(token.value))
            if precedence is None:
                return None
            if not self._starts_value_at_offset(1):
                return None
            return token, precedence, True

        if current_target["type"] != "identifier" and self._is_infix_identifier_call():
            token = self._peek()
            precedence = self._infix_priority_for_symbol(str(token.value), default=0)
            return token, precedence, False

        return None

    def _infix_priority_for_symbol(self, symbol: str, default: int | None = None) -> int | None:
        if symbol in self.infix_priorities:
            return self.infix_priorities[symbol]
        return default

    def _is_unit_postfix_call(self, current_value: dict[str, any]) -> bool:
        if not self._check("IDENTIFIER"):
            return False
        if self._peek(1).type == "DOUBLE_COLON":
            return False
        if self._starts_value_at_offset(1):
            return False
        token = self._peek()
        return current_value["span"]["end"] == token.span["start"]

    def _parse_primary(self, stop: set[str]) -> dict[str, any]:
        token = self._peek()

        if token.type in stop:
            self.eh.throwWithSpan("expectedValue", "expected value", token.span)

        if self._match("INTEGER"):
            return self._node("integer", token.span, value=token.value)
        if self._match("FLOAT"):
            return self._node("float", token.span, value=token.value)
        if self._match("STRING"):
            return self._node("string", token.span, value=token.value, text=token.text)
        if self._check("OPERATOR"):
            token = self._advance()
            return self._node("operator", token.span, value=token.value)
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

        self.eh.throwWithSpan("expectedValue", f"expected value, got {token.type}", token.span)

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

        if not self._check("RPAREN", "EOF"):
            args = self._new_map(value["span"])
            self._add_positional(args, value)

            while not self._check("RPAREN", "EOF"):
                if self._match("NEWLINE", "SEMICOLON"):
                    continue
                if self._check("COMMENT"):
                    comment = self._comment()
                    if comment is not None:
                        self._add_comment(args, comment)
                    continue

                self._add_positional(
                    args,
                    self.parse_expression(
                        stop={"RPAREN", "EOF"},
                        allow_implicit_call=True,
                    ),
                )

            close_token = self._consume("RPAREN", "Expected ')' after group")
            return self._node("group", self._span_between(open_token, close_token), value=self._call(value, args, close_token))

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
                    allow_implicit_call=False,
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
                if self._parse_kwarg_into_trailing_call(result, stop=stop):
                    continue
                self._parse_kwarg_into(result, stop=stop)
                continue
            if self._check("ARROW"):
                self._add_positional(result, self._parse_arrow_block())
                continue
            if not self._starts_value():
                break

            # Keep keyword arguments attached to the current call instead of
            # being absorbed into an implicit nested call.
            # Parenthesized arguments are explicitly grouped, so they may still
            # contain an implicit call like `(stringify 5..=4)`.
            allow_implicit_call = self._check("LPAREN")
            value = self.parse_expression(stop=stop | {"ARROW"}, allow_implicit_call=allow_implicit_call)
            self._add_positional(result, value)

        if not result["map"] and not result.get("comments"):
            result["span"] = start.span
        else:
            last = self._previous()
            result["span"] = self._span_between(start, last)
        return result

    def _parse_kwarg_into_trailing_call(self, result: dict[str, any], stop: set[str]) -> bool:
        positional_items = self._get_positional_items(result)
        # If we already collapsed a trailing implicit call (e.g. `lang.is x type::integer`),
        # keep attaching subsequent keyword arguments to that call.
        if len(positional_items) == 1 and positional_items[0]["type"] == "call":
            trailing_call = positional_items[0]
            trailing_target = trailing_call.get("target", {})
            target_value = str(trailing_target.get("value", ""))
            if trailing_target.get("type") != "identifier" or "." not in target_value:
                return False

            key_token = self._advance()
            self._consume("DOUBLE_COLON", "Expected '::' after map key")
            if self._at_stop(stop) or not self._starts_value():
                self.eh.throwWithSpan("expectedValue", "expected value after '::'", self._peek().span)

            allow_implicit_call = self._check("LPAREN")
            value = self.parse_expression(stop=stop, allow_implicit_call=allow_implicit_call)
            self._add_map_item(trailing_call["args"], str(key_token.value), value)
            trailing_call["span"] = self._merge_spans(trailing_call["span"], value["span"])
            result["span"] = self._merge_spans(result["span"], trailing_call["span"])
            return True

        if len(positional_items) < 2:
            return False

        candidate_index = -1
        for i in range(len(positional_items) - 2, -1, -1):
            if positional_items[i]["type"] != "identifier":
                continue
            identifier_value = str(positional_items[i].get("value", ""))
            if i > 0 or "." in identifier_value:
                candidate_index = i
                break

        if candidate_index < 0:
            return False

        trailing_target = positional_items[candidate_index]
        trailing_args = self._new_map(self._span_from_nodes(trailing_target, positional_items[-1]))
        for item in positional_items[candidate_index + 1 :]:
            self._add_positional(trailing_args, item)

        key_token = self._advance()
        self._consume("DOUBLE_COLON", "Expected '::' after map key")
        if self._at_stop(stop) or not self._starts_value():
            self.eh.throwWithSpan("expectedValue", "expected value after '::'", self._peek().span)

        allow_implicit_call = self._check("LPAREN")
        value = self.parse_expression(stop=stop, allow_implicit_call=allow_implicit_call)
        self._add_map_item(trailing_args, str(key_token.value), value)

        trailing_call = self._call(trailing_target, trailing_args)
        combined_items = positional_items[:candidate_index] + [trailing_call]
        self._set_positional_items(result, combined_items)
        result["span"] = self._merge_spans(result["span"], trailing_call["span"])
        return True

    def _parse_kwarg_into(self, result: dict[str, any], stop: set[str]) -> None:
        key_token = self._advance()
        self._consume("DOUBLE_COLON", "Expected '::' after map key")
        if self._at_stop(stop) or not self._starts_value():
            self.eh.throwWithSpan("expectedValue", "expected value after '::'", self._peek().span)
        # Keep subsequent keyword arguments at this call level.
        # Parenthesized values can still contain intentional implicit calls.
        allow_implicit_call = self._check("LPAREN")
        value = self.parse_expression(stop=stop, allow_implicit_call=allow_implicit_call)
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
        operator_syntax: bool = False,
        unit_syntax: bool = False,
    ) -> dict[str, any]:
        span_end = end_token if end_token is not None else args
        return self._node(
            "call",
            self._span_from_node_list(target, span_end),
            target=target,
            args=args,
            current_interp_arg=None,
            operator_syntax=operator_syntax,
            unit_syntax=unit_syntax,
        )

    def _new_map(self, span: dict[str, int]) -> dict[str, any]:
        result: dict[str, any] = {
            "type": "map",
            "map": {},
            "truthiness": lambda map: bool(map["map"]),
            "span": dict(span),
        }
        if self.preserve_comments:
            result["comments"] = []
        return result

    def _add_positional(self, result: dict[str, any], value: dict[str, any]) -> None:
        if "value" not in result["map"]:
            result["map"]["value"] = value
        elif result["map"]["value"]["type"] == "array" and result["map"]["value"].get("is_argument_pack"):
            result["map"]["value"]["items"].append(value)
            result["map"]["value"]["span"] = self._merge_spans(result["map"]["value"]["span"], value["span"])
        else:
            result["map"]["value"] = self._node(
                "array",
                self._merge_spans(result["map"]["value"]["span"], value["span"]),
                items=[result["map"]["value"], value],
            )
            result["map"]["value"]["is_argument_pack"] = True
        result["span"] = self._merge_spans(result["span"], value["span"])

    def _get_positional_items(self, result: dict[str, any]) -> list[dict[str, any]]:
        value = result["map"].get("value")
        if value is None:
            return []
        if value["type"] == "array" and value.get("is_argument_pack"):
            return list(value["items"])
        return [value]

    def _set_positional_items(self, result: dict[str, any], items: list[dict[str, any]]) -> None:
        map_obj = result["map"]
        if not items:
            map_obj.pop("value", None)
            return
        if len(items) == 1:
            map_obj["value"] = items[0]
            return

        array_node = self._node(
            "array",
            self._span_from_nodes(items[0], items[-1]),
            items=items,
        )
        array_node["is_argument_pack"] = True
        map_obj["value"] = array_node

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
            text=token.text
        )

    def _looks_like_kwarg(self) -> bool:
        return self._peek().type in {"IDENTIFIER", "STRING", "INTEGER", "FLOAT", "OPERATOR"} and self._peek(1).type == "DOUBLE_COLON"

    def _starts_value(self) -> bool:
        return self._peek().type in self.VALUE_STARTERS or self._check("COMMENT")

    def _starts_value_at_offset(self, offset: int) -> bool:
        token = self._peek(offset)
        return token.type in self.VALUE_STARTERS or token.type == "COMMENT"

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
        self.eh.throwWithSpan("illegalSyntax", message, self._peek().span)

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
        return {"type": node_type, **fields, "map": {}, "truthiness": lambda x: bool(x.get("value")), "span": dict(span)}

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

def parse_perkeo(
    content: str,
    preserve_comments: bool = True,
    perkeo: any = None,
) -> dict[str, any]:
    return Parser(perkeo, content, preserve_comments=preserve_comments).parse()
