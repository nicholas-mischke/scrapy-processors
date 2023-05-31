
# Standard library imports
from decimal import Decimal
from fractions import Fraction
from typing import Any, Callable, Iterable, Mapping, Optional, Tuple, TypeVar, Union


# Typing aliases
T = TypeVar('T')  # Generic input type

V = TypeVar('V')  # Single input value type
ProcessorType = Callable[
    [
        # Process a single value or an iterable of values
        Union[V, Iterable[V]],
        Optional[Mapping[str, Any]]  # Optional context dict or ChainMap
    ],
    Any  # Can return any type
]
WrappedProcessorType = Callable[
    [Union[V, Iterable[V]]],  # Process a single value or an iterable of values
    Any  # Can return any type
]
ProcessorCollectionType = Callable[
    [
        # Process a single value or an iterable of values
        Union[V, Iterable[V]],
        Optional[Mapping[str, Any]]  # Optional context dict or ChainMap
    ],
    Any  # Can return any type
]

# Some useful constants for Processor subclasses default_context
# False and the numeric values return True when False == 0, etc.
special_falsey_values: Tuple[Any] = (None, False)
numeric_falsey_values: Tuple[Any] = (0, 0.0, 0j, Decimal(0), Fraction(0, 1))
iterable_falsey_values: Tuple[Any] = ('', [], {}, set(), range(0))

falsey_values: Tuple[Any] = special_falsey_values + \
    numeric_falsey_values + iterable_falsey_values
