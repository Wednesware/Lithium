import time, subprocess


def _pko_wait(interpreter, target, value: "float|integer") -> None: # type: ignore
    time.sleep(value["value"])
    
def _pko_output(interpreter, target, value: "identifier") -> None: # type: ignore
    if value["value"] not in interpreter.outputs:
        if value["value"] in interpreter.outputs:
            interpreter.eh.throw("invalidOutput", f"output target '{value['value']}' is already in the list of outputs.")
        interpreter.outputs.append(value["value"])
        
def _pko_rmoutput(interpreter, target, value: "identifier") -> None: # type: ignore
    if value["value"] in interpreter.outputs:
        if value["value"] not in interpreter.outputs:
            interpreter.eh.throw("invalidOutput", f"output target '{value['value']}' is not in the list of outputs.")
        interpreter.outputs.remove(value["value"])
        
def _pko_console(interpreter, target, value: "string|identifier") -> None: # type: ignore
    subprocess.run(value["value"], shell=True, check=True)
    
def _pko_scopes(interpreter, target) -> dict: # type: ignore
    span = interpreter.current_ast["span"]
    return {
        "type": "array",
        "items": [{"type": "data", "source": scope, "map": {}, "span": span, "stringify": lambda x: f"<{x['source'].name} scope data at {hex(id(x))}>"} for scope in interpreter.scopes],
        "map": {},
        "truthiness": lambda x: len(x.get("items", [])) > 0,
        "span": span,
    }
    
def _pko_visualise(interpreter, target, value: "data") -> None: # type: ignore
    print(repr(value["source"]))