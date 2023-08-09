# Standard library imports
from typing import Any, Iterable, List, Mapping, Optional, Tuple

# itemloaders imports
from scrapy.utils.python import flatten
from itemloaders.processors import Identity

# Local application/library specific imports
from scrapy_processors.base import Processor
from scrapy_processors.common import falsey_values
from scrapy_processors.common import V


class TakeAll(Identity):
    """
    Renaming of itemloaders.processors.Identity Processor.
    The name is more intutive when using the processor as an output processor.
    """

    pass


class TakeAllTruthy(Processor):
    """
    Processor that takes an iterable and returns all truthy values.
    If no values are truthy, return default parameter passed to the constructor.

    In Python, truthy values are those which are evaluated to True in a Boolean context.
    All values are considered "truthy" except for the following, which are "falsy":
    - None
    - False
    - zero of any numeric type (0, 0.0, 0j, Decimal(0), Fraction(0, 1))
    - empty sequences and collections ('', (), [], {}, set(), range(0))

    Args:
        default (List[Any]): The default list to return when no truthy values exist. Defaults to an empty list.

    Returns:
        List[Any]: The list of all truthy values in the input iterable.

    Example:
        processor = TakeAllTruthy(default=[1, 2, 3])
        result = processor([0, False, None, [], 'Hello', 5])  # passing an iterable to the instance
        print(result)  # Output: ['Hello', 5]
    """

    default: Any = None  # value to return if all values are falsey
    falsey: Tuple[Any] = falsey_values

    def __call__(
        self, values: Iterable[V], loader_context: Optional[Mapping[str, Any]] = None
    ) -> List[V]:
        default, falsey = self.unpack_context(loader_context)
        return [value for value in values if value not in falsey] or default


class TakeFirstTruthy(Processor):
    """
    A TakeFirst processor that returns the first truthy value.
    """

    default: Any = None  # value to return if all values are falsey
    falsey: Tuple[Any] = falsey_values

    def __call__(
        self, values: Iterable[V], loader_context: Optional[Mapping[str, Any]] = None
    ) -> V:
        default, falsey = self.unpack_context(loader_context)

        for value in values:
            if value not in falsey:
                return value

        return default


class Coalesce(Processor):
    """Return first non NoneType value in an iterable."""

    def __call__(self, values, loader_context=None):
        return next((v for v in values if v is not None), None)


class Join(Processor):
    """
    Given an iterable of values, return a string of the values joined by a separator.
    Elements of the iterable must be strings or have a __str__ method defined.
    """

    separator: str = " "

    def __call__(
        self, values: Iterable[V], loader_context: Optional[Mapping[str, Any]] = None
    ) -> str:
        separator = self.unpack_context(loader_context)
        return separator.join([str(value) for value in values])


class Flatten(Processor):
    """
    _flatten_ an iterable of iterables into a single iterable.
    """

    def __call__(self, values, loader_context=None) -> List[V]:
        return flatten(values)
