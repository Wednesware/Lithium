class Scope:
    def __init__(self, parent: "Scope | None" = None):
        self.parent = parent
        self.values: dict[str, any] = {}
        self.constants: set[str] = set()

    def child(self) -> "Scope":
        return self.lithium.res.Scope(self)

    def define(self, name: str, value: any, constant: bool = False) -> any:
        if name in self.constants:
            raise RuntimeError(f"Cannot redefine constant {name!r}")
        self.values[name] = value
        if constant:
            self.constants.add(name)
        return value

    def assign(self, name: str, value: any) -> any:
        scope = self._find_scope(name)
        if scope is None:
            return self.define(name, value)
        if name in scope.constants:
            raise RuntimeError(f"Cannot assign constant {name!r}")
        scope.values[name] = value
        return value

    def get(self, name: str) -> any:
        scope = self._find_scope(name)
        if scope is None:
            raise NameError(f"Unknown identifier {name!r}")
        return scope.values[name]

    def has(self, name: str) -> bool:
        return self._find_scope(name) is not None

    def to_dict(self) -> dict[str, any]:
        values: dict[str, any] = {}
        if self.parent is not None:
            values.update(self.parent.to_dict())
        values.update(self.values)
        return values

    def _find_scope(self, name: str) -> "Scope | None":
        if name in self.values:
            return self
        if self.parent is not None:
            return self.parent._find_scope(name)
        return None