
from scrapy_processors.base import Processor, ProcessorCollection
from scrapy_processors.collections import Compose, MapCompose

from scrapy_processors.single_value import (
    # ... Strings ...
    UnicodeEscape,
    NormalizeWhitespace,
    CharWhitespacePadding,
    StripQuotes,
    RemoveHTMLTags,
    Demojize,
    RemoveEmojis,
    # ... Numeric / Numeric Strings ...
    ExtractDigits,
    NormalizeNumericString,
    PriceParser,
    ToFloat,
    # ... Dates & Time ...
    DateTimeExtraordinaire,
    DateTime,
    Date,
    Time,
    # ... Contact ...
    Emails,
    PhoneNumbers,
    Socials,
    # ... Misc ...
    SelectJmes
)
from scrapy_processors.multi_values import (
    TakeAll,
    TakeAllTruthy,
    TakeFirst,
    TakeFirstTruthy,
    Coalesce,
    Join,
    Flatten
)

# Clean scraped strings
clean_string = MapCompose(
    UnicodeEscape(),
    RemoveHTMLTags(),
    str.strip,
    StripQuotes(),
    NormalizeWhitespace(),
)
