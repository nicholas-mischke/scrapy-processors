
import pytest
from scrapy_processors.utils import *


class test_wrap_context:

    def func_without_context(values):
        return None

    def func_with_context(values, context):
        return None

    def func_with_loader_context(values, loader_context):
        return None

    def func_with_too_many_args(values, context, a, b, c):
        return None

    @pytest.mark.parametrize("func", [
        func_without_context,
        func_with_context,
        func_with_loader_context,
    ])
    def test(self, func):
        wrapped_func = wrap_context(func, {})

        try:
            wrapped_func('some value')
            assert True
        except TypeError:
            assert False

    def test_TypeError(self):
        wrapped_func = wrap_context(
            test_wrap_context.func_with_too_many_args,
            {}
        )

        with pytest.raises(TypeError) as error:
            wrapped_func('some value')


class test_get_processor:

    class SomeUncallableClass:
        def some_method(self, arg):
            return None

    class SomeCallableClass:
        def __call__(self, arg):
            return None

        def __eq__(self, other):
            return isinstance(other, self.__class__)

    # Must take at least one argument, to be valid processor.
    def some_function(arg):
        return None
    some_method = SomeUncallableClass().some_method

    @pytest.mark.parametrize("processor", [
        str.upper,           # `C` function
        some_function,       # function
        lambda x: x.upper(), # lambda
        some_method,         # method
        SomeCallableClass(), # callable class
    ])
    def test(self, processor):
        assert get_processor(processor) == processor

    @pytest.mark.parametrize("not_a_processor", [
        [1, 2, 3],             # list
        SomeUncallableClass(), # class
        'some string',         # string
    ])
    def test_non_callable_TypeError(self, not_a_processor):
        with pytest.raises(TypeError) as error:
            result = get_processor(not_a_processor)

        assert "cannot be used as a processor, because it's not callable." in str(error.value)
