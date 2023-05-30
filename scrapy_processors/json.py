
from typing import Any, Tuple, Iterable, Union, Optional, Mapping, List
from pathlib import Path

from itemloaders.processors import Identity

from scrapy_processors import common
from scrapy_processors.common import V
from scrapy_processors.base import Processor

import jmespath


class SelectJmes(Processor):
    """
    processor = SelectJmes('foo') <-- Find foo in a value that's a dict, or list of dicts
    SelectJmes({'foo': 'bar'}) --> 'bar'
    """

    search_string: str = None
    
    def process_value(
        self, 
        value: Union[Mapping[str, Any], List[Mapping[str, Any]]],
        context: Optional[Mapping[str, Any]] = None
    )-> Any:

        search_string = self.unpack_context(context)
        return jmespath.search(search_string, value)


