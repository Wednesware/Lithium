from __future__ import annotations


class Builtins:
    @staticmethod
    def return_(interpreter, node, args, scope):
        value = args.get("value")

        if isinstance(value, list):
            value = value[0] if value else None

        raise interpreter.lithium.res.ReturnSignal(value)


    @staticmethod
    def call(interpreter, node, args, scope):
        value = args.get("value")

        if isinstance(value, list):
            value = value[0] if value else None

        if isinstance(value, interpreter.lithium.res.BuiltinInfo):
            return value.handler(
                interpreter,
                node,
                args,
                scope,
            )

        if not callable(value):
            raise interpreter.error(
                "call expects a callable value",
                node,
            )

        kwargs = args.get("kwargs", {})

        return value(
            **kwargs
        )


    @staticmethod
    def import_(interpreter, node, args, scope):
        value = args.get("value")

        if isinstance(value, list):
            value = value[0] if value else None

        if not isinstance(value, str):
            raise interpreter.error(
                "import expects a module name",
                node,
            )

        if value in interpreter.modules:
            return interpreter.modules[value]

        path = interpreter._resolve_module_path(value)

        if path is None:
            raise interpreter.error(
                f"Module {value!r} not found",
                node,
            )

        with open(path, encoding="utf-8") as file:
            source = file.read()

        parser = interpreter.lithium.res.Parser(
            interpreter.lithium,
            source,
        )

        ast = parser.parse()

        module_scope = interpreter.lithium.res.Scope(
            parent=interpreter.global_scope,
            lithium=interpreter.lithium,
        )

        interpreter.execute(
            ast,
            module_scope,
        )

        module = module_scope.to_dict()

        interpreter.modules[value] = module

        return module