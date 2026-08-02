class ReturnSignal(Exception):
    def __init__(self, value: any = None, layers: int = 1):
        self.value = value
        self.layers = layers
        super().__init__(value, layers)