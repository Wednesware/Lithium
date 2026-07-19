def _pko_type(interpreter, target, value: "any") -> dict: # type: ignore
    span = value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"]
    return {
        "type": "string",
        "value": value["type"],
        "map": {},
        "span": span,
    }
    
def _pko_id(interpreter, target, value: "string") -> dict: # type: ignore
    return {
        "type": "identifier",
        "value": value["value"],
        "map": {},
        "span": value["span"],
    }