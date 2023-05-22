
# Standard library imports
import re
from collections import ChainMap
from datetime import datetime

# 3rd 🎉 imports
import emoji
from bs4 import BeautifulSoup
from price_parser import Price

# itemloaders imports
from itemloaders.utils import arg_to_iter


class Processor:

    def process_value(self, value):
        raise NotImplementedError()

    def __call__(self, values):
        values = arg_to_iter(values)
        return [self.process_value(value) for value in values]


class ContextProcessor:

    def __init__(self, **default_loader_context):
        self.default_loader_context = default_loader_context

    def process_value(self, value, context=None):
        raise NotImplementedError()

    # The arg in the callable "loader_context" shouldn't be renamed.
    # It is used by the itemloaders library.
    def __call__(self, values, loader_context=None):
        values = arg_to_iter(values)

        if loader_context:
            context = ChainMap(loader_context, self.default_loader_context)
        else:
            context = self.default_loader_context

        return [
            self.process_value(value, context)
            for value in values
        ]


class EnsureEncoding(Processor):
    """
    Given a string, return a string with the specified encoding.
    """

    def __init__(self, encoding='utf-8', ignore=True):
        self.encoding = encoding
        self.ignore = ignore

    def process_value(self, value):
        return str(value) \
            .encode(
                self.encoding,
                errors="ignore" if self.ignore else "strict"
        ).decode(self.encoding)


class NormalizeWhitespace(Processor):
    """
    Given a string, return a string with all whitespace normalized.

    Normalizing whitespace includes 4 steps:
        1) Remove zero-width spaces
        2) Replace multiple whitespaces with single whitespace
        3) Normalize whitespace around punctuation marks
        4) Remove leading and trailing whitespaces

    Typically not fully appropriate for numerical strings.
    This is because in a sentences a commas and periods are typically followed by a space.
    In numbers a period they are not. Consider combining this processor with
    NormalizeNumericString, inside a MapCompose processor.

    Assumes utf8, utf16, ascii or latin-1 encoding.
    """

    # The class variables below are here more for readability than anything else
    # The default values used in the __init__ method are the same as the class variables
    # Just rewritten as tuples and flattened.
    punctuation_marks_no_space = [
        # Punctuation Characters That Typically Don't Have Whitespace Around Them
        '-',  # Hyphen-minus
        '/',  # Slash
        '_',  # Underscore
        '@',  # At sign
        '\\',  # Backslash
        '^',  # Circumflex accent
        '~',  # Tilde
    ]

    punctuation_marks_no_left_space = [
        # Punctuation Characters That Typically Don't Have Whitespace to Their Left
        '.',  # Period/Full stop
        ',',  # Comma
        '!',  # Exclamation mark
        '?',  # Question mark
        ')',  # Right parenthesis
        ']',  # Right square bracket
        '}',  # Right curly brace
        ':',  # Colon
        ';',  # Semicolon
        '%',  # Percent sign
        '\u2019',  # Right Single Quotation Mark ('’')
        '\u201D',  # Right Double Quotation Mark ('”')
        '\x92',    # Right Single Quotation Mark ('’')
        '\x94'     # Right Double Quotation Mark ('”')
    ]

    punctuation_marks_no_right_space = [
        # Punctuation Characters That Typically Don't Have Whitespace to Their Right
        '(',  # Left parenthesis
        '$',  # Dollar sign
        '[',  # Left square bracket
        '{',  # Left curly brace
        '#',  # Hash/Pound sign
        '\u2018',  # Left Single Quotation Mark ('‘')
        '\u201C',  # Left Double Quotation Mark ('“')
        '\x91',    # Left Single Quotation Mark ('‘')
        '\x93',    # Left Double Quotation Mark ('“')
    ]

    other_punctuation = [
        '*',  # Asterisk
        '&',  # Ampersand
        '|',  # Vertical bar

        # ASCII (difficult to know if they should be left or right stripped)
        '\x27',    # Apostrophe ("'")
        '\x22',    # Quotation Mark ('"')

        # Numerical ones
        '=',  # Equals sign
        '+',  # Plus sign
        '<',  # Less than sign
        '>',  # Greater than sign
    ]

    def __init__(
        self,
        lstrip_punctuation=('.', ',', '!', '?', ')', ']', '}',
                            ':', ';', '%', '\u2019', '\u201D', '\x92', '\x94'),
        rstrip_punctuation=(
            '(', '$', '[', '{', '#', '\u2018', '\u201C', '\x91', '\x93'),
        strip_punctuation=('-', '/', '_', '@', '\\', '^', '~')
    ):
        self.lstrip_punctuation = lstrip_punctuation
        self.rstrip_punctuation = rstrip_punctuation
        self.strip_punctuation = strip_punctuation

    def process_value(self, value):
        # Step 1) Remove zero-width spaces
        value = re.sub(r'[\u200b\ufeff]', '', value)

        # Step 2) Replace multiple whitespaces with single whitespace
        value = re.sub(r'\s+', ' ', value)

        # Step 3) Normalize whitespace around punctuation

        # Remove trailing whitespaces from lstrip_punctuation
        # "This is a sentence !" --> "This is a sentence!"
        lstrip = re.escape(''.join(self.lstrip_punctuation))
        lstrip_pattern = r'\s*(?=[' + lstrip + r'])'
        value = re.sub(lstrip_pattern, '', value)

        # Remove leading whitespaces from rstrip_punctuation
        # "$ 100" --> "$100"
        rstrip = re.escape(''.join(self.rstrip_punctuation))
        rstrip_pattern = r'(?<=[' + rstrip + r'])\s*'
        value = re.sub(rstrip_pattern, '', value)

        # Remove leading and trailing whitespaces from strip_punctuation
        # "Sandwitch - The - Hyphens" --> "Sandwitch-The-Hyphens"
        strip = re.escape(''.join(self.strip_punctuation))
        strip_pattern = r'\s*([' + strip + r'])\s*'
        value = re.sub(strip_pattern, r'\1', value)

        # Step 4) Remove leading and trailing whitespaces
        return value.strip()


class CharWhitespacePadding(Processor):
    """
    lpadding a rpadding are int values representing the number of spaces
    around a character. For example, if lpadding=1 and rpadding=2, then
    the character 'a' would be replaced with ' a  '.

    useful for numeric symbols 1 > 2, 7 - 3 = 4.

    Normalize whitepsace may remove space around hypens, but if these are
    subtraction signs you may want to add padding for readability.
    """

    def __init__(self, chars, lpad=1, rpad=1):
        self.chars = chars
        self.lpad = lpad
        self.rpad = rpad

    def process_value(self, value):
        pattern = "[" + re.escape("".join(self.chars)) + "]"
        return re.sub(
            r'\s*' + pattern + r'\s*', lambda match: ' ' *
            self.lpad + match.group(0).strip() + ' '*self.rpad,
            value
        )


class NormalizeNumericString(Processor):
    """
    Given a string, representing a number, format the string in a standard way.
    Default args are '' and '.' for thousands_sep and decimal_sep respectively.
    These defaults allow for the numerical string to be converted to a numerical type
    in python more easily.

    Edge case to be careful of is when a period is used to seperate thousands.
    100.000 is assumed to be 100,000 by the Price parser and returns an error
    An addtional processor will have to be ran before this one otherwise. 

    Can be used alongside MapCompose(NormalizeNumericString(), float)
    """

    def __init__(
        self,
        thousands_sep='',
        decimal_sep='.',
        decimal_places=2,
        keep_trailing_zeros=False,
        input_decimal_sep='.'
    ):
        self.thousands_sep = thousands_sep
        self.decimal_sep = decimal_sep
        self.decimal_places = decimal_places
        self.keep_trailing_zeros = keep_trailing_zeros

        # This may be better passed as context and subclassing this class
        # from ContextProcessor instead of Processor
        self.input_decimal_sep = input_decimal_sep

    def process_value(self, value):
        """
        The curr_thousands_sep and curr_decimal_sep arguments are used to determine
        Need to be supplied so the string can be seperated into it's integer and decimal parts.
        """
        # The price_parser.Price object is good at detecting various number formats.
        # 1 000 000,00
        # 1,000,000.00
        # 1.000.000,00
        # so no custom logic needs to be implemented to turn string into number.
        num = Price.fromstring(
            value,
            decimal_separator=self.input_decimal_sep
        ).amount_float

        # The f-string won't take all possible formats for thousands_sep and decimal_sep
        # For example f"{num: ,2f}" will raise a ValueError (use space for thousands_sep, and comma for decimal_sep)
        # So we'll use default values and replace them later
        num = f"{num:,.{self.decimal_places}f}"

        # If we have the number 1,000,000.00 and we wish to use
        # a dot as the thousands_sep and a comma as the decimal_sep
        # doing the following will not work:
        # num = num.replace(',', '.')
        # num = num.replace('.', ',')
        # We'll get 100,000,000,00 instead of 100,000,000.00
        # So we'll replace the commas and dots with temporary values
        num = num.replace(',', 'THOUSANDS_SEP')
        num = num.replace('.', 'DECIMAL_SEP')

        # Now to replace the temporary values with the user supplied values
        num = num.replace('THOUSANDS_SEP', self.thousands_sep)
        num = num.replace('DECIMAL_SEP', self.decimal_sep)

        if self.keep_trailing_zeros is False:
            # Return integer if no non-zero decimal places
            num = num.rstrip('0').rstrip(self.decimal_sep)

        return num


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
        # from w3lib.html import remove_tags (vs BeautifulSoup)
        return BeautifulSoup(value, "html.parser").get_text()


class Demojize(Processor):
    """
    Replace Unicode emoji in a string with emoji shortcodes. Useful for storage.
    Accepts delimiters, language, version, handle_version as keyword arguments
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def process_value(self, value):
        return emoji.demojize(value, *self.args, **self.kwargs)


class RemoveEmojis(Processor):
    """
    Given a string, return a string with all emojis removed.
    Accepts replace and version as keyword arguments
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def process_value(self, value):
        return emoji.replace_emoji(value, *self.args, **self.kwargs)


class StripQuotes(Processor):
    """
    Given a string, return a string striped of any number of quotes/tick marks.
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
