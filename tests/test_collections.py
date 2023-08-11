import pytest
from scrapy_processors.collections import *


class TestMapCompose:

    @pytest.fixture
    def reverse_upper_processor(self, reverse_processor, upper_processor):
        return MapCompose(reverse_processor, upper_processor)

    @pytest.fixture
    def lower_processor(self, lower_processor):
        return MapCompose(lower_processor)

    @pytest.fixture
    def clean_processor(self, strip_processor, title_processor):
        return MapCompose(strip_processor, title_processor)

    @pytest.mark.parametrize("input_values, expected_reverse_upper, expected_lower, expected_clean", [
        (
        "  `Tis but a single value  ",
        ["  EULAV ELGNIS A TUB SIT`  "], ["  `tis but a single value  "], ["`Tis But A Single Value"]
        ),
        (["hello", "world  "],
         ["OLLEH", "  DLROW"], ["hello", "world  "], ["Hello", "World"]),

        (["apPlE", "baNAna"],
         ["ELPPA", "ANANAB"], ["apple", "banana"], ["Apple", "Banana"]),

        (["this is a string", "this is another string"],
         ["GNIRTS A SI SIHT", "GNIRTS REHTONA SI SIHT"],
         ["this is a string", "this is another string"],
         ["This Is A String", "This Is Another String"]),
    ])
    def test(
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


class TestCompose:

    @pytest.fixture
    def len_of_last_element_processor(
        self,
        reverse_processor,
        get_first_processor,
        get_length_processor
    ):
        return Compose(
            reverse_processor,
            get_first_processor,
            get_length_processor
        )

    @pytest.fixture
    def filter_out_world_processor(self):
        return Compose(lambda x: [_ for _ in x if _ != "world"])

    @pytest.mark.parametrize(
        (
            "input_values, "
            "expected_len_of_last_element, "
            "expected_filter_out_world"
        ),
        [
            (
                ["hello", "world"],
                5,
                ["hello"]
            ),
            (
                ["apple", "banana", "cherry", "world", "zucchini"],
                8,
                ["apple", "banana", "cherry", "zucchini"],
            ),
    ])
    def test(
        self,
        len_of_last_element_processor,
        filter_out_world_processor,
        input_values,
        expected_len_of_last_element,
        expected_filter_out_world
    ):
        assert len_of_last_element_processor(input_values) \
            == expected_len_of_last_element
        assert filter_out_world_processor(input_values) \
            == expected_filter_out_world