
# Standard library imports
from collections import ChainMap
from copy import deepcopy
from datetime import datetime, date, time
from inspect import Parameter, Signature
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Type, TypeVar, Union

# 3rd 🎉 imports
import emoji
from bs4 import BeautifulSoup
from price_parser import Price

# itemloaders imports
from itemloaders.utils import arg_to_iter, get_func_args
from scrapy_processors.utils import context_to_kwargs, unpack_context



T = TypeVar('T')  # Input type


class ProcessorMeta(type):
    """
    Metaclass for Processor classes.

    This metaclass automatically collects class variables into the 
    default_context attribute. When a new instance of the Processor 
    subclass is created, the default_context is updated with the 
    arguments passed to the class constructor.

    Attributes:
        default_context (Dict[str, Any]): The default loader context for the processor, 
            which will be updated with instance-specific arguments upon initialization.

    Example:
    
        class Processor(metaclass=ProcessorMeta):
            pass

        class ExampleProcessor(Processor):
            some_arg: int = 10

        print(ExampleProcessor().default_context)  # {'some_arg': 10}
        print(ExampleProcessor(some_arg=20).default_context)  # {'some_arg': 20}

    """

    def __new__(mcs: Type, name: str, bases: tuple, attrs: Dict[str, Any]) -> 'ProcessorMeta':
        """
        Processor subclass class attributes turned into default_context.
        """
        attrs["default_context"] = {
            key: value
            for key, value in attrs.items()
            if not key.startswith("__") and not callable(value)
        }
        return super().__new__(mcs, name, bases, attrs)
    
    def __init__(cls: Type, name: str, bases: tuple, attrs: dict):
        """
        Prevents Processor subclasses from defining __init__().
        This prevents the Processor __init__() from being overridden, 
        which is used to update the default_context.
        """
        if cls.__name__ != 'Processor' and '__init__' in attrs:
            raise TypeError(
                f"{cls.__name__} class should not define __init__().\n"
                "It overrides the Processor __init__() which is used to update the default_context."
            )
        super().__init__(name, bases, attrs)

    def __call__(cls: Type, *args: Any, **kwargs: Any) -> Any:
        """
        Use the args and kwargs to update the default_context.
        """
        # Deepcopy the class default_context
        default_context = deepcopy(cls.default_context)
        
        # To check for TypeErrors, dynamically create a function signature
        #  ProcessorSubClass() takes 3 positional arguments but 4 were given
        #  ProcessorSubClass() got multiple values for argument 'arg'
        params = [
            Parameter(
                name,
                Parameter.POSITIONAL_OR_KEYWORD,
                default=default_context[name]
            ) for name in list(default_context.keys())
        ]
        signature = Signature(params)
        bound_args = signature.bind(*args, **kwargs).arguments

        # Update the default_context with the bound arguments
        default_context.update(bound_args)

        # Create the new instance and set its default_context
        instance = super().__call__()
        instance.default_context = default_context
        return instance


class Processor(metaclass=ProcessorMeta):
    """
    A Processor class that uses an optional context to process values.

    The Processor class is an abstract class that provides a structure for creating data 
    cleaning or transformation functionalities. Each Processor subclass should define 
    a specific data processing method in its `_process_value` function, which might
    optionally use a context.

    The `_process_value` method MUST be overridden in subclasses.

    When an instance of a `Processor` subclass is invoked (called as a function) with 
    an iterable of values and an optional context, it processes each value using the 
    `_process_value` method and returns a list of results. Single values are also accepted 
    and processed in the same manner.

    Example:

    import random

    class ScrambleProcessor(Processor):
        random_order = False
        reverse = False
    
        def _process_value(self, value, context):
            if context['reverse']:
                return value[::-1]
            elif context['random_order']:
                return "".join(random.shuffle(list(value)))
            else:
                return value

    # Values passed as loader_context from ItemLoader
    processor = ReverserProcessor() # {'random_order': False, 'reverse': False}
    values = ["hello", "world"]
    
    print(processor(values)) # Output: ['hello', 'world']
    print(processor(values, {'reverse': True})) # Output: ['olleh', 'dlrow']
    print(processor(values, {'random_order': True})) # Output: ['ehllo', 'dlorw']
    """

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
    ) -> Any:
        """
        Process a single value using an optional context.

        This method is central to the functionality of the Processor class and should define 
        the specific data cleaning or transformation functionality in each subclass.

        Note:
        When calling this method directly, the `default_context` is not applied.
        
        :param value: The value to process.
        :param context: An optional context to use when processing the value. It can be a dictionary or a ChainMap.
        :return: The processed value.

        :raises NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `_process_value` method. "
            "This method should be overridden in all subclasses to provide the processing logic."
        )
    
    # The `loader_context` parameter cannot be renamed.
    # It is used by the itemloaders package.
    def __call__(
        self,
        values: Union[T, Iterable[T]],
        loader_context: Optional[Union[Dict[str, Any], ChainMap]] = None
    ) -> List[Any]:
        """
        Process a collection of values using an optional context.

        This method uses the `_process_value` method to process each value and returns a list of results.
        It's responsible for passing the context to the `_process_value` method.
        
        :param values: An iterable of values to process.
        :param loader_context: An optional context to use when processing the values. It can be a dictionary or a ChainMap.
        :return: A list of processed values.
        """
        values = arg_to_iter(values)

        if loader_context:
            context = ChainMap(loader_context, self.default_context)
        else:
            context = self.default_context

        if 'context' in get_func_args(self._process_value):
            return [self._process_value(value, context) for value in values]
        return [self._process_value(value) for value in values]


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

    Returns:
        str: The input string encoded with the desired encoding.
    """

    encoding: str = 'utf-8'
    encoding_errors: str = 'ignore'
    decoding_errors: str = 'strict'

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
    ) -> str:

        encoding, encoding_errors, decoding_errors = unpack_context(context, 3)

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

        processor = NormalizeWhitespace()
        result = processor(['$ 100', 'Sandwitch - The - Hyphens', '   Multiple   Whitespaces   Here   '])  # passing an iterable to the instance
        print(result) # Output: ['$100', 'Sandwitch-The-Hyphens', 'Multiple Whitespaces Here']

    Assumes utf8, utf16, ascii or latin-1 encoding.
    """

    lstrip_chars: Set[str] = {
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
        '\x92',    # latin-1 Right Single Quotation Mark ('’')
        '\x94'     # latin-1 Right Double Quotation Mark ('”')
    }
    rstrip_chars: Set[str] = {
        # Punctuation Characters That Typically Don't Have Whitespace to Their Right
        '(',  # Left parenthesis
        '$',  # Dollar sign
        '[',  # Left square bracket
        '{',  # Left curly brace
        '#',  # Hash/Pound sign
        '\u2018',  # Left Single Quotation Mark ('‘')
        '\u201C',  # Left Double Quotation Mark ('“')
        '\x91',    # latin-1 Left Single Quotation Mark ('‘')
        '\x93',    # latin-1 Left Double Quotation Mark ('“')
    }
    strip_chars: Set[str] = {
        # Punctuation Characters That Typically Don't Have Whitespace Around Them
        '-',  # Hyphen-minus
        '/',  # Slash
        '_',  # Underscore
        '@',  # At sign
        '\\', # Backslash
        '^',  # Circumflex accent
        '~',  # Tilde
    }
    other_chars: Set[str] = {
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
    }

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
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

        lstrip_pattern = r'\s*(?=[' + re.escape(''.join(lstrip)) + r'])'
        value = re.sub(lstrip_pattern, '', value)

        # Remove leading whitespaces from rstrip_punctuation
        # "$ 100" --> "$100"
        rstrip = context['rstrip_chars']
        rstrip_add = context.get('rstrip_add', set())
        rstrip_ignore = context.get('rstrip_ignore', set())
        rstrip = rstrip.union(rstrip_add).difference(rstrip_ignore)

        rstrip_pattern = r'(?<=[' + re.escape(''.join(rstrip)) + r'])\s*'
        value = re.sub(rstrip_pattern, '', value)

        # Remove leading and trailing whitespaces from strip_punctuation
        # "Sandwitch - The - Hyphens" --> "Sandwitch-The-Hyphens"
        strip = context['strip_chars']
        strip_add = context.get('strip_add', set())
        strip_ignore = context.get('strip_ignore', set())
        strip = strip.union(strip_add).difference(strip_ignore)

        strip_pattern = r'\s*([' + re.escape(''.join(strip)) + r'])\s*'
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

        processor = CharWhitespacePadding(chars=['>', '='], lpad=1, rpad=1)
        result = processor(['7*3=21', '7-3=4']) # passing a list of strings to the instance 
        print(result) # Output: ['7 * 3 = 21', '7 - 3 = 4']
    """

    chars: Union[str, Tuple[str, ...]] = tuple()
    lpad: int = 1
    rpad: int = 1

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
    ) -> str:

        chars, lpad, rpad = unpack_context(context, 3)

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

        processor = NormalizeNumericString(thousands_sep='', decimal_sep='.', decimal_places=0)
        result = processor(['1,000,000.00', '2.50', '100.99'])  # passing an iterable to the instance
        print(result) # Output: ['1000000', '3', '101']
    """

    thousands_separator: str = ''
    decimal_separator: str = '.'
    decimal_places: int = 2
    keep_trailing_zeros: bool = False

    input_decimal_separator: str = '.'

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
    ) -> str:
        
        thousands_separator, decimal_separator, decimal_places, \
        keep_trailing_zeros, input_decimal_separator = unpack_context(context, 5)

        # The price_parser.Price object is good at detecting various number formats.
        # 1 000 000,00
        # 1,000,000.00
        # 1.000.000,00
        # so no custom logic needs to be implemented to turn string into number.
        num = Price.fromstring(
            value,
            decimal_separator=input_decimal_separator
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
        num = num.replace('THOUSANDS_SEP', thousands_separator)
        num = num.replace('DECIMAL_SEP', decimal_separator)

        if keep_trailing_zeros is False:
            # Return integer if no non-zero decimal places
            num = num.rstrip('0').rstrip(decimal_separator)

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
    
        processor = PriceParser()
        result = processor(['$19.99', '€9.99', '£49.99'])  # passing an iterable to the instance
        for price in result:
            print(price.amount, price.currency)  # Output: 19.99 $, 9.99 €, 49.99 £
    """

    currency_hint: Optional[str] = 'USD'
    decimal_separator: Optional[str] = '.'

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
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

        processor = RemoveHTMLTags()
        result = processor(['<p>Foo</p>', '<div>Bar</div>', '<span>Baz</span>'])  # passing an iterable to the instance
        print(result)  # Output: ['Foo', 'Bar', 'Baz']
    """

    def _process_value(self, value: str) -> str:
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

        processor = Demojize()
        result = processor(['😂', '🥰', '👍'])  # passing an iterable to the instance
        print(result)  # Output: [':face_with_tears_of_joy:', ':smiling_face_with_hearts:', ':thumbs_up:']
    """

    delimiters: Tuple[str, str] = (':', ':')
    language: str = 'en'
    version: Optional[Union[str, int]] = None
    handle_version: Optional[Union[str, Callable[[str, dict], str]]] = None

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
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

        processor = RemoveEmojis()
        result = processor(['😂', I Llove you! '🥰', '👍'])  # passing an iterable to the instance
        print(result)  # Output: ['', 'I love you! ', '']
    """

    replace: Union[str, Callable[[str, dict], str]] = ''
    version: int = -1

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
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

        processor = StripQuotes()
        result = processor(['"😂"', '‘🥰’', '“👍”'])  # passing an iterable to the instance
        print(result)  # Output: ['😂', '🥰', '👍']
    """

    def _process_value(self, value: str) -> str:
        return re.sub(
            r'^[`ˋ‘’“”\'"'
            r'\u0060\u02CB\x91\x92\x93\x94]+'
            r'|[`ˋ‘’“”\'"'
            r'\u0060\u02CB\x91\x92\x93\x94]+$',
            '',
            value
        )


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

        processor = StringToDateTime(format='%d/%m/%Y %H:%M')
        result = processor(['22/05/2023 12:30', '23/05/2023 13:45'])  # passing a list of strings to the instance
        print(result)  # Output: [datetime.datetime(2023, 5, 22, 12, 30), datetime.datetime(2023, 5, 23, 13, 45)]
    """

    format: str = '%Y-%m-%d, %H:%M:%S'

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
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

        processor = StringToDate(format='%d/%m/%Y')
        result = processor(['22/05/2023', '23/05/2023'])  # passing a list of strings to the instance
        print(result)  # Output: [datetime.date(2023, 5, 22), datetime.date(2023, 5, 23)]
    """

    format: str = '%Y-%m-%d'

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
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

        processor = StringToTime(format='%H:%M')
        result = processor(['14:35', '18:40'])  # passing a list of strings to the instance
        print(result)  # Output: [datetime.time(14, 35), datetime.time(18, 40)]
    """

    format: str = '%H:%M:%S'

    def _process_value(
        self,
        value: T,
        context: Optional[Union[Dict[str, Any], ChainMap]] = None
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
    """

    default = None

    def __call__(
        self,
        values: Union[T, Iterable[T]],
        loader_context: Optional[Union[Dict[str, Any], ChainMap]] = None
    ) -> List[Any]:

        values = arg_to_iter(values)

        if loader_context:
            context = ChainMap(loader_context, self.default_context)
        else:
            context = self.default_context

        return [value for value in values if value] or context['default']
