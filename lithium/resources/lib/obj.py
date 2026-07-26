def _pko_class(interpreter, target, value: "array|idarray", inherits: "any" = None) -> dict: # type: ignore
    inherits = inherits if inherits is not None else {"type": "array", "items": []}
    span = value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"]
    name: str = value["items"][0]["value"]
    block = value["items"][1]
    previous_ast = interpreter.current_ast
    last_result = {"type": "null", "map": {}, "span": span}
    for item in block.get("body", []):
        interpreter.current_ast = item
        interpreted = interpreter.interpret()
        if interpreted is not None:
            last_result = interpreted
    interpreter.current_ast = previous_ast
    interpreter.scopes.pop()
    return {
        "type": "class",
        "value": name,
        "map": {},
        "span": span,
    }