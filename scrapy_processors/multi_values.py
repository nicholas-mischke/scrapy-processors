# Standard Library Imports
from decimal import Decimal
from fractions import Fraction
from typing import Any, Iterable, List, Optional, Tuple

# Local Imports
from scrapy.utils.python import flatten
from scrapy_processors.base import Processor


falsey_values = (
    None,
    False,
    0,
    0.0,
    0j,
    Decimal(0),
    Fraction(0, 1),
)


def is_truthy(
    value: Any,
    falsey_values: Tuple[Any] = falsey_values,
    empty_iterables_are_falsey: bool = True,
    *exclude,
) -> bool:
    """Determines whether a value is "truthy" or "falsey" according to specific rules.

    Parameters:
    ----------
        - value (Any): The value to be checked.
        - falsey_values (Tuple[Any], optional): A tuple of falsey values. Defaults to predefined falsey_values.
        - empty_iterables_are_falsey (bool, optional): Determines if empty iterables are considered falsey. Defaults to True.
        - exclude: Types that are excluded from the check. Defaults to None.

    Returns:
    -------
        bool: True if the value is truthy, False if it is falsey.
    """
    for falsey_value in exclude:
        if isinstance(value, type(falsey_value)) and str(value) == str(falsey_value):
            return True

    if (
        empty_iterables_are_falsey
        and hasattr(value, "__iter__")
        and hasattr(value, "__len__")
        and len(value) == 0
    ):
        return False

    for falsey_value in falsey_values:
        if isinstance(value, type(falsey_value)) and str(value) == str(falsey_value):
            return False

    return True


class TakeAll:
    """
    Identical to itemloaders.processors.Identity Processor.
    The name is more intuitive when using the processor as an output processor.

    Example:
    --------
    >>> processor = TakeAll()
    >>> processor(['apple', 'banana', 'cherry'])
    ['apple', 'banana', 'cherry']
    >>> processor('apple')
    'apple' # Not ['apple'], but would be if it inherited from scrapy_processors.base.Processor

    Note:
    ----
    This processor does not inherit from scrapy_processors.base.Processor.
    This is because values is wrapped in a list if it's a single value.
    """

    def __call__(self, values: Any) -> Any:
        return values

class Identity(TakeAll):
    """
    Identical to itemloaders.processors.Identity Processor and the
    scrapy_processors.TakeAll Processor. While the TakeAll name is more intuitive
    when using the processor as an output processor, the Identity name is more
    intuitive when using the processor as an input processor.

    Example:
    --------
    >>> processor = TakeAll()
    >>> processor(['apple', 'banana', 'cherry'])
    ['apple', 'banana', 'cherry']
    >>> processor('apple')
    'apple' # Not ['apple'], but would be if it inherited from scrapy_processors.base.Processor

    Note:
    ----
    This processor does not inherit from scrapy_processors.base.Processor.
    This is because values is wrapped in a list if it's a single value.
    """
    ...

class TakeAllTruthy(Processor):
    """
    Processor that takes an iterable and returns all truthy values.
    If no values are truthy, return the default parameter passed to the constructor.

    In Python, truthy values are those which are evaluated to True in a Boolean context.
    All values are considered "truthy" except for the following, which are "falsy":
    - None
    - False
    - zero of any numeric type (0, 0.0, 0j, Decimal(0), Fraction(0, 1))
    - empty sequences and collections ('', (), [], {}, set(), range(0))

    Default Context:
    ----------------
    - falsey_values (Tuple[Any]):
        Defaults to (None, False, 0, 0.0, 0j, Decimal(0), Fraction(0, 1)).
    - empty_iterables_are_falsey (bool): Determine if empty iterables are considered falsey.
        Defaults to True.
    - exclude (Optional[Iterable[Any]]): Types to exclude from the check.
        Defaults to "Don't exclude any falsey values".
    - default (Any): The default list to return when no truthy values exist. Defaults to an empty list.
        Defaults to None.

    Returns:
    -------
    List[Any]: A list of all truthy values.

    Example:
    --------
        >>> processor = TakeAllTruthy()
        >>> processor([0, False, None, [], 'Hello', 5])
        ['Hello', 5]
    """

    falsey_values: Tuple[Any] = falsey_values
    empty_iterables_are_falsey: bool = True
    exclude: Optional[Iterable[Any]] = "Don't exclude any falsey values"

    default: Any = None  # value to return if all values are falsey

    def __call__(self, values, **loader_context) -> List[Any]:
        (
            falsey_values,
            empty_iterables_are_falsey,
            exclude,
            default,
        ) = self.unpack_context(**loader_context)

        exclude = tuple() if exclude == "Don't exclude any falsey values" else exclude
        truthy = [
            v
            for v in values
            if is_truthy(v, falsey_values, empty_iterables_are_falsey, *exclude)
        ]

        if len(truthy) == 0:
            return default
        return truthy


class TakeFirst(Processor):
    """
    Nearly identical to itemloaders.processors.TakeFirst Processor.
    Difference being it's now contextually aware, and allows for a default value.

    Default Context:
    ----------------
    - exclude (Tuple[Any, ...]): Values to exclude from returning, even if first.
    - default (Any): The default value to return if no values are found.

    Returns:
    -------
    Any: The first value in the list, or the default value if no values are found.

    Example:
    --------
    >>> processor = TakeFirst()
    >>> processor(['apple', 'banana', 'cherry'])
    'apple'
    """

    exclude: Tuple[Any, ...] = (None, "")
    default: Any = None

    def __call__(self, values, **loader_context):
        for value in values:
            if value not in loader_context["exclude"]:
                return value
        return loader_context["default"]


class TakeFirstTruthy(Processor):
    """
    A TakeFirst processor that returns the first truthy value.

    Default Context:
    ----------------
    - falsey_values (Tuple[Any]):
        Defaults to (None, False, 0, 0.0, 0j, Decimal(0), Fraction(0, 1)).
    - empty_iterables_are_falsey (bool): Determine if empty iterables are considered falsey.
        Defaults to True.
    - exclude (Optional[Iterable[Any]]): Types to exclude from the check.
        Defaults to "Don't exclude any falsey values".
    - default (Any): The default list to return when no truthy values exist. Defaults to an empty list.
        Defaults to None.

    Returns:
    -------
    Any: The first truthy value.

    Example:
    --------
    >>> processor = TakeFirstTruthy()
    >>> processor([0, False, None, [], 'Hello', 5])
    'Hello'
    """

    falsey_values: Tuple[Any] = falsey_values
    empty_iterables_are_falsey: bool = True
    exclude: Optional[Iterable[Any]] = "Don't exclude any falsey values"

    default: Any = None  # value to return if all values are falsey

    def __call__(self, values: Any, **loader_context) -> Any:
        (
            falsey_values,
            empty_iterables_are_falsey,
            exclude,
            default,
        ) = self.unpack_context(**loader_context)

        exclude = tuple() if exclude == "Don't exclude any falsey values" else exclude
        for value in values:
            if is_truthy(value, falsey_values, empty_iterables_are_falsey, *exclude):
                return value
        return default


class Coalesce(Processor):
    """
    Return first non ``NoneType`` value in an iterable.

    Default Context:
    ----------------
    - default (Any): The value to return if all values are `None`. Defaults to `None`.

    Returns:
    -------
    Any: The first non-None value.

    Example:
    --------
    >>> processor = Coalesce(default='No values')
    >>> processor([None, None, None, 'Hello', None])
    'Hello'
    >>> processor([None, None, None])
    'No values'
    """

    default: Any = None  # value to return if all values are None

    def __call__(self, values, **loader_context) -> Any:
        for value in values:
            if value is not None:
                return value
        return loader_context["default"]


class Join(Processor):
    """
    Given an iterable of values, return a string of the values joined by a separator.
    Elements of the iterable must be strings or have a __str__ method defined.

    Default Context:
    ----------------
    - separator (str): The separator to use when joining values. Defaults to a space (" ").

    Returns:
    -------
    str: The joined string.

    Example:
    --------
    >>> processor = Join(separator=', ')
    >>> processor(['apple', 'banana', 'cherry'])
    'apple, banana, cherry'
    """

    separator: str = " "

    def __call__(self, values, **loader_context) -> str:
        return loader_context["separator"].join([str(value) for value in values])


class Flatten(Processor):
    """
    Flatten an iterable of iterables into a single iterable.

    Example:
    --------
    >>> processor = Flatten()
    >>> processor([[1, 2], [3, 4], [5, 6]])
    [1, 2, 3, 4, 5, 6]
    """

    def __call__(self, values) -> List[Any]:
        return flatten(values)
