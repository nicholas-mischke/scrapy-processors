
from itemloaders.processors import Identity
from itemloaders.processors import Compose as BuiltInCompose
from itemloaders.processors import MapCompose as BuiltInMapCompose

from scrapy_processors.utils import get_callable, merge_context_dicts


class MapCompose(BuiltInMapCompose):
    """
    This class overwrites the built-in MapCompose class constructor,
    allowing it to accept any callable, or any class that once instantiated
    is callable. 

    Additionally, it defines the __add__ method, allowing MapCompose objects
    to be added together. The result is a new MapCompose object with the
    functions and default_loader_contexts of both objects.
    """

    def __init__(self, *callables, **default_loader_context):
        self.functions = tuple(
            get_callable(callable) for callable in callables
        )
        self.default_loader_context = default_loader_context

    def __add_MapCompose(self, other):
        return MapCompose(
            *self.functions + other.functions,
            **merge_context_dicts(
                self.default_loader_context,
                other.default_loader_context
            )
        )

    def __add_callable(self, other):
        try:
            other = get_callable(other)
        except TypeError:
            raise TypeError(
                f"Unsupported operand type for +: 'MapCompose' and '{type(other).__name__}'"
            )

        return MapCompose(* self.functions + (other,), **self.default_loader_context)

    def __add__(self, other):
        if isinstance(other, MapCompose):
            return self.__add_MapCompose(other)
        return self.__add_callable(other)


class Compose(BuiltInCompose):
    """
    MapCompose works on the objs in a list, while Compose works on the list obj itself.
    """

    def __init__(self, *callables, **default_loader_context):
        self.functions = tuple(
            get_callable(callable) for callable in callables
        )
        self.stop_on_none = default_loader_context.get("stop_on_none", True)
        self.default_loader_context = default_loader_context

    def __add_Compose(self, other):
        return Compose(
            *self.functions + other.functions,
            **merge_context_dicts(
                self.default_loader_context,
                other.default_loader_context
            )
        )

    def __add_callable(self, other):
        try:
            other = get_callable(other)
        except TypeError:
            raise TypeError(
                f"Unsupported operand type for +: 'Compose' and '{type(other).__name__}'"
            )

        return Compose(* self.functions + (other,), **self.default_loader_context)

    def __add__(self, other):
        if isinstance(other, Compose):
            return self.__add_Compose(other)
        return self.__add_callable(other)


class TakeAll(Identity):
    """
    Renaming of the built-in `Identity` processor.
    More intutive when used as a output processor.
    """
    pass
