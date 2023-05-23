
from inspect import isclass
from itemloaders.utils import get_func_args


def get_callable(arg):
    """
    Given an argument, return a callable.

    If the argument is callable, return it.
    If the argument is a class, instantiate it and return the instance.
    If the argument or instiated class isn't callable, raise a TypeError.
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


def merge_context_dicts(dict1, dict2):
    """
    Used to merge the default_loader_contexts of two Compose or MapCompose
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
    default_loader_context = dict1.copy()
    default_loader_context.update(dict2)

    return default_loader_context


def context_to_kwargs(context, callable):
    """
    Extracts the values from the context dict that are relevant to the callable
    and returns them as a kwargs dict.
    """
    callable_args = get_func_args(callable)
    return {key: context[key] for key in callable_args if key in context}
