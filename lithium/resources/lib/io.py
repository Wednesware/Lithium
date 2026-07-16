import os, subprocess


def _pko_print(interpreter, target, value: "any" = None, to: "identifier|idarray" = None) -> None: # type: ignore
    string_value = interpreter.stringifier.stringify(value) if value is not None else ""
    outputs: list[str] = [loc["value"] for loc in (to["items"] if to["type"] == "array" else [to])] if to is not None else interpreter.outputs
    for output in outputs:
        if output == "terminal":
            print(string_value)
        else:
            if os.path.exists(output):
                with open(output, "a") as file:
                    file.write(f"{string_value}\n")
            else:
                interpreter.eh.throw("invalidOutput", f"output target '{output}' does not exist.")
def _pko_clear(interpreter, target, value: "identifier|idarray" = None) -> None: # type: ignore
    outputs: list[str] = [loc["value"] for loc in (value["items"] if value["type"] == "array" else [value])] if value is not None else interpreter.outputs
    print(outputs)
    for output in outputs:
        if output == "terminal":
            print("hi")
            subprocess.run(["clear"])
        else:
            if os.path.exists(output):
                with open(output, "w") as file:
                    file.write("")
            else:
                interpreter.eh.throw("invalidOutput", f"output target '{output}' does not exist.")
def _pko_stringify(interpreter, target, value: "any" = None, force: "boolean" = False) -> str: # type: ignore
    string_value = interpreter.stringifier.stringify(value, allow_custom_stringification=not force) if value is not None else ""
    return {
        "type": "string",
        "value": string_value,
        "map": {},
        "span": value["span"] if isinstance(value, dict) and "span" in value else interpreter.current_ast["span"],
    }