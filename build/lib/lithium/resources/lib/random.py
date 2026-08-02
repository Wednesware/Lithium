import random


def _pko_randominteger(interpreter, target, arg_from: "integer", to: "integer") -> dict:  # type: ignore
    items = value.get("items", []) if isinstance(value, dict) else []
    if len(items) < 2:
        interpreter.eh.throw("tooFewArguments", "'randomInteger' expects a lower and upper bound.")

    lower_bound = items[0]
    upper_bound = items[1]
    if not isinstance(lower_bound, dict) or lower_bound.get("type") != "integer":
        interpreter.eh.throw("typeError", "'randomInteger' expects an integer as the lower bound.")
    if not isinstance(upper_bound, dict) or upper_bound.get("type") != "integer":
        interpreter.eh.throw("typeError", "'randomInteger' expects an integer as the upper bound.")

    random_value = random.randint(lower_bound["value"], upper_bound["value"])
    return {"type": "integer", "value": random_value, "map": {}, "span": target["span"]}