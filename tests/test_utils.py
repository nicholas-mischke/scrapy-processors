
import pytest
from scrapy_processors.utils import get_callable, merge_context_dicts

# Generic callables
def str_upper(value):
    return value.upper()

def str_reverse(value):
    return value[::-1]

class SomeClass:
    def some_method(self):
        return None

class SomeCallableClass:
    def __call__(self):
        return None

def some_function():
    return None
# some_lambda = lambda x: x.upper()
# This lambda function is suppose to be the line above, but the autofomatter
# I use often turns into the line below.
# def some_lambda(x): return x.upper()
some_lambda = lambda x: x.upper()
some_method = SomeClass().some_method
some_callable_obj = SomeCallableClass()

@pytest.mark.parametrize("input_values, expected_output", [
    (str.upper, str.upper),  # function
    (some_function, some_function),  # function
    (some_lambda, some_lambda),  # lambda
    (some_method, some_method),  # method
    (some_callable_obj, some_callable_obj),  # callable class instance
])
def test_get_callable(input_values, expected_output):
    assert get_callable(input_values) == expected_output

def test_get_callable_on_callable_cls():
    assert get_callable(SomeCallableClass).__func__ \
        == SomeCallableClass.__call__

@pytest.mark.parametrize("input_values", [
    [1, 2, 3],  # list
    SomeClass,  # class
    SomeClass(),  # class instance
    'some string',  # string
])
def test_get_callable_raises_TypeError(input_values):
    with pytest.raises(TypeError) as error:
        result = get_callable(input_values)

    assert 'Unsupported callable type' in str(error.value)


@pytest.mark.parametrize("dict1, dict2, expected_output", [
    ({}, {}, {}),
    ({'a': 1}, {}, {'a': 1}),
    ({}, {'a': 1}, {'a': 1}),
    ({'a': 1}, {'b': 2}, {'a': 1, 'b': 2}), # No shared keys
    (
        {'a': 1, 'b': 2, 'c': 3},
        {'b': 2, 'c': 3, 'd': 4},
        {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    ), # Some Shared keys
])
def test_merge_context_dicts(dict1, dict2, expected_output):
    assert merge_context_dicts(dict1, dict2) == expected_output

def test_merge_context_dicts_raises_ValueError():
    dict1 = {'a': 1, 'b': 2, 'c': 3}
    dict2 = {'b': 3, 'c': 4, 'd': 5}
    
    # Test with mismatched values for shared keys
    with pytest.raises(ValueError):
        merge_context_dicts(dict1, dict2)