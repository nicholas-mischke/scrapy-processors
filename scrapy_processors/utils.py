
from inspect import isclass, isfunction, ismethod

from itemloaders.utils import get_func_args


def get_callable_args(callable):
    """
    Given a callable, return a list of the names of the arguments.
    if `self` is in names, remove it.
    """

    if isfunction(callable):
        return get_func_args(callable)
    elif ismethod(callable):
        func = callable
    elif isclass(callable):
        func = callable().__call__
    elif hasattr(callable, '__call__'): # is object with __call__ method
        func = callable.__call__
    else:
        raise TypeError()
    
    args = get_func_args(func)
    return [arg for arg in args if arg != 'self']
