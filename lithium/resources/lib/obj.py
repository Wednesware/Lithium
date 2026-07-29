import copy
from decimal import Decimal


_pko_operator = {
    "type": "class",
    "value": "operator",
    "map": {
        "__class_kind__": {
            "type": "string",
            "value": "operator",
            "map": {},
            "span": {"line": 0, "column": 0, "end_column": 0},
        },
    },
    "truthiness": lambda _: True,
    "span": {"line": 0, "column": 0, "end_column": 0},
}


def _class_kind(class_map: dict) -> str | None:
    kind = class_map.get("__class_kind__")
    if isinstance(kind, dict) and kind.get("type") == "string":
        return kind.get("value")
    return None


def _register_unit(interpreter, name: str, class_map: dict, span: dict) -> dict:
    scale = class_map.get("scale")
    if not isinstance(scale, dict) or scale.get("type") != "array" or len(scale.get("items", [])) != 2:
        interpreter.eh.throw("invalidUnitScale", "a custom unit needs `scale::[numerator:denominator referenceUnit]`.")

    ratio, reference = scale["items"]
    if not isinstance(ratio, dict) or ratio.get("type") != "map":
        interpreter.eh.throw("invalidUnitScale", "a custom unit scale must start with a numeric ratio.")
    numerator = ratio.get("map", {}).get("start")
    denominator = ratio.get("map", {}).get("end")
    if not isinstance(numerator, dict) or not isinstance(denominator, dict):
        interpreter.eh.throw("invalidUnitScale", "a custom unit scale ratio must have a numerator and denominator.")
    numerator_value = interpreter.perkeo.res.Builtins._asDecimal(interpreter.perkeo.res.Builtins._asNumber(interpreter, numerator))
    denominator_value = interpreter.perkeo.res.Builtins._asDecimal(interpreter.perkeo.res.Builtins._asNumber(interpreter, denominator))
    if denominator_value == 0:
        interpreter.eh.throw("invalidUnitScale", "a custom unit scale denominator cannot be zero.")
    if isinstance(reference, dict) and reference.get("type") == "identifier":
        reference = interpreter.findVariable(reference["value"])
    if not isinstance(reference, dict) or reference.get("type") != "unit":
        interpreter.eh.throw("invalidUnitScale", "a custom unit scale must end with a reference unit.")

    reference_name = reference["value"]
    unit_defs = interpreter.perkeo.res.Builtins._unitDefs(interpreter)
    dimension = interpreter.perkeo.res.Builtins._unitDimension(interpreter, reference_name)
    reference_factor = unit_defs.get(reference_name, (None, None))[1]
    if dimension is None or reference_factor is None:
        interpreter.eh.throw("invalidUnitScale", f"'{reference_name}' cannot be used as a custom unit scale reference.")

    unit_defs[name] = (
        dimension,
        reference_factor * numerator_value / denominator_value,
    )
    return interpreter.perkeo.res.Builtins.getUnitASTOf(
        interpreter,
        name,
        source=interpreter.perkeo.res.Builtins.unitCall,
    )


def _register_operator(interpreter, name: str, class_ast: dict, class_map: dict, span: dict) -> dict:
    symbol = class_map.get("symbol")
    apply = class_map.get("apply")
    if not isinstance(symbol, dict) or symbol.get("type") != "string" or not symbol.get("value"):
        interpreter.eh.throw("invalidOperator", "a custom operator needs a non-empty `symbol::" + '"%%"' + "` member.")
    if not isinstance(apply, dict) or apply.get("type") != "function":
        interpreter.eh.throw("invalidOperator", "a custom operator needs an `fn apply` member.")

    parameter_names = [parameter[0] for parameter in apply.get("params", [])]

    def operator_call(call_interpreter, target, value: "array") -> dict:  # type: ignore
        left, right = call_interpreter.perkeo.res.Builtins._binaryItems(call_interpreter, value)
        if len(parameter_names) == 2:
            call_kwargs = {parameter_names[0]: left, parameter_names[1]: right}
        else:
            call_kwargs = {"value": value}

        members = class_ast["map"].copy()
        members["me"] = class_ast
        call_interpreter.scopes.insert(0, call_interpreter.perkeo.res.Scope(call_interpreter, "operator", members))
        try:
            return apply["map"]["call"]["source"](call_interpreter, apply, **call_kwargs)
        finally:
            call_interpreter.scopes.pop(0)

    return interpreter.perkeo.res.Builtins.getOperatorASTOf(
        interpreter,
        symbol["value"],
        source=operator_call,
        prio=3,
    )


def _pko_class(interpreter, target, value: "array|idarray", inherits: "any" = None) -> dict: # type: ignore
    span = value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"]
    name: str = value["items"][0]["value"]
    block = value["items"][1]
    class_scope = interpreter.scopes[-1]
    class_scope_index = len(interpreter.scopes) - 1
    previous_ast = interpreter.current_ast
    for item in block.get("body", []):
        interpreter.current_ast = item
        interpreter.interpret()
    interpreter.current_ast = previous_ast

    if interpreter.scopes[class_scope_index] is not class_scope:
        interpreter.eh.throw("inconsistentScopeStack", "'class' body left an inconsistent scope stack.")
    own_map: dict = {}
    for scope in interpreter.scopes[class_scope_index:]:
        own_map.update(scope.vars)
    del interpreter.scopes[class_scope_index:]

    combined_map: dict = {}
    for parent in interpreter.perkeo.res.Builtins._classParents(inherits):
        if not isinstance(parent, dict) or parent.get("type") != "class":
            parent_type = parent.get("type") if isinstance(parent, dict) else type(parent).__name__
            interpreter.eh.throw("typeError", f"'inherits' expects class values, got {parent_type!r}")
        combined_map.update(copy.deepcopy(parent.get("map", {})))
    combined_map.update(own_map)

    class_ast = {
        "type": "class",
        "value": name,
        "map": combined_map,
        "truthiness": lambda x: True,
        "span": span,
    }
    kind = _class_kind(combined_map)
    if kind == "unit":
        unit_ast = _register_unit(interpreter, name, combined_map, span)
        interpreter.scopes[-1].set(name, unit_ast)
        return unit_ast
    interpreter.scopes[-1].set(name, class_ast)
    if kind == "operator":
        operator_ast = _register_operator(interpreter, name, class_ast, combined_map, span)
        interpreter.scopes[-1].set(operator_ast["value"], operator_ast)
    return class_ast

def _pko_new(interpreter, target, value: "identifier|string", **kwargs) -> dict: # type: ignore
    span = value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"]
    class_name = value["value"]
    class_data = interpreter.findVariable(class_name)
    if not isinstance(class_data, dict) or class_data.get("type") != "class":
        interpreter.eh.throw("typeError", f"'{class_name}' is not a class.")
    instance = {
        "type": "instance",
        "value": class_name,
        "map": copy.deepcopy(class_data.get("map", {})),
        "truthiness": lambda x: True,
        "span": span,
    }
    constructor = instance["map"].get("constructor")
    if constructor is None:
        if kwargs:
            interpreter.eh.throw("noConstructor", f"'{class_name}' has no constructor to receive creation arguments.")
        return instance
    if not isinstance(constructor, dict) or constructor.get("type") != "function":
        interpreter.eh.throw("invalidConstructor", f"'{class_name}.constructor' must be a function.")

    members = instance["map"].copy()
    members["me"] = instance
    interpreter.scopes.insert(0, interpreter.perkeo.res.Scope(interpreter, "instance", members))
    try:
        constructor["map"]["call"]["source"](interpreter, constructor, **kwargs)
    finally:
        interpreter.scopes.pop(0)
    return instance