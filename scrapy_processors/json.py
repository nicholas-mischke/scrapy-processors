
# Standard library imports
from typing import Any, List, Mapping, Optional, Union

# 3rd 🎉 imports
import jmespath

# Local application/library specific imports
from scrapy_processors.base import Processor


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
    ) -> Any:

        search_string = self.unpack_context(context)
        return jmespath.search(search_string, value)
