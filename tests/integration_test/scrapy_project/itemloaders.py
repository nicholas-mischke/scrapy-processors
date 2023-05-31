
from itemloaders import ItemLoader
import json
import pytz

from scrapy_processors import (
    StringToDateTime, TakeFirstTruthy, MapCompose,
    SelectJmes, NormalizeNumericString, PriceParser,
    UnicodeEscape, StripQuotes, NormalizeWhitespace
)


class DateTimeItemLoader(ItemLoader):
    default_input_processor = StringToDateTime(input_tz=pytz.UTC)
    default_output_processor = TakeFirstTruthy()


class NumericStringItemLoader(ItemLoader):
    default_input_processor = NormalizeNumericString()
    default_output_processor = TakeFirstTruthy()


class PriceItemLoader(ItemLoader):
    default_input_processor = PriceParser()
    default_output_processor = TakeFirstTruthy()


clean_text = MapCompose(
    UnicodeEscape(),  # convert unicode escape sequences to unicode characters
    str.strip,  # remove leading and trailing whitespace
    StripQuotes(),  # remove leading and trailing quotes
    NormalizeWhitespace(),  # replace multiple whitespace with a single space
)


class TextItemLoader(ItemLoader):
    # Adding a processor to MapCompose will return a new instance of MapCompose
    default_input_processor = clean_text + str.capitalize
    default_output_processor = TakeFirstTruthy()


select_jmes = MapCompose(
    json.loads,  # convert string to dict
    SelectJmes('foo')
)


class JsonItemLoader(ItemLoader):
    default_input_processor = select_jmes
    default_output_processor = TakeFirstTruthy()


class JsonItemLoader2(ItemLoader):
    # Can replace a processor at a specific index and return a new instance of MapCompose
    # Adding two MapCompose together and an additional processor func.
    # Returns new instance of MapCompose
    default_input_processor = select_jmes.replace_processor(
        1, SelectJmes('name')
    ) + clean_text + str.title

    default_output_processor = TakeFirstTruthy()
