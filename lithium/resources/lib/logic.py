def _truthy(value: dict) -> bool:
	if not isinstance(value, dict):
		return bool(value)
	predicate = value.get("truthiness")
	if callable(predicate):
		return bool(predicate(value))
	if "value" in value:
		return bool(value["value"])
	if "items" in value:
		return bool(value["items"])
	if "map" in value:
		return bool(value["map"])
	return True

def _run_block(interpreter, block: dict) -> dict:
	previous_ast = interpreter.current_ast
	last_result = {"type": "null", "map": {}, "span": block["span"]}
	for item in block.get("body", []):
		interpreter.current_ast = item
		interpreted = interpreter.interpret()
		if interpreted is not None:
			last_result = interpreted
	interpreter.current_ast = previous_ast
	return last_result

def _pko_if(interpreter, target, value: "array") -> dict:  # type: ignore
    items = value.get("items", []) if isinstance(value, dict) else []
    if len(items) < 2:
        interpreter.eh.throw("tooFewArguments", "'if' expects condition and block.")
    condition = items[0]
    block = items[1]
    if not isinstance(block, dict) or block.get("type") != "block":
        interpreter.eh.throw("typeError", "'if' expects a child block after '->'.")
    condition_true: bool = _truthy(condition)
    interpreter.last_if = condition_true
    if condition_true:
        return _run_block(interpreter, block)
    return {"type": "null", "map": {}, "span": block["span"]}

def _pko_else(interpreter, target, value: "block") -> dict:  # type: ignore
    if not hasattr(interpreter, "last_if") or interpreter.last_if is None:
        interpreter.eh.throw("unexpectedElse", "'else' must follow an 'if' statement or 'elseif' statement.")
    if interpreter.last_if:
        return {"type": "null", "map": {}, "span": target["span"]}
    block = value.get("body", [])
    if not block:
        interpreter.eh.throw("tooFewArguments", "'else' expects a child block after '->'.")
    return _run_block(interpreter, block)

def _pko_elseif(interpreter, target, value: "array") -> dict:  # type: ignore
    if not hasattr(interpreter, "last_if") or interpreter.last_if is None:
        interpreter.eh.throw("unexpectedElseIf", "'elseif' must follow an 'if' statement or 'elseif' statement.")
    if interpreter.last_if:
        return {"type": "null", "map": {}, "span": target["span"]}
    items = value.get("items", []) if isinstance(value, dict) else []
    if len(items) < 2:
        interpreter.eh.throw("tooFewArguments", "'elseif' expects condition and block.")
    condition = items[0]
    block = items[1]
    if not isinstance(block, dict) or block.get("type") != "block":
        interpreter.eh.throw("typeError", "'elseif' expects a child block after '->'.")
    condition_true: bool = _truthy(condition)
    interpreter.last_if = condition_true
    if condition_true:
        return _run_block(interpreter, block)
    return {"type": "null", "map": {}, "span": block["span"]}

def _pko_match(interpreter, target, value: "array") -> dict:  # type: ignore
    items = value.get("items", []) if isinstance(value, dict) else []
    if len(items) < 2:
        interpreter.eh.throw("tooFewArguments", "'match' expects a value and at least one case.")
    object = items[0]
    block = items[1]
    if not isinstance(block, dict) or block.get("type") != "block":
        interpreter.eh.throw("typeError", "'match' expects a child block after '->'.")
    interpreter.match = object
    return_value = _run_block(interpreter, block)
    interpreter.match = None
    return return_value

def _pko_case(interpreter, target, value: "array") -> dict:  # type: ignore
    if interpreter.match is None:
        interpreter.eh.throw("unexpectedCase", "'case' must be used within a 'match' block.")
    items = value.get("items", []) if isinstance(value, dict) else []
    if len(items) < 2:
        interpreter.eh.throw("tooFewArguments", "'case' expects a value and a block.")
    case_value = items[0]
    block = items[1]
    if not isinstance(block, dict) or block.get("type") != "block":
        interpreter.eh.throw("typeError", "'case' expects a child block after '->'.")
    if case_value == interpreter.match:
        return _run_block(interpreter, block)