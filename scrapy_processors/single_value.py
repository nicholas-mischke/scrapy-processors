"""
This file contains the definition of the processors that override the process_value
method of the Processor class.

iterable_processors contains the processors that override the __call__ method of the
Processor class.
"""

# Standard Library Imports
from collections import defaultdict
from datetime import datetime, date, time
from typing import (
    Any,
    Optional,
    Mapping,
    Iterable,
    List,
    Union,
    Set,
    Tuple,
    Dict,
    Callable,
)
from urllib.parse import urlparse
import re

# 3rd 🎉 Imports
import dateparser
import emoji
import jmespath
import pytz
from bs4 import BeautifulSoup
from phonenumbers import PhoneNumberMatcher, PhoneNumberFormat, format_number
from price_parser import Price
from tzlocal import get_localzone

# Local Imports
from itemloaders.utils import arg_to_iter
from scrapy.http import Response
from scrapy_processors.base import Processor


# ... String ...
def regex_chars(chars: Union[str, Iterable[str]], escape: bool = True) -> str:
    """
    Returns a regex character class from a string or iterable of strings.

    Description:
    ------------
    This function takes a string or iterable of strings and converts them into a regex character class.
    Optionally, it can escape the characters.

    Parameters:
    -----------
    - chars (Union[str, Iterable[str]]): A string or iterable of strings.
    - escape (bool): Whether to escape the characters. Default is True.

    Returns:
    --------
    str: A regex character class.

    Example:
    --------
    >>> regex_chars(['a', 'b', 'c'])
    '[abc]'
    >>> regex_chars('abc', escape=False)
    '[abc]'
    """
    chars = arg_to_iter(chars)
    chars = [re.escape(c) if escape else c for c in chars]
    return r"[{}]".format("".join(chars))


class UnicodeEscape(Processor):
    """
    Processor to encode and decode strings, converting escape sequences into their respective characters.

    Note:
    -----
    Some escape sequences in this docstring will not display properly in the rendered docs.
    If the escape sequences are not visible, please refer to the source code.

    Description:
    ------------
    This class takes a string input and returns it with escape sequences such as '\\n', '\\t', etc.
    converted to their corresponding characters.

    Default Context:
    ----------------
    - encoding (str): The string encoding format. Default is 'utf-8'.
    - encoding_errors (str): The policy for encoding errors. If set to 'ignore', errors will be ignored. If set to 'strict', encoding errors raise a UnicodeError. Default is 'backslashreplace'.
    - decoding (str): The decoding format. Default is 'unicode_escape'.
    - decoding_errors (str): The policy for decoding errors. Default is 'strict'.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    str: The input string with escape sequences converted to respective characters.

    Example:
    --------
    >>> processor = UnicodeEscape()
    >>> processor.process_value('hello\\nworld')  # 'hello\\nworld' is now 'hello\nworld'
    'hello\nworld'
    """

    encoding: str = "utf-8"
    encoding_errors: str = "backslashreplace"

    decoding: str = "unicode_escape"
    decoding_errors: str = "strict"

    def process_value(self, value: str, **context) -> str:
        bytes = value.encode(context["encoding"], context["encoding_errors"])
        return bytes.decode(context["decoding"], context["decoding_errors"])


class NormalizeWhitespace(Processor):
    """
    Processor to turn any number of whitespaces (newline, tabs, spaces, etc.) into a single space.

    Description:
    ------------
    This class takes a string and returns a new string in which all contiguous
    whitespace characters are replaced with a single space.

    leading and trailing whitespaces are removed.

    - leading whitespaces are removed from lstrip_chars.
    - trailing whitespaces are removed from rstrip_chars.
    - leading and trailing whitespaces are removed from strip_chars.

    Default Context:
    ----------------
    - lstrip_chars (Set[str]): Punctuation characters that should not have whitespace to their left.
    - lstrip_chars_add (Set[str]): Additional punctuation characters that should not have whitespace to their left.
    - listrip_chars_ignore (Set[str]): Punctuation characters to ignore.

    - rstrip_chars (Set[str]): Punctuation characters that should not have whitespace to their right.
    - rstrip_chars_add (Set[str]): Additional punctuation characters that should not have whitespace to their right.
    - rstrip_chars_ignore (Set[str]): Punctuation characters to ignore.

    - strip_chars (Set[str]): Punctuation characters that should not have whitespace on either side.
    - strip_chars_add (Set[str]): Additional punctuation characters that should not have whitespace on either side.
    - strip_chars_ignore (Set[str]): Punctuation characters to ignore.

    - other_chars (Set[str]): Here more for documentation, than functionality.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    str: The input string with normalized whitespace.

    Example:
    --------
    >>> processor = NormalizeWhitespace()
    >>> processor.process_value('This \n     is a \t\t   sentence !')
    'This is a sentence!'
    ...
    >>> processor.process_value('$ 100')
    '$100'
    >>> processor(['    For the low, low price of $ 1,000,000 !!!'])
    ['For the low, low price of $1,000,000!!!']

    Notes:
    ------
    Assumes utf8, utf16, ascii or latin-1 encoding.
    """

    lstrip_chars: Set[str] = {
        # Punctuation Characters That Typically Don't Have Whitespace to Their Left
        ".",  # Period/Full stop
        ",",  # Comma
        "!",  # Exclamation mark
        "?",  # Question mark
        ")",  # Right parenthesis
        "]",  # Right square bracket
        "}",  # Right curly brace
        ":",  # Colon
        ";",  # Semicolon
        "%",  # Percent sign
        "\u2019",  # Right Single Quotation Mark ('’')
        "\u201D",  # Right Double Quotation Mark ('”')
        "\x92",  # latin-1 Right Single Quotation Mark ('’')
        "\x94",  # latin-1 Right Double Quotation Mark ('”')
    }
    lstrip_chars_add: Set[str] = set()
    lstrip_chars_ignore: Set[str] = set()

    rstrip_chars: Set[str] = {
        # Punctuation Characters That Typically Don't Have Whitespace to Their Right
        "(",  # Left parenthesis
        "$",  # Dollar sign
        "[",  # Left square bracket
        "{",  # Left curly brace
        "#",  # Hash/Pound sign
        "\u2018",  # Left Single Quotation Mark ('‘')
        "\u201C",  # Left Double Quotation Mark ('“')
        "\x91",  # latin-1 Left Single Quotation Mark ('‘')
        "\x93",  # latin-1 Left Double Quotation Mark ('“')
    }
    rstrip_chars_add: Set[str] = set()
    rstrip_chars_ignore: Set[str] = set()

    strip_chars: Set[str] = {
        # Punctuation Characters That Typically Don't Have Whitespace Around Them
        "-",  # Hyphen-minus
        "/",  # Slash
        "_",  # Underscore
        "@",  # At sign
        "\\",  # Backslash
        "^",  # Circumflex accent
        "~",  # Tilde
    }
    strip_chars_add: Set[str] = set()
    strip_chars_ignore: Set[str] = set()

    # Not used in the logic of the processor, but here for documentation.
    other_chars: Set[str] = {
        "*",  # Asterisk
        "&",  # Ampersand
        "|",  # Vertical bar
        # ASCII (difficult to know if they should be left or right stripped)
        "\x27",  # Apostrophe ("'")
        "\x22",  # Quotation Mark ('"')
        # Numerical ones
        "=",  # Equals sign
        "+",  # Plus sign
        "<",  # Less than sign
        ">",  # Greater than sign
    }

    def process_value(self, value: str, **context) -> str:
        # Step 1) Remove zero-width spaces
        value = re.sub(r"[\u200b\ufeff]", "", value)

        # Step 2) Replace multiple whitespaces with single whitespace
        value = re.sub(r"\s+", " ", value)

        # Step 3) Normalize whitespace around punctuation

        context = self.unpack_context(**context)

        # Remove trailing whitespaces from lstrip_punctuation
        # "This is a sentence !" --> "This is a sentence!"
        lstrip, add, ignore = context[:3]
        lstrip, add, ignore = set(lstrip), set(add), set(ignore)
        chars = lstrip.union(add).difference(ignore)
        pattern = r"\s*(?=" + regex_chars(chars) + r")"
        value = re.sub(pattern, "", value)

        # Remove leading whitespaces from rstrip_punctuation
        # "$ 100" --> "$100"
        rstrip, add, ignore = context[3:6]
        rstrip, add, ignore = set(rstrip), set(add), set(ignore)
        chars = rstrip.union(add).difference(ignore)
        pattern = r"(?<=" + regex_chars(chars) + r")\s*"
        value = re.sub(pattern, "", value)

        # Remove leading and trailing whitespaces from strip_punctuation
        # "Sandwitch - The - Hyphens" --> "Sandwitch-The-Hyphens"
        strip, add, ignore = context[6:9]
        strip, add, ignore = set(strip), set(add), set(ignore)
        chars = strip.union(add).difference(ignore)
        pattern = r"\s*(" + regex_chars(chars) + r")\s*"
        value = re.sub(pattern, r"\1", value)

        # Step 4) Remove leading and trailing whitespaces
        return value.strip()


class CharWhitespacePadding(Processor):
    """
    Processor that takes a string and adds padding around specific characters.

    Description:
    ------------
    This class is useful for numeric expressions (e.g. "1 > 2", "7 - 3 = 4") where
    padding around operators enhances readability.

    Default Context:
    ----------------
    - chars (Set[str]): The characters around which to add padding.
    - lpad (int): The number of spaces to add to the left of the character. Default is 1.
    - rpad (int): The number of spaces to add to the right of the character. Default is 1.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    str: The input string with padding added around the specified characters.

    Example:
    --------
    >>> processor = CharWhitespacePadding(('-', '='), lpad=1, rpad=1)
    >>> processor.process_value('7   - 3  = 4')
    '7 - 3 = 4'

    >>> processor = CharWhitespacePadding(chars=('*', '-', '='), lpad=1, rpad=1)
    >>> processor.process_value(['7*3=21', '7-3=4'])
    ['7 * 3 = 21', '7 - 3 = 4']
    """

    chars: Union[str, Set[str]] = set()
    lpad: int = 1
    rpad: int = 1

    def process_value(self, value: str, **context) -> str:
        chars, lpad, rpad, *_ = self.unpack_context(**context)
        chars = set(chars)

        pattern = regex_chars(chars)
        return re.sub(
            r"\s*" + pattern + r"\s*",
            lambda match: " " * lpad + match.group(0).strip() + " " * rpad,
            value,
        )


class StripQuotes(Processor):
    """
    Processor that removes any leading or trailing quote/tick marks from a given string.

    Description:
    ------------
    The processor handles multiple encodings such as UTF-8, UTF-16, ASCII, or Latin-1.
    It uses a regex pattern to detect and strip quote marks at the start and end of the string.

    Default Context:
    ----------------
    - quotes (Set[str]): A set of quote marks to remove.
    - quotes_add (Set[str]): Additional quote marks to remove.
    - quotes_ignore (Set[str]): Quote marks to ignore.

    - ticks (Set[str]): A set of tick marks to remove.
    - ticks_add (Set[str]): Additional tick marks to remove.
    - ticks_ignore (Set[str]): Tick marks to ignore.

    - symbols_ignore (Set[str]): Either quote marks or tick marks to ignore.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    str: The input string with leading and trailing quote marks removed.

    Example:
    --------
    >>> processor = StripQuotes()
    >>> processor.process_value('"Hello, world!"')
    'Hello, world!'

    >>> processor = StripQuotes()
    >>> processor(['"😂"', '‘🥰’', '“👍”'])
    ['😂', '🥰', '👍']
    """

    quotes: Set[str] = {
        # UTF-8 & UTF-16
        "\u2018",  # Left Single Quotation Mark ('‘')
        "\u2019",  # Right Single Quotation Mark ('’')
        "\u201C",  # Left Double Quotation Mark ('“')
        "\u201D",  # Right Double Quotation Mark ('”')
        # ASCII
        "\x27",  # Apostrophe ("'")
        "\x22",  # Quotation Mark ('"')
        # Latin-1 (ISO 8859-1)
        "\x91",  # Left Single Quotation Mark ('‘')
        "\x92",  # Right Single Quotation Mark ('’')
        "\x93",  # Left Double Quotation Mark ('“')
        "\x94",  # Right Double Quotation Mark ('”')
    }
    quotes_add: Set[str] = set()
    quotes_ignore: Set[str] = set()

    ticks: Set[str] = {
        # UTF-8
        "\u0060",  # Grave Accent ('`')
        "\u02CB",  # Modifier Letter Grave Accent ('ˋ')
        # UTF-16
        "\u0060",  # Grave Accent ('`')
        "\u02CB",  # Modifier Letter Grave Accent ('ˋ')
        # ASCII
        "\x60",  # Grave Accent ('`')
        # Latin-1 (ISO 8859-1)
        "\x60",  # Grave Accent ('`')
    }
    ticks_add: Set[str] = set()
    ticks_ignore: Set[str] = set()

    # Used for quotes or ticks that should be ignored
    symbols_ignore: Set[str] = set()

    def process_value(self, value: str, **context) -> str:
        context = self.unpack_context(**context)

        quotes, quotes_add, quotes_ignore = context[:3]
        ticks, ticks_add, ticks_ignore = context[3:6]
        ignore = context[6]

        quotes, quotes_add, quotes_ignore = (
            set(quotes),
            set(quotes_add),
            set(quotes_ignore),
        )
        ticks, ticks_add, ticks_ignore = set(ticks), set(ticks_add), set(ticks_ignore)
        ignore = set(ignore)

        quotes = quotes.union(quotes_add).difference(quotes_ignore)
        ticks = ticks.union(ticks_add).difference(ticks_ignore)

        chars = quotes.union(ticks).difference(ignore)
        chars = regex_chars(chars)

        return re.sub(r"^{chars}+|{chars}+$".format(chars=chars), "", value)


class RemoveHTMLTags(Processor):
    """
    Processor that removes all HTML tags from a string.

    Description:
    ------------
    This processor is useful when you have text data embedded in HTML and you want to
    extract only the text content. The BeautifulSoup library is used to parse and
    remove the HTML tags.

    Default Context:
    ----------------
    None

    Additional Context:
    -------------------
    None

    Returns:
    --------
    str: The input string with all HTML tags removed.

    Example:
    --------
    >>> processor = RemoveHTMLTags()
    >>> processor.process_value('<p>Hello, world!</p>')
    'Hello, world!'

    >>> processor = RemoveHTMLTags()
    >>> processor(['<p>Foo</p>', '<div>Bar</div>', '<span>Baz</span>'])
    ['Foo', 'Bar', 'Baz']
    """

    def process_value(self, value: str) -> str:
        return BeautifulSoup(value, "html.parser").get_text()


class Demojize(Processor):
    """
    Processor that replaces Unicode emojis in a string with their respective shortcodes.

    Description:
    ------------
    Emoji shortcodes are more storage-friendly and also make it easier to understand
    the meaning of an emoji across different platforms. This processor uses the `emoji`
    library to convert Unicode emojis into shortcodes.

    Default Context:
    ----------------
    None

    Additional Context:
    -------------------
    - delimiters (Optional[Tuple[str, str]]): The delimiters used to identify emojis. Default is (':', ':').
    - language (Optional[str]): The language used for shortcodes. Default is 'en'.
    - version (Optional[Union[str, int]]): The emoji version. Default is None.
    - handle_version (Optional[Union[str, Callable[[str, dict], str]]]): A custom function to handle versions. Default is None.

    Returns:
    --------
    str: The input string with Unicode emojis replaced by their respective shortcodes.

    Example:
    --------
    >>> processor = Demojize()
    >>> processor.process_value('Hello, world! 😄')
    'Hello, world! :grinning_face_with_big_eyes:'
    >>> processor(['😂', '🥰', '👍'])
    [':face_with_tears_of_joy:', ':smiling_face_with_hearts:', ':thumbs_up:']

    Method Signatures:
    ------------------
    - emoji.demojize(string, delimiters=(':', ':'), language='en', version=None, handle_version=None)

    References:
    ------------
    https://pypi.org/project/emoji/
    """

    def process_value(self, value: str, **context) -> str:
        demojizer = self.wrap_with_context(emoji.demojize, **context)
        return demojizer(value)


class RemoveEmojis(Processor):
    """
    Processor that removes all emojis from a given string.

    Description:
    ------------
    This processor uses the `emoji` library to detect and remove emojis from the input string.

    Default Context:
    ----------------
    None

    Additional Context:
    -------------------
    - replace (Optional[Union[str, Callable[[str, dict], str]]]): Replacement value for emojis. Default is an empty string.
    - version (Optional[int]): Emoji version to consider. Default is -1 (all versions).

    Returns:
    --------
    str: The input string with all emojis removed.

    Example:
    --------
    >>> processor = RemoveEmojis()
    >>> processor.process_value('Hello, world! 😄')
    'Hello, world! '
    >>> processor(['😂', 'I love you! 🥰', '👍'])
    ['', 'I love you! ', '']

    Method Signatures:
    ------------------
    - emoji.get_emoji_regexp(version=-1)

    References:
    ------------
    https://pypi.org/project/emoji/
    """

    def process_value(self, value: str, **context) -> str:
        replacer = self.wrap_with_context(emoji.replace_emoji, **context)
        return replacer(value)


# ... Numeric / Numeric Strings ...
class ExtractDigits(Processor):
    """
    Extracts numbers in various formats from a string, such as numerical values, prices, phone numbers, etc.

    Description:
    ------------
    This processor uses regular expressions to find sequences of digits in the input string,
    optionally separated by the specified separators. The found numbers are returned as strings.

    Default Context:
    ----------------
    - separators (Iterable[str]): A set of characters used as separators in the numbers.
        Defaults to {",", "."}.

    Returns:
    --------
    A list of strings representing the numbers found in the input string.

    Example:
    --------
    >>> processor = ExtractDigits()
    >>> processor.process_value("Price: $123,456.78, Phone: +123-456-7890")
    ['123,456.78', '123', '456', '7890']
    >>> processor.process_value("In stock (22 available)") # books.toscrape.com
    ['22']
    """

    separators: Iterable[str] = {",", "."}

    def process_value(self, value: str, **context) -> List[str]:
        separators, *_ = self.unpack_context(**context)

        separators = [re.escape(s) for s in separators]
        pattern = r"\d[\d{}]*\d".format("".join(separators))

        return re.findall(pattern, value)  # Returns a list of strings


class NormalizeNumericString(Processor):
    """
    Processor that takes a string representing a number and formats it in a standard way.

    Description:
    ------------
    This class is useful for standardizing numeric expressions in different formats.
    For example, it can handle thousands and decimal separators in various styles
    (1 000 000,00 or 1,000,000.00 or 1.000.000,00) and convert them into a consistent format.

    Default Context:
    ----------------
    - thousands_separator (str): The thousands separator to use in the output string. Default is ''.
    - decimal_separator (str): The decimal separator to use in the output string. Default is '.'.
    - decimal_places (Optional[int]): The number of decimal places to maintain in the output string. Default is None (no rounding).
    - keep_trailing_zeros (bool): If False, trailing zeros after the decimal point are removed. Deafult is False
    - input_decimal_separator (Optional[str]): The decimal separator used in the input string.
        Default is None, leaving PriceParser.fromstring to guess.

    Returns:
    --------
    str: A string representing the number in the desired format.

    Example:
    --------
    >>> processor = NormalizeNumericString(thousands_sep=',', decimal_sep='.', decimal_places=2)
    >>> processor.process_value('1 000 000,00')
    '1,000,000.00'

    Method Signatures:
    -------------------
    -price_parser.Price.fromstring(cls, price, currency_hint=None, decimal_separator=None)
    `decimal_seperator` in this signature is `input_decimal_separator` in context.

    References:
    -----------
    https://pypi.org/project/price-parser/
    """

    thousands_separator: str = ""
    decimal_separator: str = "."
    decimal_places: Optional[int] = None
    keep_trailing_zeros: bool = False

    input_decimal_separator: Optional[str] = None

    def process_value(self, value: str, **context) -> str:
        context = self.unpack_context(**context)

        thousands_separator, decimal_separator = context[:2]
        decimal_places, keep_trailing_zeros = context[2:4]
        input_decimal_separator = context[4]

        # The price_parser.Price object is good at detecting various number formats.
        # 1 000 000,00
        # 1,000,000.00
        # 1.000.000,00
        # so no custom logic needs to be implemented to turn string into number.
        num = Price.fromstring(
            value, decimal_separator=input_decimal_separator
        ).amount_float

        # The f-string won't take all possible formats for thousands_sep and decimal_sep
        # For example f"{num: ,2f}" will raise a ValueError (use space for thousands_sep, and comma for decimal_sep)
        # So we'll use default values and replace them later
        if decimal_places is not None:
            num = f"{num:,.{decimal_places}f}"
        else:
            num = f"{num:,}"

        # If we have the number 1,000,000.00 and we wish to use
        # a dot as the thousands_sep and a comma as the decimal_sep
        # doing the following will not work:
        # num = num.replace(',', '.')
        # num = num.replace('.', ',')
        # We'll get 100,000,000,00 instead of 100,000,000.00
        # So we'll replace the commas and dots with temporary values
        num = num.replace(",", "THOUSANDS_SEP")
        num = num.replace(".", "DECIMAL_SEP")

        # Now to replace the temporary values with the user supplied values
        num = num.replace("THOUSANDS_SEP", thousands_separator)
        num = num.replace("DECIMAL_SEP", decimal_separator)

        if keep_trailing_zeros is False:
            # Return integer if no non-zero decimal places
            num = num.rstrip("0").rstrip(decimal_separator)

        return num


class PriceParser(Processor):
    """
    Processor that takes a string representing a price and returns a price_parser.Price object.

    Description:
    ------------
    This processor is useful when you have price data in string format and you want to extract
    the price information, such as the amount and currency.

    The conversion relies on the ``price_parser.Price.fromstring`` method, and the behavior of the conversion
    can be customized by providing additional keys in the ``loader_context`` or by setting
    them as ``default_context`` when subclassing or constructing an instance of this class.

    Default Context:
    ----------------
    None

    Additional Context:
    -------------------
    - currency_hint (Optional[str]): A string representing the currency to use when parsing the price.
        If not provided, the currency will be guessed by the price_parser library.
    - decimal_separator (Optional[str]): The decimal separator to use when parsing the price.
        If not provided, the decimal separator will be guessed by the price_parser library.

    Returns:
    -------
    price_parser.Price: An object representing the parsed price, including the amount and currency.

    Example:
    --------
    >>> processor = PriceParser()
    >>> result = processor.process_value('$19.99')  # passing a single string to the instance
    >>> print(result.amount)  # Output: 19.99
    >>> print(result.currency)  # Output: '$'

    Method Signatures:
    -------------------
    - price_parser.Price.fromstring(cls, price, currency_hint=None, decimal_separator=None)

    References:
    -----------
    https://pypi.org/project/price-parser/
    """

    return_attrs: Optional[Union[str, Tuple[str, ...]]] = None

    def process_value(self, value: str, **context) -> Price:
        partial = self.wrap_with_context(Price.fromstring, **context)
        price_obj = partial(value)

        return_attrs = context["return_attrs"]
        if return_attrs is None:
            return price_obj
        if isinstance(return_attrs, str):
            return getattr(price_obj, return_attrs)


class ToFloat(Processor):
    """
    Converts a string to a float using the price_parser library.

    Description:
    ------------
    The conversion relies on the ``price_parser.Price.fromstring`` method, and the behavior of the conversion
    can be customized by providing additional keys in the ``loader_context`` or by setting
    them as the ``default_context`` when subclassing or constructing an instance of this class.

    Default Context:
    ----------------
    - decimal_places (Optional[int]): The number of decimal places to round the result to.
        If not provided, the result will not be rounded.

    Additional Context:
    --------------------------
    - decimal_separator (Optional[str]): The decimal separator to use when parsing the price.
        If not provided, the decimal separator will be guessed by the price_parser library.

    Returns:
    --------
    float: The float representation of the input string.

    Example Usage:
    --------------
    >>> processor = StringToFloat(decimal_places=2)
    >>> processor.process_value("$123.456")
    123.46

    Method Signatures:
    -------------------
    - price_parser.Price.fromstring(cls, price, currency_hint=None, decimal_separator=None)
    - round(number, decimal_places) <-- python built-in function, number from price_parser.Price.amount_float

    References:
    -----------
    https://pypi.org/project/price-parser/
    """

    decimal_places: Optional[int] = None

    def process_value(self, value, **context) -> Any:
        decimal_places, *_ = self.unpack_context(**context)

        partial = self.wrap_with_context(Price.fromstring, **context)
        num = partial(value).amount_float

        return round(num, decimal_places) if decimal_places else num


# ... Dates & Time ...
class DateTimeExtraordinaire(Processor):
    """
    Converts a string to a datetime object using the dateparser library, and
    standardizes the datetime object a specified timezone (Defaults to UTC).

    Description:
    ------------
    The conversion relies on the ``dateparser.parse`` method, and the behavior of the conversion
    can be customized by providing additional keys in the ``loader_context`` or by setting
    them as ``default_context`` when subclassing or constructing an instance of this class.

    This class is more flexible than the DateTime class because it can handle a
    wider variety of date and time formats without the need to pass context on slight changes in formats.

    Default Context:
    ----------------
    - output_tz (pytz.BaseTzInfo): The timezone to convert the datetime object to. Default is pytz.UTC.

    Additional Context:
    --------------------------
    - date_formats (Optional[List[str]]): A list of format strings using directives as given
    - languages (Optional[List[str]]): A list of language codes, e.g. ['en', 'es', 'zh-Hant'].
    - locales (Optional[List[str]]): A list of locale codes, e.g. ['fr-PF', 'qu-EC', 'af-NA'].
    - region (Optional[str]): A region code, e.g. 'IN', '001', 'NE'.
    - settings (Optional[Union[Settings, Dict[str, Any]] ]): Configure customized behavior using settings defined in :mod:`dateparser.conf.Settings`.
    - detect_languages_function (Optional[Callable[[str, float], List[str]]]): A function for language detection that takes as input a string (the `date_string`) and

    Returns:
    --------
    datetime: The datetime representation of the input string.

    Example Usage:
    --------------
    >>> processor = DateTimeExtraordinaire()
    >>> processor.process_value("12/12/12")
    2012-12-12 06:00:00+00:00
    >>> processor.process_value("Le 11 Décembre 2014 à 09:00")  # French (11 December 2014 at 09:00)
    2014-12-11 15:00:00+00:00

    Method Signatures:
    -------------------
    >>> dateparser.parse(
        date_string, # Scraped value goes here.
        date_formats=None,
        languages=None,
        locales=None,
        region=None,
        settings=None,
        detect_languages_function=None
    ): ...

    References:
    -----------
    https://pypi.org/project/dateparser/
    """

    output_tz: pytz.BaseTzInfo = pytz.UTC

    return_date = False  # If True, returns a date object instead of a datetime object
    return_time = False  # If True, returns a time object instead of a datetime object

    def process_value(self, value, **context) -> datetime:
        parser = self.wrap_with_context(dateparser.parse, **context)
        datetime_obj = parser(value)
        datetime_obj = datetime_obj.astimezone(context["output_tz"])

        return_date, return_time = context["return_date"], context["return_time"]
        if return_date and return_time:
            return {"date": datetime_obj.date(), "time": datetime_obj.time()}
        elif return_date:
            return datetime_obj.date()
        elif return_time:
            return datetime_obj.time()
        else:
            return datetime_obj


class DateTime(Processor):
    """
    Processor that converts a string representing a date and time into a datetime object.

    Description:
    ------------
    This class uses the ``strptime()`` method to convert a string into a datetime object
    based on a specified format. By default, the format is set to '%Y-%m-%d, %H:%M:%S'.

    Default Context:
    ----------------
    - format (str): The date and time format string. Defaults to '%Y-%m-%d, %H:%M:%S'.
    - input_tz (pytz.BaseTzInfo): The timezone for input datetime. Defaults to local timezone.
    - output_tz (pytz.BaseTzInfo): The timezone to convert the datetime object to. Default is UTC.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    datetime: The datetime object represented by the input string.

    Example:
    --------
    >>> processor = DateTime()
    >>> processor.process_value('2023-05-22, 12:30:45')  # passing a single string to the instance
    datetime.datetime(2023, 5, 22, 12, 30, 45)

    >>> DateTime(format='%d/%m/%Y %H:%M')
    >>> processor(['22/05/2023 12:30', '23/05/2023 13:45'])  # passing a list of strings to the instance
    [datetime.datetime(2023, 5, 22, 12, 30), datetime.datetime(2023, 5, 23, 13, 45)]
    """

    format: str = "%Y-%m-%d, %H:%M:%S"
    input_tz: pytz.BaseTzInfo = pytz.timezone(str(get_localzone()))
    output_tz: pytz.BaseTzInfo = pytz.UTC

    return_date = False  # If True, returns a date object instead of a datetime object
    return_time = False  # If True, returns a time object instead of a datetime object

    def process_value(self, value: str, **context) -> datetime:
        format_str, input_tz, output_tz, *_ = self.unpack_context(**context)

        # Get datetime object from string
        datetime_obj = datetime.strptime(value, format_str)

        # Convert to input timezone
        datetime_obj = input_tz.localize(datetime_obj)

        # Standardize to UTC (or other output timezone)
        datetime_obj = datetime_obj.astimezone(output_tz)

        return_date, return_time = context["return_date"], context["return_time"]
        if return_date and return_time:
            return {"date": datetime_obj.date(), "time": datetime_obj.time()}
        elif return_date:
            return datetime_obj.date()
        elif return_time:
            return datetime_obj.time()
        else:
            return datetime_obj


class Date(Processor):
    """
    Processor that converts a string representing a date into a date object.

    Description:
    ------------
    This class uses the ``strptime()`` method to convert a string into a
    ``datetime.date`` object and then extracts the date component based on a
    specified format.

    Default Context:
    ----------------
    - format (str): The date format string. Defaults to '%Y-%m-%d'.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    date: The date object represented by the input string.

    Example:
    --------
    >>> processor = Date()
    >>> processor.process_value('2023-05-22')  # passing a single string to the instance
    datetime.date(2023, 5, 22)

    >>> processor = Date(format='%d/%m/%Y')
    >>> processor(['22/05/2023', '23/05/2023'])  # passing a list of strings to the instance
    [datetime.date(2023, 5, 22), datetime.date(2023, 5, 23)]
    """

    format: str = "%Y-%m-%d"

    def process_value(self, value: str, **context) -> date:
        return datetime.strptime(value, context["format"]).date()


class Time(Processor):
    """
    Processor that takes a string representing a time and returns a datetime.time object.

    Description:
    ------------
    This class is useful for converting time represented as a string into a Python time object
    that can be used for time-based computations or comparisons. The time string format
    can be customized.

    Default Context:
    ----------------
    - format (str): The format of the time string.
        Defaults to '%H:%M:%S', which corresponds to hour:minute:second.

    Returns:
    --------
    datetime.time: The time object representing the time in the input string.

    Example:
    --------
    >>> processor = Time(format='%H:%M:%S')
    >>> processor.process_value('14:35:20')  # passing a single string to the instance
    datetime.time(14, 35, 20)

    >>> processor = Time(format='%H:%M')
    >>> processor(['14:35', '18:40'])  # passing a list of strings to the instance
    [datetime.time(14, 35), datetime.time(18, 40)]
    """

    format: str = "%H:%M:%S"

    def process_value(self, value: str, **context) -> time:
        return datetime.strptime(value, context["format"]).time()


# ... Contact Info ...
# class Names(Processor):
#     ...
# class Address(Processor):
#     ...


class Emails(Processor):
    """
    Extracts email addresses from a given string.

    Description:
    ------------
    This processor scans a given input string for email addresses and extracts them.
    It can optionally filter the extracted emails by a specific domain, or other content.

    Default Context:
    ----------------
    - domain (Optional[str]): The email domain to filter by. If provided, only emails with this domain will be returned.
        Default is None, meaning that all email addresses will be extracted.
    - contains (Optional[str]): A string that the extracted emails must contain.
        If provided, only emails containing this string will be returned.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    List[str]: A list of extracted email addresses. If the 'domain' parameter is provided, only email addresses with that domain will be returned.

    Example:
    --------
    >>> processor = ExtractEmails()
    >>> processor.process_value('Contact us at support@example.com and sales@example.com.')
    ['support@example.com', 'sales@example.com']

    >>> processor_with_domain = ExtractEmails(domain="example.com")
    >>> processor_with_domain('Contact us at support@example.com and sales@other.com.')
    ['support@example.com']
    """

    domain: Optional[str] = None
    contains: Optional[str] = None

    def get_domain(self, email):
        _, domain = email.split("@")
        return domain

    def process_value(self, value: str, **context) -> List[str]:
        domain, contains, *_ = self.unpack_context(**context)
        emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", value)

        if domain is not None:
            emails = [email for email in emails if domain == self.get_domain(email)]
        if contains is not None:
            emails = [email for email in emails if contains in email]
        return emails


class PhoneNumbers(Processor):
    """
    Extracts phone numbers from a given input string.
    Doesn't work on vanity numbers 1-800-GOT-JUNK.

    Description:
    ------------
    This processor scans the input for valid phone numbers and returns them in the E.164 format.
    It uses the `phonenumbers` library to match phone numbers based on the given region and leniency.

    Default Context:
    ----------------
    - region (str): The region that the phone number is being dialed from. Default is "US".
    - num_format (phonenumbers.PhoneNumberFormat): The format that the phone number should be returned in.
        Default is E.164. Other options are INTERNATIONAL, NATIONAL, and RFC3966.

    Additional Context:
    --------------------------
    - leniency (phonenumbers.Leniency): The leniency to use when matching phone numbers.
        Default is phonenumbers.Leniency.VALID.
    - max_tries (int): The maximum number of tries to attempt to match a phone number.
        Default is 65535.

    Returns:
    --------
    List[str]: A list of extracted phone numbers in E.164 format.

    Example:
    --------
    >>> processor = Phone()
    >>> processor('Call us at +1 650-253-0000 or +44 20-7031-3000.')
    ['+16502530000', '+442070313000']

    Method Signatures:
    -------------------
    - PhoneNumberMatcher.__init__(self, text, region, leniency=Leniency.VALID, max_tries=65535):
    - phonenumbers.format_number(numobj, num_format)

    References:
    -----------
    https://pypi.org/project/phonenumbers/
    """

    region: str = "US"
    num_format = PhoneNumberFormat.E164

    def process_value(self, value: str, **context) -> List[str]:
        """
        Extract phone numbers from a string.
        """
        matcher = self.wrap_with_context(PhoneNumberMatcher, **context)
        matcher = matcher(value)

        numbers = []
        for match in matcher:
            formatter = self.wrap_with_context(format_number, **context)
            numbers.append(formatter(match.number))
        return numbers


class Socials(Processor):
    """
    Extracts social media links from a web page response that match specified domains.

    Description:
    ------------
    This processor takes a Scrapy Response object and extracts links that match given
    social media domains. It can optionally filter the links based on specific content.

    Default Context:
    ----------------
    - domains (List[str]): A list of social media domains to filter by. Default includes major platforms.
    - contains (Optional[str]): A string that the extracted links must contain.
        If provided, only links containing this string will be returned.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    Dict[str, List[str]]: A dictionary where keys are the domains and values are lists of extracted links that match the specified domain and optional content filter.

    Example:
    --------
    >>> processor = Socials(domains=["facebook", "instagram"], contains="john")
    >>> result = processor.process_value(response)
    {
        'facebook': ['https://www.facebook.com/john'],
        'instagram': ['https://www.instagram.com/john']
    }
    """

    domains: List[str] = [
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "linkedin.com",
        "youtube.com",
        "tiktok.com",
        "pinterest.com",
        "reddit.com",
    ]
    additional_domains: Optional[List[str]] = None
    contains: Optional[str] = None

    def process_value(self, value: Response, **context) -> dict:
        domains, additional_domains, contains, *_ = self.unpack_context(**context)

        domains = arg_to_iter(domains)
        domains.extend(additional_domains or [])

        soup = BeautifulSoup(value.body, "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True)]

        # Group the links by domain
        links_by_domain = defaultdict(list)
        for domain in domains:
            domain_name = domain.lstrip("www.")
            filtered_links = [
                link
                for link in links
                if domain_name in urlparse(link).netloc
                and (contains is None or contains in link)
            ]
            links_by_domain[domain_name] = filtered_links

        return links_by_domain


# .. Misc ...
class SelectJmes(Processor):
    """
    Extracts a specific value from a dictionary or list of dictionaries using JMESPath.

    Description:
    ------------
    This processor takes a JMESPath expression (a query string) and applies it to a
    given dictionary or list of dictionaries. The result of the query is returned.
    This can be useful for extracting specific values from nested or complex data structures.

    Default Context:
    ----------------
    - expression (str): The JMESPath expression that defines the part of the data structure to be extracted.

    Additional Context:
    -------------------
    None

    Returns:
    --------
    Any: The value extracted from the data structure according to the JMESPath expression.

    Example:
    --------
    >>> processor = SelectJmes('foo')
    >>> processor.process_value({'foo': 'bar'})  # Finds 'foo' in a value that's a dict
    'bar'

    >>> processor = SelectJmes('foo[*].bar')
    >>> processor([{'foo': {'bar': 1}}, {'foo': {'bar': 2}}])  # Finds 'bar' inside 'foo' in a list of dicts
    [1, 2]

    Method Signatures:
    -------------------
    jmespath.search(expression, data)

    References:
    -----------
    https://pypi.org/project/jmespath/
    """

    expression: str = None

    def process_value(
        self, value: Union[Mapping[str, Any], List[Mapping[str, Any]]], **context
    ) -> Any:
        return jmespath.search(context["expression"], value)


class GetAttr(Processor):
    attr: str = None

    def process_value(self, value: Any, **context) -> Any:
        return getattr(value, context["attr"])


class CallMethod(Processor):
    method: str = None
    args: Tuple[Any] = tuple()
    kwargs: Dict[str, Any] = dict()

    def process_value(self, value: Any, **context) -> Any:
        # Allow context to be used as kwargs here as well.
        args, kwargs = context["args"], context["kwargs"]
        return getattr(value, context["method"])(*context["args"], **context["kwargs"])
