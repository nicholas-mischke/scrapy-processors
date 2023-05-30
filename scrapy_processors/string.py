
from typing import Any, Tuple, Iterable, Optional, Set, Union, Callable, Mapping
import re

from bs4 import BeautifulSoup
import emoji


from itemloaders.utils import arg_to_iter


from scrapy_processors.common import V
from scrapy_processors.base import Processor


def regex_chars(
    chars: Union[str, Iterable[str]],
    escape: bool = True
) -> str:
    """
    Returns a regex character class from a string or iterable of strings.

    Args:
        chars (Union[str, Iterable[str]]): A string or iterable of strings.
        escape (bool): Whether to escape the characters. 
            Default is True.
        flags (int): Flags to pass to the regex. 
            Default is re.UNICODE.

    Returns:
        str: A regex character class.
    """
    chars = arg_to_iter(chars)
    chars = [re.escape(c) if escape else c for c in chars]
    return r"[{}]".format(''.join(chars))


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

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> str:

        encoding, encoding_errors, decoding_errors \
            = self.unpack_context(context)

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
    lstrip_chars_add: Set[str] = set()
    lstrip_chars_ignore: Set[str] = set()

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
    rstrip_chars_add: Set[str] = set()
    rstrip_chars_ignore: Set[str] = set()

    strip_chars: Set[str] = {
        # Punctuation Characters That Typically Don't Have Whitespace Around Them
        '-',  # Hyphen-minus
        '/',  # Slash
        '_',  # Underscore
        '@',  # At sign
        '\\',  # Backslash
        '^',  # Circumflex accent
        '~',  # Tilde
    }
    strip_chars_add: Set[str] = set()
    strip_chars_ignore: Set[str] = set()

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

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> str:

        context = self.unpack_context(context)

        # Step 1) Remove zero-width spaces
        value = re.sub(r'[\u200b\ufeff]', '', value)

        # Step 2) Replace multiple whitespaces with single whitespace
        value = re.sub(r'\s+', ' ', value)

        # Step 3) Normalize whitespace around punctuation

        # Remove trailing whitespaces from lstrip_punctuation
        # "This is a sentence !" --> "This is a sentence!"
        lstrip, add, ignore = context[:3]
        lstrip, add, ignore = set(lstrip), set(add), set(ignore)
        chars = lstrip.union(add).difference(ignore)
        pattern = r'\s*(?=' + regex_chars(chars) + r')'
        value = re.sub(pattern, '', value)

        # Remove leading whitespaces from rstrip_punctuation
        # "$ 100" --> "$100"
        rstrip, add, ignore = context[3:6]
        rstrip, add, ignore = set(rstrip), set(add), set(ignore)
        chars = rstrip.union(add).difference(ignore)
        pattern = r'(?<=' + regex_chars(chars) + r')\s*'
        value = re.sub(pattern, '', value)

        # Remove leading and trailing whitespaces from strip_punctuation
        # "Sandwitch - The - Hyphens" --> "Sandwitch-The-Hyphens"
        strip, add, ignore = context[6:9]
        rstrip, add, ignore = set(strip), set(add), set(ignore)
        chars = strip.union(add).difference(ignore)
        pattern = r'\s*(' + regex_chars(chars) + r')\s*'
        value = re.sub(pattern, r'\1', value)

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

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> str:

        chars, lpad, rpad = self.unpack_context(context)

        pattern = regex_chars(chars)
        return re.sub(
            r'\s*' + pattern + r'\s*',
            lambda match: ' ' * lpad + match.group(0).strip() + ' ' * rpad,
            value
        )


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

    quotes: Set[str] = {
        # UTF-8 & UTF-16
        '\u2018',  # Left Single Quotation Mark ('‘')
        '\u2019',  # Right Single Quotation Mark ('’')
        '\u201C',  # Left Double Quotation Mark ('“')
        '\u201D',  # Right Double Quotation Mark ('”')

        # ASCII
        '\x27',    # Apostrophe ("'")
        '\x22',    # Quotation Mark ('"')

        # Latin-1 (ISO 8859-1)
        '\x91',    # Left Single Quotation Mark ('‘')
        '\x92',    # Right Single Quotation Mark ('’')
        '\x93',    # Left Double Quotation Mark ('“')
        '\x94'     # Right Double Quotation Mark ('”')
    }
    quotes_add: Set[str] = set()
    quotes_ignore: Set[str] = set()

    ticks: Set[str] = {
        # UTF-8
        '\u0060',  # Grave Accent ('`')
        '\u02CB',  # Modifier Letter Grave Accent ('ˋ')

        # UTF-16
        '\u0060',  # Grave Accent ('`')
        '\u02CB',  # Modifier Letter Grave Accent ('ˋ')

        # ASCII
        '\x60',    # Grave Accent ('`')

        # Latin-1 (ISO 8859-1)
        '\x60'     # Grave Accent ('`')
    }
    ticks_add: Set[str] = set()
    ticks_ignore: Set[str] = set()

    # Used for quotes or ticks that should be ignored
    symbols_ignore: Set[str] = set()

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> str:

        context = self.unpack_context(context)

        quotes, quotes_add, quotes_ignore = context[:3]
        quotes, quotes_add, quotes_ignore = set(quotes), set(quotes_add), set(quotes_ignore)
        
        ticks, ticks_add, ticks_ignore = context[3:6]
        ticks, ticks_add, ticks_ignore = set(ticks), set(ticks_add), set(ticks_ignore)
        
        symbols_ignore = context[6]
        symbols_ignore = set(symbols_ignore)

        quotes = quotes.union(quotes_add).difference(quotes_ignore)
        ticks = ticks.union(ticks_add).difference(ticks_ignore)

        chars = quotes.union(ticks).difference(symbols_ignore)
        chars = regex_chars(chars)

        return re.sub(
            r'^{chars}+|{chars}+$'.format(chars=chars),
            '',
            value
        )


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

        processor = Demojize()
        result = processor(['😂', '🥰', '👍'])  # passing an iterable to the instance
        print(result)  # Output: [':face_with_tears_of_joy:', ':smiling_face_with_hearts:', ':thumbs_up:']
    """

    delimiters: Optional[Tuple[str, str]] = (':', ':')
    language: Optional[str] = 'en'
    version: Optional[Union[str, int]] = None
    handle_version: Optional[Union[str, Callable[[str, dict], str]]] = None

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> str:

        kwargs = self.context_to_kwargs(context, emoji.demojize)
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

    replace: Optional[Union[str, Callable[[str, dict], str]]] = ''
    version: Optional[int] = -1

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> str:

        kwargs = self.context_to_kwargs(context, emoji.replace_emoji)
        return emoji.replace_emoji(value, **kwargs)
