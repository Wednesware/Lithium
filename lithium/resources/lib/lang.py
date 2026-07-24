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
    
def _pko_operator(interpreter, target, value: "string") -> dict: # type: ignore
    return {
        "type": "operator",
        "value": value["value"],
        "map": {},
        "span": value["span"],
    }

def _pko_unit(interpreter, target, value: "string") -> dict: # type: ignore
    return {
        "type": "unit",
        "value": value["value"],
        "map": {},
        "span": value["span"],
    }
    
def _pko_rve(interpreter, target, value: "string") -> dict: # type: ignore
    return eval(value["value"])

def _pko_ast(interpreter, target, value: "any") -> dict: # type: ignore
    span = value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"]
    return {
        "type": "string",
        "value": str(value),
        "text": f"\"{str(value)}\"",
        "raw": True,
        "map": {},
        "truthiness": lambda x: bool(x["map"]),
        "span": span,
    }