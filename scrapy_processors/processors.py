
# Standard library imports
import re
from collections import ChainMap
from datetime import datetime, date, time
from typing import Any, Callable, Dict, Iterable, Optional, List, Set, Tuple, TypeVar, Union

# 3rd 🎉 imports
import emoji
from bs4 import BeautifulSoup
from price_parser import Price

# itemloaders imports
from itemloaders.utils import arg_to_iter, get_func_args
from scrapy_processors.utils import context_to_kwargs


T = TypeVar('T')  # Input type


class Processor:
    """
    A Processor-like class that uses an optional context to process values.

    This class should be subclassed and the `process_value` method overridden
    to provide specific data cleaning or transformation functionality that could
    optionally use a context.
    >>> def process_value(value, context):
    ...    pass
    >>> def proess_value(value):
    ...    pass
    This context can be used to get kwargs for function calls, for example.

    The overridden `process_value` method should take two arguments, the value to
    process and an optional context, perform some operation on it, and return the 
    processed value.

    When an instance of a `Processor` subclass is called with an iterable
    of values and an optional context, it will return a list with the result of 
    processing each value with the context.

    Example:

    ```python
    class ReverserProcessor(Processor):
        def process_value(self, value: str, context: Optional[dict] = None) -> str:
            reverse = context.get('reverse') if context is not None else False
            return value[::-1] if reverse else value

    # Values passed as loader_context from ItemLoader
    reverser_processor = ReverserProcessor()
    print(reverser_processor(["hello", "world"], {'reverse': True}))  # Output: ['olleh', 'dlrow']
    print(reverser_processor(["hello", "world"], {'reverse': False}))  # Output: ['hello', 'world']
    print(reverser_processor(["hello", "world"]))  # Output: ['hello', 'world']

    # Values passed as default_loader_context from constructor
    reverser_processor = ReverserProcessor(reverse=True)
    print(reverser_processor(["hello", "world"]))  # Output: ['olleh', 'dlrow']

    ```
    """

    def __init__(self, **default_loader_context: Dict[str, Any]):
        self.default_loader_context = default_loader_context

    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        If calling directoy, default_loader_context isn't used. 
        
        Process a single value using an optional context.

        This method must be overridden by subclasses.

        :param value: The value to process.
        :param context: The optional context to use when processing the value.
        :return: The processed value.
        """
        raise NotImplementedError()

    # The `loader_context` parameter cannot be renamed. 
    # It is used by the itemloaders package. 
    def __call__(
        self, 
        values: Iterable[T], 
        loader_context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Process a collection of values using an optional context.

        :param values: An iterable of values to process.
        :param context: The optional context to use when processing the values.
        :return: A list of processed values.
        """
        values = arg_to_iter(values)

        if loader_context:
            context = ChainMap(loader_context, self.default_loader_context)
        else:
            context = self.default_loader_context

        if 'context' in get_func_args(self.process_value):
            return [self.process_value(value, context) for value in values]
        return [self.process_value(value) for value in values]


class EnsureEncoding(Processor):
    """
    Processor to ensure a specific string encoding.

    Given a string, it returns a string with the specified encoding. 

    Args:
        encoding (str): The desired encoding. 
            Default is 'utf-8'.
        ignore_encoding_errors (bool): Whether to ignore encoding errors. 
            If True, errors will be ignored.
            If False, encoding errors raise a UnicodeError. 
            Default is True.

    Example:
        processor = EnsureEncoding('utf-16')
        result = processor('hello world')  # passing a single string to the instance
        # 'hello world' is now encoded in 'utf-16'

        processor = EnsureEncoding('latin-1')
        result = processor(['hello', 'world'])  # passing an iterable to the instance
        # both strings in ['hello', 'world'] are now encoded in 'latin-1'

        processor = EnsureEncoding('ascii', ignore_encoding_errors=False)
        result = processor.process_value('hello world')  # calling process_value method directly
        # 'hello world' is now encoded in 'ascii'

    Returns:
        str: The input string encoded with the desired encoding.
    """

    def __init__(
        self, 
        encoding: str = 'utf-8', 
        encoding_errors: str = 'ignore',
        decoding_errors: str = 'strict'
    ):
        self.default_loader_context = {
            'encoding': encoding, 
            'encoding_errors': encoding_errors,
            'decoding_errors': decoding_errors
        }
        
    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        encoding = context['encoding']
        encoding_errors = context['encoding_errors']
        decoding_errors = context['decoding_errors']
        
        incoming_string = str(value)
        bytes = incoming_string.encode(encoding, encoding_errors)
        outgoing_string = bytes.decode(encoding, decoding_errors)
        
        return outgoing_string


class NormalizeWhitespace(Processor):
    """
    Processor to normalize whitespace in a string.

    This class takes a string and returns a new string in which all contiguous
    whitespace characters are replaced with a single space. It can be called with a 
    single value or an iterable of values.

    The normalization process includes four steps:
        1) Remove zero-width spaces
        2) Replace multiple whitespaces with single whitespace
        3) Normalize whitespace around punctuation marks
        4) Remove leading and trailing whitespaces

    The processor is typically not fully appropriate for numerical strings. 
    This is because in sentences, commas and periods are typically followed by 
    a space, while in numbers, they are not. Consider combining this processor 
    with NormalizeNumericString, inside a MapCompose processor.

    Args:
        lstrip_punctuation (tuple): A tuple of punctuation characters that should not have whitespace to their left. 
        rstrip_punctuation (tuple): A tuple of punctuation characters that should not have whitespace to their right.
        strip_punctuation (tuple): A tuple of punctuation characters that should not have whitespace on either side.

    Returns:
        str: The input string with normalized whitespace.

    Example:
        processor = NormalizeWhitespace()
        result = processor('This is a sentence !')  # passing a single string to the instance
        print(result)  # Output: 'This is a sentence!'

        result = processor.process_value('This is a sentence !')  # calling process_value method directly
        print(result)  # Output: 'This is a sentence!'

        processor = NormalizeWhitespace()
        result = processor(['$ 100', 'Sandwitch - The - Hyphens', '   Multiple   Whitespaces   Here   '])  # passing an iterable to the instance
        print(result) # Output: ['$100', 'Sandwitch-The-Hyphens', 'Multiple Whitespaces Here']

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

    # Utf-8 quotation marks
    # '\u2019', '\u201D', '\u2018', '\u201C',
    # Latin-1 quotation marks
    # '\x92', '\x94', '\x91', '\x93'
    def __init__(
        self,
        lstrip_chars: Set[str] = {
            '.', ',', '!', '?', ')', ']', '}', ':', ';', '%', '\u2019', '\u201D', '\x92', '\x94'
        },
        rstrip_chars: Set[str] = {
            '(', '$', '[', '{', '#', '\u2018', '\u201C', '\x91', '\x93'
        },
        strip_chars: Set[str] = {'-', '/', '_', '@', '\\', '^', '~'}
    ):
        self.default_loader_context = {
            'lstrip_chars': lstrip_chars,
            'rstrip_chars': rstrip_chars,
            'strip_chars': strip_chars
        }

    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        # Step 1) Remove zero-width spaces
        value = re.sub(r'[\u200b\ufeff]', '', value)

        # Step 2) Replace multiple whitespaces with single whitespace
        value = re.sub(r'\s+', ' ', value)

        # Step 3) Normalize whitespace around punctuation

        # Remove trailing whitespaces from lstrip_punctuation
        # "This is a sentence !" --> "This is a sentence!"
        lstrip = context['lstrip_chars']
        lstrip_add = context.get('lstrip_add', set())
        lstrip_ignore = context.get('lstrip_ignore', set())
        lstrip = lstrip.union(lstrip_add).difference(lstrip_ignore)
        
        lstrip = re.escape(''.join(lstrip))
        lstrip_pattern = r'\s*(?=[' + lstrip + r'])'
        value = re.sub(lstrip_pattern, '', value)

        # Remove leading whitespaces from rstrip_punctuation
        # "$ 100" --> "$100"
        rstrip = context['rstrip_chars']
        rstrip_add = context.get('rstrip_add', set())
        rstrip_ignore = context.get('rstrip_ignore', set())
        rstrip = rstrip.union(rstrip_add).difference(rstrip_ignore)
        
        rstrip = re.escape(''.join(rstrip))
        rstrip_pattern = r'(?<=[' + rstrip + r'])\s*'
        value = re.sub(rstrip_pattern, '', value)

        # Remove leading and trailing whitespaces from strip_punctuation
        # "Sandwitch - The - Hyphens" --> "Sandwitch-The-Hyphens"
        strip = context['strip_chars']
        strip_add = context.get('strip_add', set())
        strip_ignore = context.get('strip_ignore', set())
        strip = strip.union(strip_add).difference(strip_ignore)
        
        strip = re.escape(''.join(strip))
        strip_pattern = r'\s*([' + strip + r'])\s*'
        value = re.sub(strip_pattern, r'\1', value)

        # Step 4) Remove leading and trailing whitespaces
        return value.strip()


class CharWhitespacePadding(Processor):
    """
    Processor that takes a string and adds padding around specific characters.

    This class is useful for numeric expressions (e.g. "1 > 2", "7 - 3 = 4") where 
    padding around operators enhances readability.

    Note: 
    The NormalizeWhitespace processor may remove spaces around hyphens, if 
    a hypen is a char in the strip_punctuation tuple for the constructor of that
    class.

    Hypens are also commonly used as subtraction signs in numeric expressions.
    Adding padding around hyphens may be useful for readability in numeric expressions.

    Args:
        chars (Tuple[str]): The characters around which to add padding.
        lpad (int): The number of spaces to add to the left of the character. Defaults to 1.
        rpad (int): The number of spaces to add to the right of the character. Defaults to 1.

    Returns:
        str: The input string with padding added around the specified characters.

    Example:
        processor = CharWhitespacePadding('-', lpad=1, rpad=2)
        result = processor('7-3=4')  # passing a single string to the instance
        print(result)  # Output: '7 -  3 = 4'

        result = processor.process_value('7-3=4')  # calling process_value method directly
        print(result)  # Output: '7 -  3 = 4'

        processor = CharWhitespacePadding(chars=['>', '='], lpad=1, rpad=1)
        result = processor(['7*3=21', '7-3=4']) # passing a list of strings to the instance 
        print(result) # Output: ['7 * 3 = 21', '7 - 3 = 4']
    """

    def __init__(self, chars: Tuple[str], lpad: int = 1, rpad: int = 1):
        self.default_loader_context = {
            'chars': chars,
            'lpad': lpad,
            'rpad': rpad
        }
        
    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        
        chars, lpad, rpad = context['chars'], context['lpad'], context['rpad']
        
        pattern = "[" + re.escape("".join(chars)) + "]"
        return re.sub(
            r'\s*' + pattern + r'\s*', lambda match: ' ' *
            lpad + match.group(0).strip() + ' '*rpad,
            value
        )


class NormalizeNumericString(Processor):
    """
    Processor that takes a string representing a number and formats it in a standard way.

    This class is useful for standardizing numeric expressions in different formats. 
    For example, it can handle thousands and decimal separators in various styles 
    (1 000 000,00 or 1,000,000.00 or 1.000.000,00) and convert them into a consistent format.

    It can be used alongside MapCompose(NormalizeNumericString(), float) to transform
    numerical strings into python numerical data types.
    The default args for this class '' and '.' are choosen to be compatible 
    with python's int(string) or float(string) conversions, as commas will result in a ValueError.
    int("1000") --> 1000
    int("1,000") --> ValueError: invalid literal for int() with base 10: '1,000'

    Note: 
        Edge case to be careful of is when a period is used to separate thousands.
        # Hers One Hundred with two trailing zeros and three trailing zeros
        num = Price.fromstring('100.00').amount_float # 100.0
        num = Price.fromstring('100.000').amount_float # 100000.0
        # These may be errors depending on the context of the data.
        # use input_decimal_sep='.' to avoid this issue.

    Args:
        thousands_sep (str): The thousands separator to use in the output string. Default is ''.
        decimal_sep (str): The decimal separator to use in the output string. Default is '.'.
        decimal_places (int): The number of decimal places to maintain in the output string. Default is 2.
        keep_trailing_zeros (bool): If False, trailing zeros after the decimal point are removed.
        input_decimal_sep (str): The decimal separator used in the input string. Default is '.'.

    Returns:
        str: The input string formatted as a standard numerical string.

    Example:
        processor = NormalizeNumericString(thousands_sep=',', decimal_sep='.', decimal_places=2)
        result = processor('1 000 000,00')  # passing a single string to the instance
        print(result)  # Output: '1,000,000.00'

        result = processor.process_value('1,000,000.00')  # calling process_value method directly
        print(result)  # Output: '1,000,000.00'

        processor = NormalizeNumericString(thousands_sep='', decimal_sep='.', decimal_places=0)
        result = processor(['1,000,000.00', '2.50', '100.99'])  # passing an iterable to the instance
        print(result) # Output: ['1000000', '3', '101']
    """

    def __init__(
        self,
        thousands_sep: str = '',
        decimal_sep: str = '.',
        decimal_places: int = 2,
        keep_trailing_zeros: bool = False,
        input_value_decimal_sep: str = '.'
    ):
        self.default_loader_context = {
            'thousands_sep': thousands_sep,
            'decimal_sep': decimal_sep,
            'decimal_places': decimal_places,
            'keep_trailing_zeros': keep_trailing_zeros,
            'input_value_decimal_sep': input_value_decimal_sep
        }

    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        The curr_thousands_sep and curr_decimal_sep arguments are used to determine
        Need to be supplied so the string can be seperated into it's integer and decimal parts.
        """
        thousands_sep = context['thousands_sep']
        decimal_sep = context['decimal_sep']
        decimal_places = context['decimal_places']
        keep_trailing_zeros = context['keep_trailing_zeros']
        input_value_decimal_sep = context['input_value_decimal_sep']
        
        # The price_parser.Price object is good at detecting various number formats.
        # 1 000 000,00
        # 1,000,000.00
        # 1.000.000,00
        # so no custom logic needs to be implemented to turn string into number.
        num = Price.fromstring(
            value,
            decimal_separator=input_value_decimal_sep
        ).amount_float

        # The f-string won't take all possible formats for thousands_sep and decimal_sep
        # For example f"{num: ,2f}" will raise a ValueError (use space for thousands_sep, and comma for decimal_sep)
        # So we'll use default values and replace them later
        num = f"{num:,.{decimal_places}f}"

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
        num = num.replace('THOUSANDS_SEP', thousands_sep)
        num = num.replace('DECIMAL_SEP', decimal_sep)

        if keep_trailing_zeros is False:
            # Return integer if no non-zero decimal places
            num = num.rstrip('0').rstrip(decimal_sep)

        return num


class PriceParser(Processor):
    """
    Processor that takes a string representing a price and returns a price_parser.Price object.

    This processor is useful when you have price data in string format and you want to extract 
    the price information, such as the amount and currency. 

    Note: The input should be a string formatted like a price (e.g. "$19.99"). 

    Returns:
        price_parser.Price: An object representing the parsed price, including the amount and currency.

    Example:
        processor = PriceParser()
        result = processor('$19.99')  # passing a single string to the instance
        print(result.amount)  # Output: 19.99
        print(result.currency)  # Output: '$'

        result = processor.process_value('€9.99')  # calling process_value method directly
        print(result.amount)  # Output: 9.99
        print(result.currency)  # Output: '€'

        processor = PriceParser()
        result = processor(['$19.99', '€9.99', '£49.99'])  # passing an iterable to the instance
        for price in result:
            print(price.amount, price.currency)  # Output: 19.99 $, 9.99 €, 49.99 £
    """
    
    def __init__(
        self, 
        currency_hint: Optional[str] = None,
        decimal_sep: Optional[str] = None
    ):
        self.default_loader_context = {
            'currency_hint': currency_hint,
            'decimal_separator': decimal_sep
        }

    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> Price:
        
        kwargs = context_to_kwargs(context, Price.fromstring)
        return Price.fromstring(value, **kwargs)


class RemoveHTMLTags(Processor):
    """
    Processor that removes all HTML tags from a string.

    This processor is useful when you have text data embedded in HTML and you want to 
    extract only the text content. The BeautifulSoup library is used to parse and 
    remove the HTML tags. 

    Note: This processor does not remove the content inside the HTML tags.

    Args:
        value (str): The string from which HTML tags should be removed.

    Returns:
        str: The input string with all HTML tags removed.

    Example:
        processor = RemoveHTMLTags()
        result = processor('<p>Hello, world!</p>')  # passing a single string to the instance
        print(result)  # Output: 'Hello, world!'

        result = processor.process_value('<div><p>Hello, world!</p></div>')  # calling process_value method directly
        print(result)  # Output: 'Hello, world!'

        processor = RemoveHTMLTags()
        result = processor(['<p>Foo</p>', '<div>Bar</div>', '<span>Baz</span>'])  # passing an iterable to the instance
        print(result)  # Output: ['Foo', 'Bar', 'Baz']
    """

    def process_value(self, value: str) -> str:
        # from w3lib.html import remove_tags (vs BeautifulSoup)
        return BeautifulSoup(value, "html.parser").get_text()


class Demojize(Processor):
    """
    Processor that replaces Unicode emojis in a string with their respective shortcodes.

    Emoji shortcodes are more storage-friendly and also make it easier to understand 
    the meaning of an emoji across different platforms.

    This processor uses the `emoji` library to convert Unicode emojis into shortcodes.

    Args:
        *args (Tuple): Variable length argument list.
        **kwargs (Dict): Arbitrary keyword arguments.

    Returns:
        str: The input string with Unicode emojis replaced by their respective shortcodes.

    Example:
        processor = Demojize()
        result = processor('Hello, world! 😄')  # passing a single string to the instance
        print(result)  # Output: 'Hello, world! :grinning_face_with_big_eyes:'

        result = processor.process_value('I love 🍕')  # calling process_value method directly
        print(result)  # Output: 'I love :pizza:'

        processor = Demojize()
        result = processor(['😂', '🥰', '👍'])  # passing an iterable to the instance
        print(result)  # Output: [':face_with_tears_of_joy:', ':smiling_face_with_hearts:', ':thumbs_up:']
    """

    def __init__(self,         
        delimiters: Tuple[str, str] = (':', ':'),
        language: str = 'en',
        version: Optional[Union[str, int]] = None,
        handle_version: Optional[Union[str, Callable[[str, dict], str]]] = None
    ):
        self.default_loader_context = {
            'delimiters': delimiters,
            'language': language,
            'version': version,
            'handle_version': handle_version
        }
        
    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        
        kwargs = context_to_kwargs(context, emoji.demojize)
        return emoji.demojize(value, **kwargs)


class RemoveEmojis(Processor):
    """
    Processor that removes all emojis from a given string.

    This processor uses the `emoji` library to detect and remove emojis from the input string.

    Args:
        *args (Tuple): Variable length argument list.
        **kwargs (Dict): Arbitrary keyword arguments.

    Returns:
        str: The input string with all emojis removed.

    Example:
        processor = RemoveEmojis()
        result = processor('Hello, world! 😄')  # passing a single string to the instance
        print(result)  # Output: 'Hello, world! '

        result = processor.process_value('I love 🍕')  # calling process_value method directly
        print(result)  # Output: 'I love '

        processor = RemoveEmojis()
        result = processor(['😂', I Llove you! '🥰', '👍'])  # passing an iterable to the instance
        print(result)  # Output: ['', 'I love you! ', '']
    """

    def __init__(
        self, 
        replace: Union[str, Callable[[str, dict], str]] = '', 
        version: int = -1
    ):
        self.default_loader_context = {
            'replace': replace,
            'version': version
        }

    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        
        kwargs = context_to_kwargs(context, emoji.replace_emoji)
        return emoji.replace_emoji(value, **kwargs)


class StripQuotes(Processor):
    """
    Processor that removes any leading or trailing quote/tick marks from a given string.

    The processor handles multiple encodings such as UTF-8, UTF-16, ASCII, or Latin-1.
    It uses a regex pattern to detect and strip quote marks at the start and end of the string.

    Returns:
        str: The input string with leading and trailing quote marks removed.

    Example:
        processor = StripQuotes()
        result = processor('"Hello, world!"')  # passing a single string to the instance
        print(result)  # Output: 'Hello, world!'

        result = processor.process_value('‘I love pizza’')  # calling process_value method directly
        print(result)  # Output: 'I love pizza'

        processor = StripQuotes()
        result = processor(['"😂"', '‘🥰’', '“👍”'])  # passing an iterable to the instance
        print(result)  # Output: ['😂', '🥰', '👍']
    """

    pattern = r'^[`ˋ‘’“”\'"\u0060\u02CB\x91\x92\x93\x94]+|[`ˋ‘’“”\'"\u0060\u02CB\x91\x92\x93\x94]+$'

    def process_value(self, value: str) -> str:
        return re.sub(self.pattern, '', value)


class StringToDateTime(Processor):
    """
    Processor that converts a string representing a date and time into a datetime object.

    This class uses the strptime() method to convert a string into a datetime object 
    based on a specified format. By default, the format is set to '%Y-%m-%d, %H:%M:%S'.

    Args:
        format (str): The date and time format string. Defaults to '%Y-%m-%d, %H:%M:%S'.

    Returns:
        datetime: The datetime object represented by the input string.

    Example:
        processor = StringToDateTime()
        result = processor('2023-05-22, 12:30:45')  # passing a single string to the instance
        print(result)  # Output: datetime.datetime(2023, 5, 22, 12, 30, 45)

        result = processor.process_value('2023-05-22, 12:30:45')  # calling process_value method directly
        print(result)  # Output: datetime.datetime(2023, 5, 22, 12, 30, 45)

        processor = StringToDateTime(format='%d/%m/%Y %H:%M')
        result = processor(['22/05/2023 12:30', '23/05/2023 13:45'])  # passing a list of strings to the instance
        print(result)  # Output: [datetime.datetime(2023, 5, 22, 12, 30), datetime.datetime(2023, 5, 23, 13, 45)]
    """

    def __init__(self, format: str = '%Y-%m-%d, %H:%M:%S'):
        self.default_loader_context = {
            'format': format
        }

    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> datetime:
        return datetime.strptime(value, context['format'])


class StringToDate(Processor):
    """
    Processor that converts a string representing a date into a date object.

    This class uses the strptime() method to convert a string into a datetime object 
    and then extracts the date component based on a specified format. By default, the format is set to '%Y-%m-%d'.

    Args:
        format (str): The date format string. Defaults to '%Y-%m-%d'.

    Returns:
        date: The date object represented by the input string.

    Example:
        processor = StringToDate()
        result = processor('2023-05-22')  # passing a single string to the instance
        print(result)  # Output: datetime.date(2023, 5, 22)

        result = processor.process_value('2023-05-22')  # calling process_value method directly
        print(result)  # Output: datetime.date(2023, 5, 22)

        processor = StringToDate(format='%d/%m/%Y')
        result = processor(['22/05/2023', '23/05/2023'])  # passing a list of strings to the instance
        print(result)  # Output: [datetime.date(2023, 5, 22), datetime.date(2023, 5, 23)]
    """

    def __init__(self, format: str = '%Y-%m-%d'):
        self.default_loader_context = {
            'format': format
        }

    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> date:
        return datetime.strptime(value, context['format']).date()


class StringToTime(Processor):
    """
    Processor that takes a string representing a time and returns a datetime.time object.

    This class is useful for converting time represented as a string into a python time object 
    that can be used for time-based computations or comparisons. The time string format 
    can be customized.

    Args:
        format (str): The format of the time string. Defaults to '%H:%M:%S' which corresponds to hour:minute:second.

    Returns:
        datetime.time: The time object representing the time in the input string.

    Example:
        processor = StringToTime(format='%H:%M:%S')
        result = processor('14:35:20')  # passing a single string to the instance
        print(result)  # Output: datetime.time(14, 35, 20)

        result = processor.process_value('14:35:20')  # calling process_value method directly
        print(result)  # Output: datetime.time(14, 35, 20)

        processor = StringToTime(format='%H:%M')
        result = processor(['14:35', '18:40'])  # passing a list of strings to the instance
        print(result)  # Output: [datetime.time(14, 35), datetime.time(18, 40)]
    """

    def __init__(self, format: str = '%H:%M:%S'):
        self.default_loader_context = {
            'format': format
        }

    def process_value(
        self, 
        value: T, 
        context: Optional[Dict[str, Any]] = None
    ) -> time:
        return datetime.strptime(value, context['format']).time()


class TakeAllTruthy(Processor):
    """
    Processor that takes an iterable and returns all truthy values.
    If no values are truthy, return default parameter passed to the constructor.

    In Python, truthy values are those which are evaluated to True in a Boolean context. 
    All values are considered "truthy" except for the following, which are "falsy":
    - None
    - False
    - zero of any numeric type (0, 0.0, 0j, Decimal(0), Fraction(0, 1))
    - empty sequences and collections ('', (), [], {}, set(), range(0))

    Args:
        default (List[Any]): The default list to return when no truthy values exist. Defaults to an empty list.

    Returns:
        List[Any]: The list of all truthy values in the input iterable.

    Example:
        processor = TakeAllTruthy(default=[1, 2, 3])
        result = processor([0, False, None, [], 'Hello', 5])  # passing an iterable to the instance
        print(result)  # Output: ['Hello', 5]

        result = processor.process_value([0, False, None, [], '', {}])  # all values are falsy
        print(result)  # Output: [1, 2, 3] (default value is used)
    """

    def __init__(self, default=None):
        self.default = default

    def __call__(self, values: Iterable[Any]) -> List[Any]:
        values = arg_to_iter(values)
        return [value for value in values if value] or self.default
