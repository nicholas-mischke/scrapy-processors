
import pytest
from scrapy_processors.base import *

from collections import ChainMap


@pytest.fixture
def processor_cls():
    class SomeProcessor(Processor):

        a, b, c = 1, 2, 3

        # These decorators are designed to be used with methods, that take self
        # as the first argument, so we'll use a class.
        # We need new methods in the class as process_value and __call__
        # are already decorated by the MetaClass.

        @iter_values_decorator
        def method_for_iter_values_test(self, value):
            assert hasattr(value, '__iter__')

        @chainmap_context_decorator
        def method_for_chainmap_context_test(self, context):
            assert isinstance(context, ChainMap)
            # Make sure context overrides default_context
            assert context.get('a') == 10

        @iter_values_chainmap_context_decorator
        def method_for_iter_values_chainmap_context_test(self, values, context):
            assert hasattr(values, '__iter__')
            assert isinstance(context, ChainMap)
            # Make sure context overrides default_context
            assert context.get('a') == 10

        def process_value(self, value, context):
            # Not iterable, by default. Only an iterable if the arg passed is.
            # value could be an int, or a list. One is iterable and one is not.
            # For testing only non iterable objects are passed.
            assert not hasattr(value, '__iter__')
            assert isinstance(context, ChainMap)

        def __call__(self, values, loader_context):
            assert hasattr(values, '__iter__')
            assert isinstance(loader_context, ChainMap)

    return SomeProcessor


@pytest.fixture
def processor(processor_cls):
    return processor_cls()


@pytest.fixture
def processor_collection_cls():
    class SomeProcessorCollection(ProcessorCollection):
        a, b, c = 1, 2, 3

        def __call__(self, values, loader_context):
            ...

    return SomeProcessorCollection


@pytest.fixture
def reverse_processor_collection(processor_collection_cls, reverse_processor):
    return processor_collection_cls(reverse_processor)


@pytest.fixture
def processor_collection_cls_b():
    class SomeOtherProcessorCollection(ProcessorCollection):
        a, b, c = 1, 2, 3

        def __call__(self, values, loader_context):
            ...

    return SomeOtherProcessorCollection


class Test_decorators:

    dict_context = {'a': 10, 'b': 20, 'c': 30}
    chainmap_context = ChainMap(dict_context)

    @pytest.mark.parametrize("value", [
        1,                # Not iterable
        ['a', 'b', 'c'],  # Iterable
    ])
    def test_iter_values(self, processor, value):
        processor.method_for_iter_values_test(value)

    @pytest.mark.parametrize("context", [
        dict_context,  # Not ChainMap
        chainmap_context  # ChainMap
    ])
    def test_chainmap_context(self, processor, context):
        processor.method_for_chainmap_context_test(context)

    @pytest.mark.parametrize("values, context", [
        (1, dict_context),  # Not iterable, Not ChainMap
        (1, chainmap_context),  # Not iterable, ChainMap
        (['a', 'b', 'c'], dict_context),  # Iterable, Not ChainMap
        (['a', 'b', 'c'], chainmap_context)  # Iterable, ChainMap
    ])
    def test_iter_values_chainmap_context(self, processor, values, context):
        processor.method_for_iter_values_chainmap_context_test(values, context)


class TestProcessorMeta:

    def test__new__(self, processor):
        # Be sure default_context is set with class variables
        assert processor.default_context == {'a': 1, 'b': 2, 'c': 3}

    def test__init__(self, processor):
        # Test that the Processor subclass doesn't have a __init__ method
        with pytest.raises(TypeError):
            class SomeOtherProcessor(Processor):
                def __init__(self):
                    pass

        # Test that the Processor subclass use `loader_context` rather than `context` in __call__
        with pytest.raises(TypeError):
            class SomeOtherProcessor(Processor):
                def __call__(self, values, context):
                    pass

        # Test that process_value and __call__ are decorated
        processor(1, {})
        processor.process_value(1, {})

    def test__call__(self, processor_cls):
        assert processor_cls().default_context == {'a': 1, 'b': 2, 'c': 3}
        assert processor_cls(a=10, c=30).default_context == {
            'a': 10, 'b': 2, 'c': 30}

    def test__call__TypeError(self, processor_cls):
        # Too many args
        with pytest.raises(TypeError):
            processor_cls(1, 2, 3, 4)

        # Multiple values for keyword argument 'a'
        with pytest.raises(TypeError):
            processor_cls(1, a=1)


class TestProcessorCollectionMeta:

    def test__new__(self, processor_collection_cls):
        # Must be called with at least one processor
        assert processor_collection_cls(
            lambda x: x*2).default_context == {'a': 1, 'b': 2, 'c': 3}

    def test__init__(self):
        # Test that the ProcessorCollection subclass doesn't have a __init__ method
        with pytest.raises(TypeError):
            class SomeOtherProcessorCollection(ProcessorCollection):
                def __init__(self):
                    pass

        # Test that the ProcessorCollection subclass use `loader_context` rather than `context` in __call__
        with pytest.raises(TypeError):
            class SomeOtherProcessorCollection(ProcessorCollection):
                def __call__(self, values, context):
                    pass

    def test__call__(self, processor_collection_cls):
        with pytest.raises(TypeError):
            processor_collection_cls()  # Must be run with at least one processor

        def times_two(x): return x * 2
        def squared(x): return x ** 2

        processor = processor_collection_cls(times_two, squared, a=10, c=30)

        assert processor.processors == (times_two, squared)
        assert processor.default_context == {'a': 10, 'b': 2, 'c': 30}


class TestProcessorMixin:

    def test_cls_name(self, processor):
        assert processor.cls_name == 'SomeProcessor'

    @pytest.mark.parametrize("args, expected_output", [
        (
            (),
            (1, 2, 3)
        ),  # no context
        (
            ({'a': 10}, ),
            (10, 2, 3)
        ),  # context overrides default_context
        (
            ({'d': 40}, ('d', )),
            (1, 2, 3, 40)
        ),  # additional keys
    ])
    def test_unpacked_context(self, processor, args, expected_output):
        assert processor.unpack_context(*args) == expected_output

    def test_unpack_context_single_value(self):
        # single value should be returned as a single value, not a tuple
        class SomeOtherProcessor(Processor):
            z = 10
        assert SomeOtherProcessor().unpack_context() == 10

    def test_context_to_kwargs(self, processor):
        def a_func(a):
            ...

        def bc_func(b, c):
            ...

        assert processor.context_to_kwargs(
            {'a': 100}, a_func
        ) == {'a': 100}
        assert processor.context_to_kwargs(
            {'b': 200}, bc_func
        ) == {'b': 200, 'c': 3}


class TestProcessor:

    def test_process_value_NotImplementedError(self):
        processor = Processor()
        with pytest.raises(NotImplementedError):
            processor.process_value('value')

    def test__call__with_context(self):
        """
        Make sure it can call process_value with a context or without context.
        """
        class ContextSubClass(Processor):
            def process_value(self, value, context):
                ...

        class ContextlessSubClass(Processor):
            def process_value(self, value):
                ...

        context_subclass = ContextSubClass().__call__([])
        contextless_subclass = ContextlessSubClass().__call__([])

    def test__str__(self, processor):
        assert str(processor) == 'SomeProcessor(a=1, b=2, c=3)'

    def test__eq__(self, processor_cls):
        class SomeOtherProcessor(Processor):
            a, b, c = 1, 2, 3

        assert processor_cls() == processor_cls()  # Same type, same default_context
        # same type, different default_context
        assert processor_cls() != processor_cls(10)
        # different type, same default_context
        assert processor_cls() != SomeOtherProcessor()


class TestProcessorCollection:

    def test__call__NotImplementedError(self):
        with pytest.raises(NotImplementedError):
            ProcessorCollection(str.lower).__call__()

    def test__add__(
        self,
        processor_collection_cls,
        reverse_processor_collection,
        reverse_processor,
        lower_processor,
        upper_processor,
        strip_processor
    ):

        processor_b = processor_collection_cls(
            lower_processor, strip_processor)

        # Add single function
        result = reverse_processor_collection + upper_processor
        assert isinstance(result, processor_collection_cls)
        assert result.processors == (reverse_processor, upper_processor)

        # Add collection of functions
        result = reverse_processor_collection + (upper_processor, strip_processor)
        assert isinstance(result, processor_collection_cls)
        assert result.processors == (
            reverse_processor, upper_processor, strip_processor)

        # Add two processor collections of the same type
        result = reverse_processor_collection + processor_b
        assert isinstance(result, processor_collection_cls)
        assert result.processors == (
            reverse_processor, lower_processor, strip_processor)

    def test__add__TypeError(
        self,
        reverse_processor_collection,
        processor_collection_cls_b,
        lower_processor,
    ):
        # Can't add two different types of ProcessorCollection
        with pytest.raises(TypeError):
            reverse_processor_collection + \
                processor_collection_cls_b(lower_processor)

        # Can't add a noncallable to a ProcessorCollection
        with pytest.raises(TypeError):
            reverse_processor_collection + 'not callable'

    # append & extend are the same as __add__, so we don't need to test them

    def test_insert(
        self,
        processor_collection_cls,
        reverse_processor,
        lower_processor,
        strip_processor
    ):
        processor = processor_collection_cls(
            reverse_processor, lower_processor)

        result = processor.insert(1, strip_processor)
        assert isinstance(result, processor_collection_cls)
        assert result.processors == (
            reverse_processor, strip_processor, lower_processor)

    def test__getitem__(
        self,
        processor_collection_cls,
        reverse_processor,
        lower_processor,
        strip_processor
    ):
        processor = processor_collection_cls(
            strip_processor, reverse_processor, lower_processor)

        assert processor[0] == strip_processor
        assert processor[2] == lower_processor
        assert processor[1:3] == (reverse_processor, lower_processor)

    def test_replace_processor(
        self,
        processor_collection_cls,
        reverse_processor,
        lower_processor,
        upper_processor,
    ):
        processor = processor_collection_cls(
            reverse_processor, upper_processor
        )

        result = processor.replace_processor(1, lower_processor)
        assert isinstance(result, processor_collection_cls)
        assert result.processors == (reverse_processor, lower_processor)

    def test_delete_processor(self, processor_collection_cls, reverse_processor, lower_processor):
        processor = processor_collection_cls(
            reverse_processor, lower_processor)

        result = processor.delete_processor(1)
        assert isinstance(result, processor_collection_cls)
        assert result.processors == (reverse_processor, )

    def test_delete_IndexError(self, reverse_processor_collection):
        with pytest.raises(IndexError):
            reverse_processor_collection.delete_processor(0)

    def test__contains__(self, reverse_processor_collection, reverse_processor):
        assert reverse_processor in reverse_processor_collection
        assert str.upper not in reverse_processor_collection

    def test__len__(self, reverse_processor_collection):
        assert len(reverse_processor_collection) == 1

    def test__str__(self, reverse_processor_collection, processor):
        
        assert str(reverse_processor_collection) == \
            'SomeProcessorCollection(reverse_processor)'

        processor_collection = reverse_processor_collection + (processor, str.upper)

        assert str(processor_collection) == \
            'SomeProcessorCollection(reverse_processor, SomeProcessor(a=1, b=2, c=3), str.upper)'
