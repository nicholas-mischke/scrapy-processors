# Standard Library Imports
from typing import Any, List

# Local Imports
from itemloaders.utils import arg_to_iter
from scrapy_processors.base import ProcessorCollection


class Compose(ProcessorCollection):
    """
    Compose applies a collection of processors to the entire list of values,
    one after the other. If a processor returns a list, or another object type
    the next processor is called with that object.

    This distinguishes it from MapCompose, which applies a collection of processors
    to each individual element in a list, one after the other, flattening lists if necessary.

    The __init__ method of this class accepts any number of processors as positional arguments.
    Any keyword arguments passed to the constructor become the default_context for the processors.

    These classes provide a list-like interface for adding, removing, and extending processors.
    This is useful for creating reusable processors that can be extended by other processors.
    When a mutable method (such as addition) is called on a processor, a new processor is returned,
    leaving the original instance unchanged.

    Example:
    -------
        >>> class CubeProcessor(Processor):
        ...     def process_value(self, value, **context):
        ...         return value ** 3

        >>> compose = Compose(CubeProcessor(), sum)
        >>> compose([1, 2, 3, 4, 5])
        225

    List-like interface Example:
    ---------------------------
        >>> compose = Compose(sum)
        >>> compose_with_square = compose + (lambda x: x ** 2)

        >>> compose([1, 2, 3, 4, 5])
        15
        >>> compose_with_square([1, 2, 3, 4, 5])
        55

    Compose vs MapCompose:
    ----------------------
        >>> def reverse(iterable):
        ...     return iterable[::-1]

        >>> map_compose = MapCompose(reverse)
        >>> compose = Compose(reverse)

        >>> map_compose(['hello', 'world'])
        ['olleh', 'dlrow']
        >>> compose(['hello', 'world'])
        ['world', 'hello']
    """

    stop_on_none: bool = True
    default: Any = None

    def __call__(self, values, *wrapped_processors, **loader_context) -> Any:
        stop_on_none, default = self.unpack_context(**loader_context)

        for processor in wrapped_processors:
            if values is None and stop_on_none:
                return default
            try:
                values = processor(values)
            except Exception as e:
                raise ValueError(
                    "Error in Compose with "
                    f"{str(processor)} values={values} "
                    f"error='{type(e).__name__}: {str(e)}'"
                ) from e
        return values


class MapCompose(ProcessorCollection):
    """
    MapCompose applies a collection of processors to each element in a list,
    one after the other. If a processor returns a list, the list is flattened,
    and the next processor is applied to each element of the flattened list.

    This distinguishes it from Compose, which applies a collection of processors
    to the entire list itself, one after the other. If a processor returns a list,
    or another object type the next processor is called with that object.

    The __init__ method of this class accepts any number of processors as positional arguments.
    Any keyword arguments passed to the constructor become the default context for the processors.

    These classes provide a list-like interface for adding, removing, and extending processors.
    This is useful for creating reusable processors that can be extended by other processors.
    When a mutable method (such as addition) is called on a processor, a new processor is returned,
    leaving the original instance unchanged.

    Example:
    -------
        >>> class StripProcessor(Processor):
        ...     def process_value(self, value, **context):
        ...         return value.strip()

        >>> map_compose = MapCompose(StripProcessor(), str.upper, lambda x: x[::-1])
        >>> map_compose([' hello', 'world '])
        ['OLLEH', 'DLROW']

    List-like interface Example:
    ---------------------------
        >>> map_compose = MapCompose(lambda x: x[::-1])
        >>> map_compose_two = map_compose + str.upper

        >>> map_compose(['hello', 'world'])
        ['olleh', 'dlrow']
        >>> map_compose_two(['hello', 'world'])
        ['OLLEH', 'DLROW']

    MapCompose vs Compose:
    ----------------------
        >>> def reverse(iterable):
        ...     return iterable[::-1]

        >>> map_compose = MapCompose(reverse)
        >>> compose = Compose(reverse)

        >>> map_compose(['hello', 'world'])
        ['olleh', 'dlrow']
        >>> compose(['hello', 'world'])
        ['world', 'hello']
    """

    def __call__(self, values, *wrapped_processors, **loader_context) -> List[Any]:
        for processor in wrapped_processors:
            processed_values = []
            for value in values:
                try:
                    processed_values += arg_to_iter(processor(value))
                except Exception as e:
                    raise ValueError(
                        "Error in MapCompose with "
                        f"{str(processor)} values={values} "
                        f"error='{type(e).__name__}: {str(e)}'"
                    ) from e
            values = processed_values
        return values
