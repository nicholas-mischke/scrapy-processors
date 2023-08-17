import pytest

from scrapy_processors.multi_values import (
    TakeAll,
    TakeAllTruthy,
    TakeFirst,
    TakeFirstTruthy,
    Coalesce,
    Join,
    Flatten,
)


def test_take_all():
    processor = TakeAll()
    assert processor([1, 2, 3]) == [1, 2, 3]
    assert processor("apple") == "apple"


class TestTakeAllTruthy:
    @pytest.fixture
    def processor(self):
        return TakeAllTruthy(default=[])

    @pytest.mark.parametrize(
        "input_values, expected_output",
        [
            ([True, 123, "abc", [1, 2, 3]], [True, 123, "abc", [1, 2, 3]]),
            ([None, False, "", [], 0], []),
            ([0, "", False, 7, [], None, "empty"], [7, "empty"]),
            ([], []),
        ],
    )
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output


class TestTakeFirst:
    @pytest.fixture
    def processor(self):
        return TakeFirst()

    @pytest.mark.parametrize(
        "input_values, expected_output",
        [([1, 2, 3], 1), ("apple", "apple"), ([None, "", 10], 10)],
    )
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output


class TestTakeFirstTruthy:
    @pytest.fixture
    def processor(self):
        return TakeFirstTruthy(default=None)

    @pytest.mark.parametrize(
        "input_values, expected_output",
        [
            ([True, 123, "abc", [1, 2, 3]], True),
            ([None, False, "", [], 7], 7),
            ([0, "", False, "empty", [], None], "empty"),
            ([], None),
        ],
    )
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output


class TestCoalesce:
    @pytest.fixture
    def processor(self):
        return Coalesce()

    @pytest.mark.parametrize(
        "input_values, expected_output",
        [([None, False, "", [], 0], False), ([None, None, "Hello"], "Hello")],
    )
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output


class TestJoin:
    @pytest.fixture
    def processor(self):
        return Join()

    @pytest.mark.parametrize(
        "input_values, expected_output",
        [
            ([1, 2, 3], "1 2 3"),
        ],
    )
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output

    @pytest.mark.parametrize(
        "input_values, context, expected_output",
        [
            ([1, 2, 3], {"separator": " - "}, "1 - 2 - 3"),
        ],
    )
    def test_with_context(self, processor, input_values, context, expected_output):
        assert processor(input_values, context) == expected_output


class TestFlatten:
    @pytest.fixture
    def processor(self):
        return Flatten()

    @pytest.mark.parametrize(
        "input_values, expected_output",
        [
            ([[1, 2, 3], [4, 5, 6]], [1, 2, 3, 4, 5, 6]),
        ],
    )
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output
