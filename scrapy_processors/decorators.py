# Standard library imports
from abc import ABC
from collections import ChainMap
from functools import wraps
import inspect
from typing import Any, Callable

# itemloaders imports
from scrapy.utils.python import flatten # from itertools import chain
from itemloaders.utils import arg_to_iter


def apply_decorators(func, *decorators):
    """
    Apply a tuple of decorators to a function
    """
    for decorator in reversed(decorators):
        func = decorator(func)
    return func


def get_bound_arguments(func, *args, **kwargs):
    """
    Bind arguments to the function.
    """
    signature = inspect.signature(func)
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    return bound.arguments


class BaseDecorator:
    def __init__(self, func):
        wraps(func)(self)
        self.func = func

    def modify_kwargs(self, kwargs):
        return kwargs

    def modify_result(self, result):
        return result

    def __call__(self, *args, **kwargs):
        kwargs = get_bound_arguments(self.func, *args, **kwargs)
        kwargs = self.modify_kwargs(kwargs)
        result = self.func(**kwargs)
        return self.modify_result(result)


class ChainMapedContext(BaseDecorator):
    def modify_kwargs(self, kwargs):
        default_context = kwargs["self"].default_context
        for key in ["context", "loader_context"]:
            if key in kwargs:
                kwargs[key] = ChainMap(kwargs[key], default_context)
        return kwargs


class ToIterable(BaseDecorator):
    def modify_kwargs(self, kwargs):
        for key in ["value", "values"]:
            if key in kwargs:
                kwargs[key] = arg_to_iter(kwargs[key])
        return kwargs


class Flattener(BaseDecorator):
    def modify_result(self, result):
        return flatten(result)
