import pytest

from scrapy_processors.base import InValidSignatureException
from scrapy_processors.base import wrap_context, chainmap_context
from scrapy_processors.base import Processor, ProcessorCollection


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

        def __call__(self, values, **loader_context):
            return values, self.wrapped_processors, loader_context

    return SomeProcessorCollection


@pytest.fixture
def processor_collection(processor_collection_cls):
    return processor_collection_cls()


@pytest.fixture
def reverse_processor_collection(reverse_processor):
    return ProcessorCollection(reverse_processor)


def test_wrap_context():
    assert wrap_context(lambda value: value)(1) == 1

    def context(value, context):
        return value, context

    assert wrap_context(context, **{"a": 1})(1) == (1, {"a": 1})

    def context(value, **context):
        return value, context

    assert wrap_context(context, **{"a": 1})(1) == (1, {"a": 1})

    def loader_context(value, loader_context):
        return value, loader_context

    assert wrap_context(loader_context, **{"a": 1})(1) == (1, {"a": 1})

    def loader_context(value, **loader_context):
        return value, loader_context

    assert wrap_context(loader_context, **{"a": 1})(1) == (1, {"a": 1})


def test_chainmap_context():
    class SomeClass:
        def __init__(self):
            self.default_context = {"a": 1, "b": 2, "c": 3}

        @chainmap_context
        def some_method(self, value, **context):
            return context

    some_obj = SomeClass()
    assert some_obj.some_method(1, **{"a": 10}) == {"a": 10, "b": 2, "c": 3}


class TestProcessorMeta:
    # Tests MetaMixin __new__, so no need to repeat these tests for ProcessorCollectionMeta
    def test__new__(self, processor):
        assert processor.default_context == {"a": 1, "b": 2, "c": 3}
        assert not hasattr(processor, "a")

    def test__new__raises(self):
        with pytest.raises(ValueError) as e:
            # item is reserved attr for ItemLoader context attr
            class SomeProcessor(Processor):
                item = "item"

    def test_validate_method_signature(self):
        with pytest.raises(InValidSignatureException) as e:

            class TooManyParams(Processor):
                def process_value(self, value, extra_arg, **context):
                    pass

        with pytest.raises(InValidSignatureException) as e:

            class NotPositional(Processor):
                def process_value(self, *, value, **context):
                    pass

        with pytest.raises(InValidSignatureException) as e:

            class NotVariableLength(Processor):
                def process_value(self, value, context):
                    pass

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
            # Cannot define __init__ in subclasses.
            class SomeProcessor(Processor):
                def __init__(self):
                    ...

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
        assert wrapped_processors == tuple()
        assert dict(loader_context) == {"a": 10, "b": 2, "c": 3}

    def test__init__raises(self):
        with pytest.raises(TypeError) as e:
            # Cannot define __init__ in subclasses.
            class SomeProcessorCollection(ProcessorCollection):
                def __init__(self):
                    ...

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

    def test_wrap_with_context(self, processor):
        def func(value, a, b, c):
            return value, a, b, c

        wrapped_func = processor.wrap_with_context(func)
        assert wrapped_func("value") == ("value", 1, 2, 3)


class TestProcessor:
    def test_process_value_NotImplementedError(self):
        processor = Processor()
        with pytest.raises(NotImplementedError):
            processor.process_value("value")

    def test__call__(self):
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

    def test_merge_default_context(self):
        class Processor(ProcessorCollection):
            a, b, c = 1, 2, 3

        class OtherProcessorI(ProcessorCollection):
            a = 1

        class OtherProcessorII(ProcessorCollection):
            a = 10

        processor = Processor()
        other_I = OtherProcessorI()
        other_II = OtherProcessorII()

        assert processor._merge_default_context(other_I) == {"a": 1, "b": 2, "c": 3}

        with pytest.raises(ValueError):
            processor._merge_default_context(other_II)

    def test_extend(self, lower_processor, upper_processor, title_processor):
        # Test with an iterable
        processor = ProcessorCollection(lower_processor, a=100)

        new_processor = processor.extend((upper_processor, title_processor))
        assert processor.processors == [lower_processor]  # original processor unchanged
        assert new_processor.processors == [
            lower_processor,
            upper_processor,
            title_processor,
        ]

        # Test with a ProcessorCollection, can merge default_context
        processor_II = ProcessorCollection(upper_processor, title_processor, a=100)

        new_processor = processor.extend(processor_II)
        assert processor.processors == [lower_processor]  # original processor unchanged
        assert new_processor.processors == [
            lower_processor,
            upper_processor,
            title_processor,
        ]

        # Test with a ProcessorCollection, cannot merge default_context
        processor_III = ProcessorCollection(upper_processor, title_processor, a=10)
        with pytest.raises(ValueError) as e:
            processor.extend(processor_III)

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
        assert processor.processors == [
            lower_processor,
            strip_processor,
        ]  # original processor unchanged
        assert result.processors == [lower_processor, strip_processor, upper_processor]

        # Add collection of functions
        result = processor + (upper_processor, strip_processor)
        assert isinstance(result, processor_collection_cls)
        assert processor.processors == [
            lower_processor,
            strip_processor,
        ]  # original processor unchanged
        assert result.processors == [
            lower_processor,
            strip_processor,
            upper_processor,
            strip_processor,
        ]

        # Adding a ProcessorCollection to a ProcessorCollection
        processor_II = processor_collection_cls(upper_processor, strip_processor)
        result = processor + processor_II
        assert isinstance(result, processor_collection_cls)
        assert processor.processors == [
            lower_processor,
            strip_processor,
        ]
        assert result.processors == [
            lower_processor,
            strip_processor,
            processor_II
        ]

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

    def test__eq__(self, lower_processor, upper_processor):
        processor = ProcessorCollection(lower_processor, a=10)

        # same type, same processors, same default_context
        assert processor == ProcessorCollection(lower_processor, a=10)
        # different default_context
        assert processor != ProcessorCollection(lower_processor, a=100)
        # different processors
        assert processor != ProcessorCollection(upper_processor, a=10)

    def test__getattr__(self, upper_processor, strip_processor):
        processor = ProcessorCollection(upper_processor, strip_processor)

        # non-mutating methods returns the value
        assert len(processor.processors) == 2

        # mutating methods returns a new ProcessorCollection
        new_processor = processor.clear()
        assert len(processor.processors) == 2
        assert len(new_processor.processors) == 0


if __name__ == "__main__":
    pytest.main(["pytest", "-k", "test_validate_method_signature"])
