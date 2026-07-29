import copy


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

def _pko_repeat(interpreter, target, value: "array") -> dict:  # type: ignore
    result: dict = {"type": "array", "map": {}, "items": [], "span": target["span"]}
    times: dict = value["items"][0]
    block: dict = value["items"][1]
    original_ast: dict = interpreter.current_ast
    for _ in range(times["value"]):
        result["items"].append(_run_block(interpreter, copy.deepcopy(block)))
        interpreter.current_ast = original_ast
    return result


def _pko_while(interpreter, target, value: "array") -> dict:  # type: ignore
    items = value.get("items", []) if isinstance(value, dict) else []
    if len(items) < 2:
        interpreter.eh.throw("tooFewArguments", "'while' expects condition and block.")

    raw_value = getattr(interpreter, "current_raw_call_args", {}).get("map", {}).get("value")
    if isinstance(raw_value, dict) and raw_value.get("type") == "array" and raw_value.get("is_argument_pack"):
        raw_items = raw_value.get("items", [])
        condition_node = raw_items[0] if raw_items else None
    else:
        condition_node = raw_value

    condition = items[0]
    block = items[1]
    if not isinstance(block, dict) or block.get("type") != "block":
        interpreter.eh.throw("typeError", "'while' expects a child block after '->'.")

    previous_ast = interpreter.current_ast
    while True:
        cond_result = condition
        if isinstance(condition_node, dict):
            interpreter.current_ast = copy.deepcopy(condition_node)
            cond_result = interpreter.interpret()

        if not _truthy(cond_result):
            break

        _run_block(interpreter, copy.deepcopy(block))

    interpreter.current_ast = previous_ast
    return {"type": "null", "map": {}, "span": block["span"]}


def _pko_for(interpreter, iterable, value: "identifier|block"):
    for item in iterable:
        interpreter.call_function(callback, [item])
