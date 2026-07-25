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
    
def _pko_is(interpreter, target, value: "any", type: "idarray|identifier") -> dict: # type: ignore
    span = value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"]
    is_true = value["type"] in ([t["value"] for t in type["items"]] if type["type"] == "array" else [type["value"]])
    return {
        "type": "boolean",
        "value": is_true,
        "map": {},
        "usedalias": str(is_true).lower(),
        "truthiness": lambda x: x["value"],
        "span": span,
    }
    
def _pko_length(interpreter, target, value: "array|string|map") -> dict: # type: ignore
    span = value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"]
    length = 0
    if value["type"] == "array":
        length = len(value.get("items", []))
    elif value["type"] == "string":
        length = len(value.get("value", ""))
    elif value["type"] == "map":
        length = len(value.get("map", {}))
    return {
        "type": "integer",
        "value": length,
        "map": {},
        "truthiness": lambda x: x["value"] > 0,
        "span": span,
    }