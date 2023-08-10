import pytest
from scrapy_processors.base import Processor, ProcessorCollection

import re


def single_space(text):
    """
    When testing Exception msg it's easy to add an extra space here or there
    on linebreaks, this function removes all extra whitespace.
    """
    return re.sub(r"\s+", " ", str(text)).strip()


@pytest.fixture
def processor_cls():
    class SomeProcessor(Processor):
        """
        Return arguments to validate decorators are working.
        """

        a, b, c = 1, 2, 3

        def process_value(self, value, **context):
            return value, context

        def __call__(self, values, **loader_context):
            return values, loader_context

    return SomeProcessor


@pytest.fixture
def processor(processor_cls):
    return processor_cls()


@pytest.fixture
def processor_collection_cls():
    class SomeProcessorCollection(ProcessorCollection):
        """
        Return arguments to validate decorators are working.
        """

        a, b, c = 1, 2, 3

        def __call__(self, values, *wrapped_processors, **loader_context):
            return values, wrapped_processors, loader_context

    return SomeProcessorCollection


@pytest.fixture
def processor_collection(processor_collection_cls):
    return processor_collection_cls()


@pytest.fixture
def reverse_processor_collection(reverse_processor):
    return ProcessorCollection(reverse_processor)


class TestProcessorMeta:
    def test__new__(self, processor):
        assert processor.default_context == {"a": 1, "b": 2, "c": 3}

    def test__new__raises(self):
        with pytest.raises(ValueError) as e:

            class SomeProcessor(Processor):
                item = "item"

        assert (
            str(e.value)
            == "The class attribute 'item' is reserved for the ItemLoader class, please choose a different name."
        )

        with pytest.raises(ValueError) as e:

            class SomeProcessor(Processor):
                selector = "selector"

        assert (
            str(e.value)
            == "The class attribute 'selector' is reserved for the ItemLoader class, please choose a different name."
        )

    def test_prepare_process_value_raises(self):
        with pytest.raises(ValueError) as e:

            class SomeProcessor(Processor):
                def process_value(self, value, extra_arg, **context):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature `SomeProcessor.process_value(self, value, extra_arg, **context)`. "
                "`SomeProcessor.process_value(self, value, **context)` is the only valid signature."
            )
        )

        with pytest.raises(TypeError) as e:

            class SomeProcessor(Processor):
                def process_value(self, *, value, **context):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature `SomeProcessor.process_value(self, *, value, **context)`. "
                "The first parameter must be positional, not KEYWORD_ONLY."
            )
        )

        with pytest.raises(TypeError) as e:

            class SomeProcessor(Processor):
                def process_value(self, value, context):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature `SomeProcessor.process_value(self, value, context)`. "
                "There must be a variable length keyword parameter. "
                "Typically named `context`, declared as **context."
            )
        )

    def test_prepare_dunder_call_raises(self):
        with pytest.raises(ValueError) as e:
            # Too many parameters
            class SomeProcess(Processor):
                def __call__(self, values, extra_arg, **loader_context):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature `SomeProcess.__call__(self, values, extra_arg, **loader_context)`. "
                "`SomeProcess__call__(self, values, **loader_context)` is the only valid signature."
            )
        )

        with pytest.raises(TypeError) as e:

            class SomeProcessor(Processor):
                # values not positional
                def __call__(self, *, values, loader_context):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature `SomeProcessor.__call__(self, *, values, loader_context)`. "
                "The first parameter must be positional, not KEYWORD_ONLY."
            )
        )

        with pytest.raises(TypeError) as e:
            # loader_context not keyword
            class SomeProcessor(Processor):
                def __call__(self, values, context):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature `SomeProcessor.__call__(self, values, context)`. "
                "The second parameter must be a variable length keyword parameter "
                "(typically named `loader_context`), not POSITIONAL_OR_KEYWORD with name `context`."
            )
        )

    def test__init__(self, processor):
        """
        If the signatures of process_value and __call__ are valid
        verify the applied decorators are working.
        """

        value, context = processor.process_value(1, **{"a": 10})
        assert value == 1
        assert dict(context) == {"a": 10, "b": 2, "c": 3}

        values, loader_context = processor("some value", **{"a": 10})
        assert values == ["some value"]
        assert dict(loader_context) == {"a": 10, "b": 2, "c": 3}

    def test__init__raises(self):
        with pytest.raises(TypeError) as e:

            class SomeProcessor(Processor):
                def __init__(self):
                    ...

        assert str(e.value) == (
            "SomeProcessor class should not define __init__. "
            "The __init__ method is reserved for the ProcessorMeta metaclass. "
            "It takes the arguments passed to the Processor subclass's constructor "
            "and uses them to update the default_context attr."
        )

    def test__call__(self, processor_cls):
        assert processor_cls().default_context == {"a": 1, "b": 2, "c": 3}
        assert processor_cls(
            10, c=30, z="Not in default_context keys"
        ).default_context == {
            "a": 10,
            "b": 2,
            "c": 30,
            "z": "Not in default_context keys",
        }


class TestProcessorCollectionMeta:
    # __new__ & prepare_dunder_call are the same as ProcessorMeta

    def test__init__(self, processor_collection):
        """
        If the signature of __call__ is valid
        verify the applied decorators are working.
        """
        values, wrapped_processors, loader_context = processor_collection(
            "some value", **{"a": 10}
        )
        assert values == ["some value"]
        assert str(wrapped_processors) == str(tuple())
        assert dict(loader_context) == {"a": 10, "b": 2, "c": 3}

    def test__init__raises(self):
        with pytest.raises(TypeError) as e:

            class SomeProcessorCollection(ProcessorCollection):
                def __init__(self):
                    ...

        assert str(e.value) == (
            "SomeProcessorCollection class should not define __init__. "
            "The __init__ method is reserved for the ProcessorCollectionMeta metaclass. "
            "The variable length positional arguments passed to the constructor "
            "become the instance's processors. The variable length keyword arguments "
            "are used to update the instance's default_context attr."
        )

    def test_prepare_dunder_call_raises(self):
        with pytest.raises(ValueError) as e:

            class SomeProcessorCollection(ProcessorCollection):
                def __call__(
                    self, values, extra_arg, *wrapped_processors, **loader_context
                ):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature "
                "`SomeProcessorCollection.__call__(self, values, extra_arg, *wrapped_processors, **loader_context)`. "
                "`SomeProcessorCollection.__call__(self, values, *wrapped_processors, **loader_context)` "
                "is the only valid signature."
            )
        )

        # values will have to be positional, since we have *wrapped_processors

        with pytest.raises(TypeError) as e:
            # wrapped_processors not variable positional
            class SomeProcessorCollection(ProcessorCollection):
                def __call__(self, values, *, wrapped_processors, loader_context):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature "
                "`SomeProcessorCollection.__call__(self, values, *, wrapped_processors, loader_context)`. "
                "The second parameter must be a variable length positional parameter "
                "(typically named `wrapped_processors`), not KEYWORD_ONLY."
            )
        )

        with pytest.raises(TypeError) as e:
            # loader_context not variable keyword
            class SomeProcessorCollection(ProcessorCollection):
                def __call__(self, values, *wrapped_processors, loader_context):
                    pass

        assert single_space(e.value) == single_space(
            (
                "Invalid signature "
                "`SomeProcessorCollection.__call__(self, values, *wrapped_processors, loader_context)`. "
                "The third parameter must be a variable length keyword parameter "
                "(typically named `loader_context`), not VAR_POSITIONAL."
            )
        )

    def test__call__(self, processor_collection_cls):
        upper_processor = str.upper

        def reverse(value):
            return value[::-1]

        processor = processor_collection_cls(
            upper_processor, reverse, a=10, c=30, z="Not in default_context keys"
        )
        assert processor.processors == [upper_processor, reverse]
        assert processor.default_context == {
            "a": 10,
            "b": 2,
            "c": 30,
            "z": "Not in default_context keys",
        }


class TestContextMixin:
    def test_cls_name(self, processor):
        assert processor.cls_name == "SomeProcessor"

    @pytest.mark.parametrize(
        "additional_keys, context, expected_output",
        [
            ((), {}, (1, 2, 3)),  # no context
            ((), {"a": 10}, (10, 2, 3)),  # context overrides default_context
            (("d",), {"d": 40}, (1, 2, 3, 40)),  # additional keys
        ],
    )
    def test_unpacked_context(
        self, processor, additional_keys, context, expected_output
    ):
        assert processor.unpack_context(*additional_keys, **context) == expected_output

    def test_unpack_context_single_value(self):
        # single value should be returned as a single value, not a tuple
        class SomeOtherProcessor(Processor):
            z = 10

        assert SomeOtherProcessor().unpack_context() == 10

    def test_call_with_context(self, processor):
        class SomeClass:
            def __init__(self, a):
                self.a = a

            def __eq__(self, other):
                return self.a == other.a

        assert processor.call_with_context(SomeClass, **{"a": 100}) == SomeClass(100)

        def a_func(a):
            return a

        def bc_func(b, c):
            return b, c

        assert processor.call_with_context(a_func, **{"a": 100}) == 100
        assert processor.call_with_context(bc_func, **{"b": 200}) == (200, 3)


class TestProcessor:
    def test_process_value_NotImplementedError(self):
        processor = Processor()
        with pytest.raises(NotImplementedError):
            processor.process_value("value")

    def test__call__(self):
        """
        Make sure it can call process_value with a context or without context.
        """

        class SomeProcessor(Processor):
            def process_value(self, value, **context):
                return f"{value} processed."

        processor = SomeProcessor()
        assert processor(["value1", "value2", "value3"]) == [
            "value1 processed.",
            "value2 processed.",
            "value3 processed.",
        ]

    def test__str__(self, processor):
        assert str(processor) == "SomeProcessor(a=1, b=2, c=3)"

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
            ProcessorCollection(str.lower).__call__(1)

    def test_extend(self, lower_processor, upper_processor, title_processor):
        # Test with an iterable
        processor = ProcessorCollection(lower_processor, a=100)
        new_processor = processor.extend((upper_processor, title_processor))
        assert new_processor.processors == [
            lower_processor,
            upper_processor,
            title_processor,
        ]

        # Test with a ProcessorCollection, can merge default_context
        processor_II = ProcessorCollection(upper_processor, title_processor, a=100)
        new_processor = processor.extend(processor_II)
        assert new_processor.processors == [
            lower_processor,
            upper_processor,
            title_processor,
        ]

        # Test with a ProcessorCollection, cannot merge default_context
        processor_III = ProcessorCollection(upper_processor, title_processor, a=10)
        with pytest.raises(ValueError) as e:
            processor.extend(processor_III)
        assert str(e.value) == (
            "Cannot call `extend` method on ProcessorCollection instance with ProcessorCollection instance. "
            "Shared keys in default_context attrs have different values. "
            "Key: a, self: 100, other: 10"
        )

    def test__add__(
        self,
        processor_collection_cls,
        lower_processor,
        upper_processor,
        strip_processor,
    ):
        processor = processor_collection_cls(lower_processor, strip_processor)

        # Add single function
        result = processor + upper_processor
        assert isinstance(result, processor_collection_cls)
        assert result.processors == [lower_processor, strip_processor, upper_processor]

        # Add collection of functions
        result = processor + (upper_processor, strip_processor)
        assert isinstance(result, processor_collection_cls)
        assert result.processors == [
            lower_processor,
            strip_processor,
            upper_processor,
            strip_processor,
        ]

        # Adding a ProcessorCollection to a ProcessorCollection is the same as extend

    def test__str__(self, reverse_processor_collection, processor):
        assert (
            str(reverse_processor_collection) == "ProcessorCollection(lambda_processor)"
        )

        processor = reverse_processor_collection + (
            processor,
            str.upper,
            lambda x: x.strip(),
        )
        assert (
            str(processor)
            == "ProcessorCollection(lambda_processor, SomeProcessor(a=1, b=2, c=3), str.upper, lambda_processor)"
        )

    def test__eq__(self):
        processor = ProcessorCollection(str.lower, a=10)

        assert processor == ProcessorCollection(str.lower, a=10)

        assert processor != ProcessorCollection(str.lower, a=100)
        assert processor != ProcessorCollection(str.upper)

    def test__getattr__(self, upper_processor, strip_processor):
        processor = ProcessorCollection(upper_processor, strip_processor)

        assert len(processor.processors) == 2

        new_processor = processor.clear()
        assert len(processor.processors) == 2
        assert len(new_processor.processors) == 0
