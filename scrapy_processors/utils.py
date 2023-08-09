# Standard library imports
from functools import partial
from typing import Any, Callable, Dict, Mapping, Set, Tuple, Type, Union, Iterable

# itemloaders imports
from itemloaders.utils import get_func_args

# Local application/library specific imports
from scrapy_processors.common import ProcessorType, WrappedProcessorType


def wrap_context(
    processor: ProcessorType, context: Mapping[str, Any]
) -> WrappedProcessorType:
    """
    Wraps a callable function to include a context dictionary as the first argument.
    If the callable function does not accept a 'context' or 'loader_context' argument,
    it is returned without modification.

    Args:
        context: Context dictionary to include as the first argument of the callable.
        callable: Callable function to wrap.

    Returns:
        A new callable function that includes the context as the first argument.

    Example:
        >>> wrap_contextual_callable({'x': 1}, lambda x: x * 2)(2)
        2
        >>> wrap_contextual_callable({'x': 1}, lambda context, x: context['x'] * x)({'x': 2}, 3)
        6
    """
    args = get_func_args(processor)

    if "context" in args:
        return partial(processor, context=context)
    elif "loader_context" in args:
        return partial(processor, loader_context=context)
    else:
        return processor


def get_processor(potential_processor: Union[Callable, Type]) -> ProcessorType:
    """
    Returns a callable ProcessorType given an argument. The argument can either be a
    callable object or a class that once initialized becomes callable.

    If the argument is already callable, it's directly returned.
    If the argument is a class, an instance is created and if the instance has
    a __call__ method, it's returned.

    Note:
        Ideally this would check for that the callable only accepts one or two arguments,
        value(s) and optionally a context. Because built-in python C functions
        cannot be inspected, this is not possible.

        for example: str.upper only accepts one argument, and is a valid processor
        but get_func_args(str.upper) raises a TypeError.

    Args:
        arg: A callable object or a class.

    Returns:
        ProcessorType object derived from the input argument.

    Raises:
        TypeError: If the argument or instantiated class is not callable.

    Example:
        >>> get_processor(lambda x: x + 1)(2)
        3
        >>> class Adder:
        ...     def __call__(self, x):
        ...         return x + 1
        ...
        >>> get_processor(Adder)(2)
        3
    """

    name = getattr(
        potential_processor, "__qualname__", type(potential_processor).__name__
    )

    if not callable(potential_processor):
        raise TypeError(
            f"{name} type cannot be used as a processor, because it's not callable."
        )

    # A callable object is a valid processor when it can be called with a single
    # argument, or two arguments where the second argument is a mapping.

    # Since built-in python C functions cannot be inspected, we cannot know
    # if they're valid processors, by simply using get_func_args().

    # If we wrap the callable with a context, we can call it with a single
    # argument and see if it raises a TypeError. This would give a good indication
    # if the callable is a valid processor or not.

    # However, this is not a good solution, because it's possible that the callable
    # raises a TypeError for reasons other than the number of arguments.
    # e.g.,
    #   lambda x: x ** 2 raises a TypeError if x is a string, but is a valid processor.
    #   str.upper raises a TypeError if it's called with an int, but is a valid processor.

    # A second way to check if a callable is a valid processor, is to check the error message.
    # However, this is not a good solution either, because the error message could change
    # in the future, and may be different depending on the python version.

    # So there's no good way to check if a callable is a valid processor,
    # without actually calling it...

    return potential_processor


def merge_contexts(
    context_a: Mapping[str, Any], context_b: Mapping[str, Any]
) -> Dict[str, Any]:
    """
    Merge two dicts, if they contain the same key the must contain the same
    value, if they don't raise an Exception.
    This is used to merge the default_context of two ProcessorCollections.
    """

    shared_keys = list(set(context_a.keys()) & set(context_b.keys()))  # same order
    a_values = [context_a[key] for key in shared_keys]
    b_values = [context_b[key] for key in shared_keys]

    if a_values != b_values:
        raise ValueError(
            f"Contexts contain different values for the same keys: {shared_keys}"
        )

    return {**context_a, **context_b}


def to_sets(*args: Any) -> Tuple[Set[Any], ...]:
    """
    Convert iterables to sets, place non-iterables into a set.
    Returns a tuple of sets
    """
    sets = []
    for arg in args:
        if arg is None:
            sets.append(set())
        elif isinstance(arg, (list, tuple, set)):
            sets.append(set(arg))
        else:
            sets.append({arg})

    if len(sets) == 1:
        return sets[0]
    return tuple(sets)
