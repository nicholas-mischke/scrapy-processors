
from inspect import isclass
from typing import Any, Callable, Dict, Type, Union

import math

from itemloaders.utils import get_func_args


def get_callable(arg: Union[Callable, Type]) -> Callable:
    """
    Returns a callable object given an argument.

    If the argument is already callable, it's directly returned.
    If the argument is a class, the class is initalized. If the instance has
        a __call__ method, it's returned.
    If the argument or instantiated class is not callable, a TypeError is raised.

    Args:
        arg: A callable object or a class.

    Returns:
        Callable object derived from the input argument.

    Raises:
        TypeError: If the argument isn't a callable or a class.
    """
    if (
        callable(arg)
        and not isclass(arg)  # classes need to be instantiated
    ):
        return arg

    if isclass(arg):
        arg = arg()

    if hasattr(arg, '__call__'):
        return arg.__call__
    else:
        raise TypeError(
            f"Unsupported callable type: '{type(arg).__name__}'"
        )


def merge_context_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges two context dictionaries, ensuring that shared keys have matching values.

    Args:
        dict1: First dictionary to merge.
        dict2: Second dictionary to merge.

    Returns:
        A new dictionary that combines dict1 and dict2.

    Raises:
        ValueError: If shared keys between the dictionaries don't have matching values.
    """
    shared_keys = set(dict1.keys()) & set(dict2.keys())

    error_msg = ''
    for key in shared_keys:
        if dict1[key] != dict2[key]:
            error_msg += f"self[{key}]: {dict1[key]}, other[{key}]: {dict2[key]}\n"
    if error_msg:
        error_msg = 'Mismatched Pairs: ' + error_msg
        raise ValueError(error_msg.strip())

    # Combine default_loader_contexts
    merged_context = dict1.copy()
    merged_context.update(dict2)

    return merged_context


def unpack_context(context, num_args: int = None) -> tuple:
    values = tuple(context.values())
    if num_args is not None:
        return values[:num_args]
    return values

def context_to_kwargs(context: Dict[str, Any], callable: Callable) -> Dict[str, Any]:
    """
    Extracts the values from a context dictionary that match the arguments of a callable.

    Args:
        context: Context dictionary with potential arguments for the callable.
        callable: Callable function for which to extract relevant arguments.

    Returns:
        A dictionary with keys and values that match the arguments of the callable.
    """
    callable_args = get_func_args(callable)
    return {key: context[key] for key in callable_args if key in context}
