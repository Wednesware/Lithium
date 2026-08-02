from __future__ import annotations

import os, sys
import importlib, importlib.util

from lithium.ww.mg26_11.config import ObjectNotation, ObjectNotationError # type: ignore
from lithium.ww.mg26_11.filepath import FilePath


class Handler:
    NAME: str = ""
    def __init__(self, project: Project):
        self.project: Project = project
    def __getattr__(self, name: str) -> any: # type: ignore
        path_no_ext: str = os.path.join(self.project.path, self.NAME, name)
        path: str = f"{path_no_ext}.py"
        if os.path.isdir(path_no_ext) and not os.path.exists(path):
            return type(self.__class__.__name__ + "_" + name, (self.__class__,), {"NAME": os.path.join(self.NAME, name)})(self.project)
        spec: importlib.util.Spec | None = importlib.util.spec_from_file_location(name, path) # type: ignore
        if spec is None:
            raise FileNotFoundError(f"Script '{name}' not found at path '{path}'")
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        return getattr(script, name)

class ScriptHandler(Handler):
    NAME: str = "scripts"
    def __getattr__(self, name: str) -> callable | handler: # type: ignore
        attribute_return: any = super().__getattr__(name) # type: ignore
        if isinstance(attribute_return, Handler):
            return attribute_return
        elif callable(attribute_return):
            return lambda *args, **kwargs: attribute_return(self.project, *args, **kwargs)
        raise TypeError(f"Script '{name}' is not a function")
    
class ResourceHandler(Handler):
    NAME: str = "resources"
    def __getattr__(self, name: str) -> type | Handler:
        attribute_return: any = super().__getattr__(name) # type: ignore
        if isinstance(attribute_return, (type, Handler)):
            return attribute_return
        raise TypeError(f"Resource '{name}' is not a class")

class Project:
    def __init__(self, cwd: str, name: str):
        self.name: str = name
        self.path: str = os.path.abspath(os.path.join(cwd, "..", self.name))
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Project '{self.name}' not found at path '{self.path}'")
        self.script: ScriptHandler = ScriptHandler(self)
        self.res: ResourceHandler = ResourceHandler(self)
        self.metadata: dict[str, any] = {}
    def getsetting(self, name: str, else_value: any = "<raiseerror>", scope: str = "prefer args", arg_names: list[str] | None = None) -> any:
        arg_names = [arg_name.format(name=name, n=name[0]) for arg_name in arg_names or ["--{name}", "-{n}"]]
        args_scope_value: str = "<notfound>"
        for i, arg in enumerate(sys.argv[1:], start=1):
            if arg in arg_names:
                try:
                    args_scope_value = sys.argv[i + 1]
                except IndexError:
                    pass
                break
        settings_path: FilePath = FilePath(self.path) / "settings.pyon"
        if not settings_path.exists():
            settings_path.write("{}")
        settings_on: ObjectNotation = ObjectNotation(settings_path)
        settings_scope_value: any = settings_on.get(name, "<notfound>")
        match scope:
            case "only args":
                return_value: any = args_scope_value
            case "only settings":
                return_value: any = settings_scope_value
            case "prefer args":
                return_value: any = settings_scope_value if args_scope_value == "<notfound>" else args_scope_value
            case "prefer settings":
                return_value: any = args_scope_value if settings_scope_value == "<notfound>" else settings_scope_value
            case "return both":
                return {
                    "args": args_scope_value,
                    "settings": settings_scope_value
                }
            case "return none":
                return None
        if return_value == "<notfound>":
            if else_value == "<raiseerror>":
                raise ValueError(f"setting '{name}' was not provided.")
            return else_value
        return return_value