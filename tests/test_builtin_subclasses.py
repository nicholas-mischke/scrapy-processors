
import pytest
from itemloaders import Identity
from scrapy_processors.builtin_subclasses import Compose, MapCompose, TakeAll


# Generic callables on objs in a list
def str_upper(value):
    return value.upper()


def str_reverse(value):
    return value[::-1]


class TestMapCompose:

    @pytest.fixture
    def reverse_upper_processor(self):
        return MapCompose(lambda x: x[::-1], str.upper)

    @pytest.fixture
    def lower_processor(self):
        return MapCompose(str.lower)

    @pytest.fixture
    def clean_processor(self):
        return MapCompose(str.strip, str.title)

    @pytest.mark.parametrize("input_values, expected_reverse_upper, expected_lower, expected_clean", [
        (["hello", "world  "],
         ["OLLEH", "  DLROW"], ["hello", "world  "], ["Hello", "World"]),

        (["apPlE", "baNAna"],
         ["ELPPA", "ANANAB"], ["apple", "banana"], ["Apple", "Banana"]),

        (["this is a string", "this is another string"],
         ["GNIRTS A SI SIHT", "GNIRTS REHTONA SI SIHT"],
         ["this is a string", "this is another string"],
         ["This Is A String", "This Is Another String"]),
    ])
    def test_process_value(
        self,
        reverse_upper_processor,
        lower_processor,
        clean_processor,
        input_values,
        expected_reverse_upper,
        expected_lower,
        expected_clean
    ):
        assert reverse_upper_processor(input_values) == expected_reverse_upper
        assert lower_processor(input_values) == expected_lower
        assert clean_processor(input_values) == expected_clean

    def test__add__(self):
        map1 = MapCompose(str_upper, foo='bar')
        map2 = MapCompose(str_reverse, foo='bar')
        map3 = MapCompose(str_reverse, foo='baz')
        callable = str_reverse
        non_callable = 'some string'

        # Add two MapCompose objects
        result = map1 + map2
        assert isinstance(result, MapCompose)
        assert result.functions == (str_upper, str_reverse)
        assert result.default_loader_context == {'foo': 'bar'}

        # Add two MapCompose objects with different loader_context
        with pytest.raises(ValueError) as error:
            result = map1 + map3
        assert str(error.value) == (
            "Cannot add Compose or MapCompose objects with mismatched "
            "key, value pairs in their default_loader_context\n"
            "Key: foo, self[foo]: bar, other[foo]: baz"
        )

        # Add MapCompose object with callable
        result = map1 + callable
        assert isinstance(result, MapCompose)
        assert result.functions == (str_upper, str_reverse)
        assert result.default_loader_context == {'foo': 'bar'}

        # Add MapCompose object with non-callable
        with pytest.raises(TypeError) as error:
            result = map1 + non_callable
        assert str(error.value) == (
            "Unsupported operand type for +: 'MapCompose' and 'str'"
        )


# Generic callables on a list obj
def get_length(list_obj):
    return len(list_obj)


def get_first(list_obj):
    return list_obj[0]


class TestCompose:

    @pytest.fixture
    def filter_out_world(self):
        def func(list_obj):
            return [word for word in list_obj if word.lower().strip() != "world"]

        return Compose(func)

    @pytest.fixture
    def sort_processor(self):
        return Compose(sorted)

    @pytest.fixture
    def reverse_sort_and_capitalized_processor(self):
        def revrese_it(list_obj):
            return sorted(list_obj, reverse=True)

        def upper_it(list_obj):
            return [word.upper() for word in list_obj]

        return Compose(revrese_it, upper_it)

    @pytest.mark.parametrize(
        (
            "input_values, "
            "expected_filter_out_world, expected_sort_processor, "
            "expected_reverse_sort_and_capitalized_processor"
        ),
        [
            (
                ["hello", "world"],
                ["hello"], ["hello", "world"], ["WORLD", "HELLO"]
            ),
            (
                ["apple", "banana", "cherry", "world", "zucchini"],
                ["apple", "banana", "cherry", "zucchini"], 
                ["apple", "banana", "cherry", "world", "zucchini"], 
                ["ZUCCHINI", "WORLD", "CHERRY", "BANANA", "APPLE"]
            ),
        ])
    def test_process_value(
        self,
        filter_out_world,
        sort_processor,
        reverse_sort_and_capitalized_processor,
        input_values,
        expected_filter_out_world, 
        expected_sort_processor, 
        expected_reverse_sort_and_capitalized_processor
    ):
        assert filter_out_world(input_values) == expected_filter_out_world
        assert sort_processor(input_values) == expected_sort_processor
        assert reverse_sort_and_capitalized_processor(input_values) == \
            expected_reverse_sort_and_capitalized_processor

    def test__add__(self):
        compose1 = Compose(get_first, foo='bar')
        compose2 = Compose(get_length, foo='bar')
        compose3 = Compose(get_length, foo='baz')
        callable = get_length
        non_callable = 'some string'

        # Add two Compose objects
        result = compose1 + compose2
        assert isinstance(result, Compose)
        assert result.functions == (get_first, get_length)
        assert result.default_loader_context == {'foo': 'bar'}

        # Add two Compose objects with different loader_context
        with pytest.raises(ValueError) as error:
            result = compose1 + compose3
        assert str(error.value) == (
            "Cannot add Compose or MapCompose objects with mismatched "
            "key, value pairs in their default_loader_context\n"
            "Key: foo, self[foo]: bar, other[foo]: baz"
        )

        # Add Compose object with callable
        result = compose1 + callable
        assert isinstance(result, Compose)
        assert result.functions == (get_first, get_length)
        assert result.default_loader_context == {'foo': 'bar'}

        # Add Compose object with non-callable
        with pytest.raises(TypeError) as error:
            result = compose1 + non_callable
        assert str(error.value) == (
            "Unsupported operand type for +: 'Compose' and 'str'"
        )


def test_TakeAll():
    assert isinstance(TakeAll(), Identity)
