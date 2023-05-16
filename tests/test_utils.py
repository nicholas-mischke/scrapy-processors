
import pytest
from scrapy_processors.utils import get_callable_args


class TestGetCallableArgs:

    def test_lambda(self):
        args = get_callable_args(lambda arg1, arg2: None)
        assert args == ['arg1', 'arg2']

    def test_function(self):
        def some_function(arg1, arg2):
            pass

        args = get_callable_args(some_function)
        assert args == ['arg1', 'arg2']

    def test_method(self):
        class SomeClass:
            def some_method(self, arg1, arg2):
                pass

        obj = SomeClass()
        args = get_callable_args(obj.some_method)
        assert args == ['arg1', 'arg2']

    def test_class(self):
        class SomeClass:
            def __call__(self, arg1, arg2):
                pass

        args = get_callable_args(SomeClass)
        assert args == ['arg1', 'arg2']

    def test_callable_with_call_method(self):
        class SomeClass:
            def __call__(self, arg1, arg2):
                pass

        obj = SomeClass()
        args = get_callable_args(obj)
        assert args == ['arg1', 'arg2']

    def test_callable_without_call_method(self):
        class SomeClass:
            pass

        obj = SomeClass()
        with pytest.raises(TypeError):
            get_callable_args(obj)

    def test_callable_without_arguments(self):
        def no_arguments():
            pass

        args = get_callable_args(no_arguments)
        assert args == []

    def test_callable_with_self_argument(self):
        # a function with a self argument should keep the self argument
        # since it's not a method of a class, where we'd expect self to be.

        def with_self(self, arg1, arg2):
            pass

        args = get_callable_args(with_self)
        assert args == ['self', 'arg1', 'arg2']
