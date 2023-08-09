
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

if __name__ == '__main__':
    # for i, value in enumerate(falsey_values):
    #     if value is None and str(value) == 'None':
    #         print('found None')
    #     elif isinstance(value, bool) and str(value) == 'False':
    #         print('found False')
    #     elif isinstance(value, (int, Decimal, Fraction)) and str(value) == '0':
    #         print('found 0')
    #     elif isinstance(value, float) and str(value) == '0.0':
    #         print('found 0.0')
    #     elif isinstance(value, complex) and str(value) == '0j':
    #         print('found complex 0j')
    #     elif isinstance(value, str) and value == '':
    #         print('found empty string')
    #     elif isinstance(value, (list, dict, set, range)) and value in ([], {}, set(), range(0)):
    #         print('found empty iterable')
    #     else:
    #         print(f'Mised this one... {i}')

    values = [0, False, None, []]
    print(' ' in values)

    # print(0j)