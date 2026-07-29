import copy


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
        interpreter.eh.throw("scopeError", "'class' body left an inconsistent scope stack.")
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
    interpreter.scopes[-1].set(name, class_ast)
    return class_ast

def _pko_new(interpreter, target, value: "identifier|string") -> dict: # type: ignore
    span = value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"]
    class_name = value["value"]
    class_data = interpreter.findVariable(class_name)
    if not isinstance(class_data, dict) or class_data.get("type") != "class":
        interpreter.eh.throw("typeError", f"'{class_name}' is not a class.")
    return {
        "type": "instance",
        "value": class_name,
        "map": copy.deepcopy(class_data.get("map", {})),
        "truthiness": lambda x: True,
        "span": span,
    }