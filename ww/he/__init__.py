from __future__ import annotations

import os
import importlib, importlib.util
from ww.mg.config import objectnotation # type: ignore
from ww.mg.filepath import filepath

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
    def __init__(self, project: Project):
        self.project: Project = project
    def __getattr__(self, name: str) -> callable | handler: # type: ignore
        attribute_return: any = super().__getattr__(name) # type: ignore
        if isinstance(attribute_return, Handler):
            return attribute_return
        elif callable(attribute_return):
            return lambda *args, **kwargs: attribute_return(self.project, *args, **kwargs)
        raise TypeError(f"Script '{name}' is not a function")
    
class ResourceHandler(Handler):
    NAME: str = "resources"
    def __init__(self, project: Project):
        self.project: Project = project
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
    def getsetting(self, name: str) -> str:
        return objectnotation(filepath(self.path) / "settings.pyon").get(name)
