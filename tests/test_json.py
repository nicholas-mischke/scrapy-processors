
import pytest
from scrapy_processors.json import *


class TestSelectJmes:

    @pytest.fixture
    def processor(self):
        return SelectJmes('foo')

    @pytest.mark.parametrize("input_values, expected_output", [
        (
            {'foo': 'bar'},
            'bar'
        ),
        (
            {'foo': {'bar': 'baz'}},
            {'bar': 'baz'}
        ),
        (
            {'foo': [{'bar': 'baz'}, {'bar': 'tar'}]},
            [{'bar': 'baz'}, {'bar': 'tar'}]
        ),
    ])
    def test(self, processor, input_values, expected_output):
        assert processor(input_values)[0] == expected_output

    def test_with_loader_context(self):
        processor = SelectJmes('foo.bar')
        assert processor({'foo': {'bar': 'baz'}})[0] == 'baz'
        
        assert processor(
            values = {'bar': {'bar': 'baz'}},
            loader_context = {'search_string': 'bar'}
        )[0] == {'bar': 'baz'}
            
        