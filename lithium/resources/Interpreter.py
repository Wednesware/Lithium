from __future__ import annotations

import os


type Builtin = any
type Scope = any

class Interpreter:
    def __init__(
            self,
            lithium,
            ast_or_parser: dict[str, any] | any,
            output: callable | None = None,
    ):
        self.lithium = lithium
        self.ast_or_parser = ast_or_parser
        self.output = output or print
        self.global_scope = self.lithium.res.Scope()
        self.builtins: dict[str, Builtin] = {}
        self.last_result = None
        self.install_defaults()

    def _resolve_module_path(self, name):
        candidates = [
            f"{name}.pk"
        ]

        for candidate in candidates:
            path = os.path.join(
                self.lithium.path,
                candidate,
            )

            if os.path.exists(path):
                return path

        return None

    def operator_builtin(self, symbol, operation):
        def builtin(interpreter, node, args, scope):
            values = args.get("value")

            if not isinstance(values, list) or len(values) != 2:
                raise interpreter.error(
                    f"Operator {symbol!r} expects two operands",
                    node,
                )

            left, right = values

            try:
                return operation(left, right)
            except Exception as exc:
                raise interpreter.error(
                    str(exc),
                    node,
                ) from exc

        return builtin

    def install_defaults(self):
        self.global_scope.define("true", True, constant=True)
        self.global_scope.define("false", False, constant=True)
        self.global_scope.define("null", None, constant=True)

        self.register_builtin(
            "call",
            self.lithium.res.Builtins.call,
        )
        self.register_builtin(
            "return",
            self.lithium.res.Builtins.return_,
        )
        self.register_builtin(
            "import",
            self.lithium.res.Builtins.import_,
        )

        for symbol, operation in {
            "+": lambda a,b:a+b,
            "-": lambda a,b:a-b,
            "*": lambda a,b:a*b,
            "/": lambda a,b:a/b,
            "%": lambda a,b:a%b,
            "=": lambda a,b:a==b,
            "==": lambda a,b:a==b,
            "!=": lambda a,b:a!=b,
            ">": lambda a,b:a>b,
            ">=": lambda a,b:a>=b,
            "<": lambda a,b:a<b,
            "<=": lambda a,b:a<=b,
        }.items():
            self.register_builtin(
                symbol,
                self.operator_builtin(symbol, operation),
            )

    def register_builtin(
        self,
        name,
        handler,
        evaluate_args=True,
        pass_block=False,
    ):
        info = self.lithium.res.Builtin(
            handler,
            evaluate_args,
            pass_block,
        )

        self.builtins[name] = info

        self.global_scope.define(
            name,
            handler,
            constant=True,
        )

        return handler

    def run_code(self) -> any:
        ast = self.ast_or_parser
        if hasattr(ast, "last_ast") and ast.last_ast is not None:
            ast = ast.last_ast
        elif hasattr(ast, "parse"):
            ast = ast.parse()

        try:
            self.last_result = self.execute(ast, self.global_scope)
        except self.lithium.res.ReturnSignal as signal:
            self.last_result = signal.value
        return self.last_result

    def execute(self, node: dict[str, any] | None, scope: Scope | None = None) -> any:
        if node is None:
            return None
        scope = scope or self.global_scope
        node_type = node.get("type")
        method = getattr(self, f"execute_{node_type}", None)
        if method is None:
            return self.evaluate(node, scope)
        return method(node, scope)

    def execute_script(self, node: dict[str, any], scope: Scope) -> any:
        result = None
        for child in node.get("body", []):
            if child.get("type") == "comment":
                continue
            result = self.execute(child, scope)
        return result

    def execute_block(self, node: dict[str, any] | None, scope: Scope | None = None) -> any:
        if node is None:
            return None
        scope = scope or self.global_scope.child()
        result = None
        for child in node.get("body", []):
            if child.get("type") == "comment":
                continue
            try:
                result = self.execute(child, scope)
            except self.lithium.res.ReturnSignal as signal:
                if signal.layers == -1 or signal.layers <= 1:
                    raise
                raise self.lithium.res.ReturnSignal(signal.value, signal.layers - 1)
        return result

    def execute_line(self, node: dict[str, any], scope: Scope) -> any:
        return self.evaluate(node.get("value"), scope)

    def evaluate(self, node: dict[str, any] | None, scope: Scope | None = None) -> any:
        if node is None:
            return None
        scope = scope or self.global_scope
        node_type = node.get("type")
        method = getattr(self, f"evaluate_{node_type}", None)
        if method is None:
            raise self.error(f"Unsupported node type {node_type!r}", node)
        return method(node, scope)


    def evaluate_integer(self, node: dict[str, any], scope: Scope) -> int:
        return node["value"]


    def evaluate_float(self, node: dict[str, any], scope: Scope) -> float:
        return node["value"]


    def evaluate_string(self, node: dict[str, any], scope: Scope) -> str:
        return node["value"]


    def evaluate_identifier(self, node: dict[str, any], scope: Scope) -> any:
        return scope.get(node["value"])


    def evaluate_operator(self, node: dict[str, any], scope: Scope) -> str:
        return node["value"]


    def evaluate_group(self, node: dict[str, any], scope: Scope) -> any:
        return self.evaluate(node.get("value"), scope)


    def evaluate_array(self, node: dict[str, any], scope: Scope) -> list[any]:
        return [
            self.evaluate(item, scope)
            for item in node.get("items", [])
            if item.get("type") != "comment"
        ]


    def evaluate_map(self, node: dict[str, any], scope: Scope) -> dict[str, any]:
        result: dict[str, any] = {}
        if node.get("value") is not None:
            result["value"] = self.evaluate(node["value"], scope)
        for key, value in node.get("kwargs", {}).items():
            result[key] = self.evaluate(value, scope)
        return result


    def evaluate_block(self, node: dict[str, any], scope: Scope) -> dict[str, any]:
        return node


    def evaluate_comment(self, node: dict[str, any], scope: Scope) -> None:
        return None


    def evaluate_call(self, node: dict[str, any], scope: Scope) -> any:
        if self._is_operator_call(node):
            return self._evaluate_operator_call(node, scope)

        target = self.evaluate(node["target"], scope)
        args = self.prepare_argument_map(
            node.get("args"),
            scope,
            evaluate=not isinstance(target, self.lithium.res.Builtin) or target.evaluate_args,
        )

        builtin = None

        if node["target"]["type"] == "identifier":
            builtin = self.builtins.get(
                node["target"]["value"]
            )

        if builtin:
            args = self.prepare_argument_map(
                node.get("args"),
                scope,
                evaluate=builtin.evaluate_args,
            )

            return builtin.handler(
                self,
                node,
                args,
                scope,
            )
        if callable(target):
            values = args["value"] if isinstance(args["value"], list) else [args["value"]]
            values = [] if args["value"] is None else values
            return target(*values, **args["kwargs"])

        raise self.error(f"Cannot call {type(target).__name__}", node)


    def prepare_argument_map(
            self,
            node: dict[str, any] | None,
            scope: Scope,
            evaluate: bool = True,
    ) -> dict[str, any]:
        if node is None:
            return {"value": None, "kwargs": {}}

        value = node.get("value")
        if evaluate:
            positional = self._evaluate_positional(value, scope)
            kwargs = {
                key: self.evaluate(value_node, scope)
                for key, value_node in node.get("kwargs", {}).items()
            }
        else:
            positional = self._raw_positional(value)
            kwargs = dict(node.get("kwargs", {}))

        return {
            "value": positional,
            "kwargs": kwargs,
            "node": node,
        }


    def write(self, text: str, end: str = "\n") -> None:
        self.output(text, end=end)


    def stringify(self, value: any) -> str:
        if value is True:
            return "true"
        if value is False:
            return "false"
        if value is None:
            return "none"
        return str(value)


    def truthy(self, value: any) -> bool:
        return bool(value)


    def error(self, message: str, node: dict[str, any] | None = None) -> Exception:
        span = node.get("span") if isinstance(node, dict) else None
        error_class = getattr(self.lithium.res.errors, "LithiumRuntimeError", RuntimeError)
        return error_class(message, span)


    def _evaluate_positional(self, value: dict[str, any] | None, scope: Scope) -> any:
        if value is None:
            return None
        if value.get("type") == "array":
            return [
                self.evaluate(item, scope)
                for item in value.get("items", [])
                if item.get("type") != "comment"
            ]
        return self.evaluate(value, scope)


    def _raw_positional(self, value: dict[str, any] | None) -> any:
        if value is None:
            return None
        if value.get("type") == "array":
            return [
                item
                for item in value.get("items", [])
                if item.get("type") != "comment"
            ]
        return value


    def _is_operator_call(self, node: dict[str, any]) -> bool:
        args = node.get("args", {})
        value = args.get("value")
        return (
                isinstance(value, dict)
                and value.get("type") == "array"
                and bool(value.get("items"))
                and value["items"][0].get("type") == "operator"
        )


    def _evaluate_operator_call(self, node: dict[str, any], scope: Scope) -> any:
        items = node["args"]["value"]["items"]
        left = self.evaluate(node["target"], scope)
        index = 0

        while index < len(items):
            operator_node = items[index]
            right_node = items[index + 1] if index + 1 < len(items) else None
            if right_node is None:
                raise self.error("Operator is missing a right-hand value", operator_node)
            operator_name = operator_node["value"]
            operator = scope.get(operator_name)
            if not isinstance(operator, self.lithium.res.Builtin):
                raise self.error(f"Operator {operator_name!r} is not callable", operator_node)
            right = self.evaluate(right_node, scope)
            left = operator(
                self,
                node,
                {
                    "value": [left, right],
                    "kwargs": {},
                    "node": node.get("args"),
                },
                scope,
            )
            index += 2

        return left