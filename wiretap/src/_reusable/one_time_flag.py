class OneTimeFlag:
    def __init__(self, initial_value: bool = False) -> None:
        self.state = initial_value
        self._initial_value = initial_value

    def __bool__(self):
        try:
            return self.state
        finally:
            if self.state == self._initial_value:
                self.state = not self.state
