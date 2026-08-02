class perkeoSyntaxError(SyntaxError):
    def __init__(self, message: str, span: dict[str, int] | None = None):
        self.message = message
        self.span = span
        if span is None:
            super().__init__(message)
        else:
            super().__init__(
                f"{message} at {span['line']}:{span['column']}"
        )