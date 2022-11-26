from dataclasses import dataclass
from typing import Dict
import abc


class Layer(abc.ABC):
    def __call__(self, extra: Dict):
        extra["layer"] = self.__class__.__name__.upper()


class Presentation(Layer):
    pass


class Application(Layer):
    pass


class Business(Layer):
    pass


class Persistence(Layer):
    pass


class Database(Layer):
    pass
