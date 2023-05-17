
# Standard library imports
import re
from datetime import datetime
from inspect import isclass, isfunction, ismethod

# itemloaders imports
from itemloaders.processors import Identity
from itemloaders.processors import MapCompose as BuiltInMapCompose
from itemloaders.utils import arg_to_iter

# 3rd 🎉 imports
import emoji
from bs4 import BeautifulSoup
from price_parser import Price


class MapCompose(BuiltInMapCompose):
    """
    This class overwrites the built-in MapCompose class constructor 
    to allow for passing of classes, class instances, and callables 
    to the constructor.
    """

    def __init__(self, *callables, **default_loader_context):
        self.default_loader_context = default_loader_context

        functions = []
        for callable in callables:
            if (
                isfunction(callable)
                or ismethod(callable)
            ):
                functions.append(callable)
            elif isclass(callable):
                functions.append(callable().__call__)
            elif hasattr(callable, '__call__'):
                functions.append(callable.__call__)
        self.functions = tuple(functions)


class Processor:

    def process_value(self, value):
        raise NotImplementedError()

    def __call__(self, values):
        values = arg_to_iter(values)
        return [self.process_value(value) for value in values]


class EnsureEncoding(Processor):
    """
    Given a string, return a string with the specified encoding.
    """

    def __init__(self, encoding='utf-8', ignore=True):
        self.encoding = encoding
        self.ignore = ignore

    def process_value(self, value):
        return str(value) \
            .encode(self.encoding, "ignore" if self.ignore else "strict") \
            .decode(self.encoding)


class NormalizeWhitespace(Processor):
    """
    Given a string, return a string with all whitespace normalized.

    Normalizing whitespace includes 4 steps:
        1) Remove zero-width spaces
        2) Replace multiple whitespaces with single whitespace
        3) Remove leading whitespaces from punctuation
        4) Remove leading and trailing whitespaces

    Assumes utf8, utf16, ascii or latin-1 encoding.
    """

    def __init__(self, punctuation=(',', '.', '!', '?', ';', ':')):
        self.punctuation = punctuation

    def process_value(self, value):
        # Step 1) Remove zero-width spaces
        value = re.sub(r'[\u200b\ufeff]', '', value)

        # Step 2) Replace multiple whitespaces with single whitespace
        value = re.sub(r'\s+', ' ', value)

        # Step 3) Remove leading whitespaces from punctuation
        # Construct the regular expression pattern dynamically
        pattern = r'\s*([' + re.escape(''.join(self.punctuation)) + r'])'

        # Remove leading whitespaces from punctuation marks
        value = re.sub(pattern, r'\1', value)

        # Step 4) Remove leading and trailing whitespaces
        return value.strip()


class PriceParser(Processor):
    """
    Given a string representing a price, return a price_parser.Price object.
    """

    def process_value(self, value):
        return Price.fromstring(value)


class RemoveHTMLTags(Processor):
    """
    Given a string, return a string with all HTML tags removed.
    """

    def process_value(self, value):
        return BeautifulSoup(value, "html.parser").get_text()


class Demojize(Processor):
    """
    Replace Unicode emoji in a string with emoji shortcodes. Useful for storage.
    Accepts delimiters, language, version, handle_version as keyword arguments
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def process_value(self, value):
        return emoji.demojize(value, **self.kwargs)


class RemoveEmojis(Processor):
    """
    Given a string, return a string with all emojis removed.
    Accepts replace and version as keyword arguments
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def process_value(self, value):
        return emoji.replace_emoji(value, **self.kwargs)


class StripQuotes(Processor):
    """
    Given a string, return a string with all leading and trailing quotes/tick marks removed.
    Assumes utf8, utf16, ascii or latin-1 encoding.
    """

    pattern = r'^[`ˋ‘’“”\'"\u0060\u02CB\x91\x92\x93\x94]+|[`ˋ‘’“”\'"\u0060\u02CB\x91\x92\x93\x94]+$'

    def process_value(self, value):
        return re.sub(self.pattern, '', value)


class StringToDateTime(Processor):
    """
    Given a string representing a date and time, return a datetime object.
    """

    def __init__(self, format='%Y-%m-%d, %H:%M:%S'):
        self.format = format

    def process_value(self, value):
        return datetime.strptime(value, self.format)


class StringToDate(Processor):
    """
    Given a string representing a date, return a date object.
    """

    def __init__(self, format='%Y-%m-%d'):
        self.format = format

    def process_value(self, value):
        return datetime.strptime(value, self.format).date()


class StringToTime(Processor):
    """
    Given a string representing a time, return a time object.
    """

    def __init__(self, format='%H:%M:%S'):
        self.format = format

    def process_value(self, value):
        return datetime.strptime(value, self.format).time()


class TakeAll(Identity):
    """
    Renaming of the built-in `Identity` processor.
    """
    pass


class TakeAllTruthy:
    """
    Return all values passed to this processor that are truthy.
    If no values are truthy, return default parameter passed to constructor.
    """

    def __init__(self, default=None):
        self.default = default

    def __call__(self, values):
        values = arg_to_iter(values)
        return [value for value in values if value] or self.default
