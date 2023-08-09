# Standard library imports
from typing import Any, Iterable, List, Optional, Union, Mapping

# itemloadesr imports
from itemloaders.utils import arg_to_iter

# Local application/library specific imports
from scrapy_processors.base import ProcessorCollection
from scrapy_processors.base import (
    chainmap_context_decorator,
    iter_values_chainmap_context_decorator,
)
from scrapy_processors.common import T, V
from scrapy_processors.utils import wrap_context


class MapCompose(ProcessorCollection):
    """
    This Processor is used to apply a sequence of processors to each value in a collection of values.
    This behavior distinguishes it from the Compose Processor, which applies a sequence of
    processors to a collection as a whole.

    The constructor of this Processor accepts any callable object as an argument.
    Any keyword arguments are passed to the constructor become the default_context

    Example:
        Consider you wish to remove superfluous whitespace in a string and then convert the
        string to lowercase. This can be achieved using the NormalizeWhitespace Processor
        from this package and Python's built-in str.lower function. They can be chained
        together using the MapCompose Processor:

        >>> processor = MapCompose(NormalizeWhitespace(), str.lower)
        >>> processor([' Hello', 'World '])
        ['hello', 'world']

        The processor also works on single values, asumming they're not iterable,
        or on strings / dictionaries, which are treated as single non iterable.
        >>> processor(' Hello')
        ['hello']

        To demonstrate addition of MapCompose objects:

        >>> map_compose_1 = MapCompose(NormalizeWhitespace())
        >>> map_compose_2 = MapCompose(str.lower)
        >>> map_compose_3 = map_compose_1 + map_compose_2
        >>> map_compose_3([' Hello', 'World '])
        ['hello', 'world']

        To add a single callable function to a MapCompose instance:

        >>> map_compose_1 = MapCompose(NormalizeWhitespace(), str.lower)
        >>> map_compose_2 = map_compose_1 + str.upper
        >>> map_compose_2([' Hello', 'World '])
        ['HELLO', 'WORLD']

        To add a collection of processors to a MapCompose instance:

        >>> processors = [str.upper, str.capitalize]
        >>> map_compose_1 = MapCompose(NormalizeWhitespace(), str.lower)
        >>> map_compose_2 = map_compose_1 + processors
        >>> map_compose_2([' Hello', 'World '])
        ['Hello', 'World']
    """

    def __call__(self, values, loader_context=None) -> Any:
        wrapped_processors = [
            wrap_context(processor, loader_context) for processor in self.processors
        ]

        for processor in wrapped_processors:
            processed_values = []
            for value in values:
                try:
                    processed_values += arg_to_iter(processor(value))
                except Exception as e:
                    raise ValueError(
                        "Error in MapCompose with "
                        f"{str(processor)} value={values} "
                        f"error='{type(e).__name__}: {str(e)}'"
                    ) from e
            values = processed_values
        return values


class Compose(ProcessorCollection):
    """
    This Processor is used to apply a sequence of processors to a
    single value of a collection of values.
    This behavior distinguishes it from the MapCompose Processor, which
    applies a sequence of processors to each value in a collection.

    constructor takes args and kwargs. args become the processors and kwargs become the default_context
    stop_on_none: if True, the processing chain will stop when a processor returns None.
    This is the default behavior.

    Examples:
        To demonstrate the addition of Compose objects:

        >>> compose_1 = Compose(sum)
        >>> compose_2 = Compose(lambda x: x * 2)
        >>> compose_3 = compose_1 + compose_2
        >>> compose_3([1, 2, 3, 4, 5])
        30

        To add a single callable function to a Compose instance:

        >>> compose_1 = Compose(sum)
        >>> compose_2 = compose_1 + (lambda x: x * 2)
        >>> compose_2([1, 2, 3, 4, 5])
        30

        To add a collection of processors to a Compose instance:

        >>> processors = [sum, lambda x: x * 2]
        >>> compose_1 = Compose(min, lambda x: [x])
        >>> compose_2 = compose_1 + processors
        >>> compose_2([1, 2, 3, 4, 5])
        2

        Note that above if lambda x: x * 2 is replaced with
        lambda x: [x * 2] a list will be returned instead of an int.
        This may or may not be desirable depending on the use case.
    """

    stop_on_none: bool = True
    default: Any = None

    def __call__(self, values, loader_context=None) -> Any:

        stop_on_none, default = self.unpack_context(loader_context)

        wrapped_processors = [
            wrap_context(processor, loader_context) for processor in self.processors
        ]

        for processor in wrapped_processors:
            if value is None and stop_on_none:
                return default
            try:
                value = processor(value)
            except Exception as e:
                raise ValueError(
                    "Error in Compose with "
                    f"{str(processor)} value={value} "
                    f"error='{type(e).__name__}: {str(e)}'"
                ) from e
        return value
