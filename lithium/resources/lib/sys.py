import time


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