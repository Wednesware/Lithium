class Builtin:
    def __init__(
        self,
        handler: callable,
        evaluate_args: bool = True,
        pass_block: bool = False,
    ):
        self.handler = handler
        self.evaluate_args = evaluate_args
        self.pass_block = pass_block