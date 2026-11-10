class Missing:
    def __init__(self, path):
        self.path = path

    def __getitem__(self, key):
        return Missing(f"{self.path}[{key}]")

    def __format__(self, spec):
        suffix = f":{spec}" if spec else ""
        return f"{{{self.path}{suffix}}}"


class FormatData(dict):
    def __missing__(self, key):
        return Missing(key)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        if isinstance(value, dict):
            return FormatData(value)
        return value
