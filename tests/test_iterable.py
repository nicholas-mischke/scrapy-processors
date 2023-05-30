
import pytest

from itemloaders.processors import Identity
from scrapy_processors.iterable import *


class TestTakeAll:

    def test(self):
        assert isinstance(TakeAll(), Identity)


class TestTakeAllTruthy:

    @pytest.fixture
    def processor(self):
        return TakeAllTruthy(default=[])

    @pytest.mark.parametrize("input_values, expected_output", [
        (
            [True, 123, 'abc', [1, 2, 3]],
            [True, 123, 'abc', [1, 2, 3]]
        ),
        (
            [None, False, '', [], 0],
            []
        ),
        (
            [0, '', False, 7, [], None, 'empty'],
            [7, 'empty']
        ),
        ([], []),
    ])
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output


class TestTakeFirstTruthy:

    @pytest.fixture
    def processor(self):
        return TakeFirstTruthy(default=None)

    @pytest.mark.parametrize("input_values, expected_output", [
        ([True, 123, 'abc', [1, 2, 3]], True),
        ([None, False, '', [], 7], 7),
        ([0, '', False, 'empty', [], None], 'empty'),
        ([], None)
    ])
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output


class TestJoin:

    @pytest.fixture
    def processor(self):
        return Join()

    @pytest.mark.parametrize("input_values, expected_output", [
        (
            [1, 2, 3],
            '1 2 3'
        ),
    ])
    def test(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output

    @pytest.mark.parametrize("input_values, context, expected_output", [
        (
            [1, 2, 3],
            {'separator': ' - '},
            '1 - 2 - 3'
        ),
    ])
    def test_with_context(
        self,
        processor,
        input_values,
        context,
        expected_output
    ):
        assert processor(input_values, context) == expected_output
