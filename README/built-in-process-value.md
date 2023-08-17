
## Built-in processors that override the process_value method

### [UnicodeEscape](#unicodeescape)
---
The `UnicodeEscape` processor is designed to encode and decode strings, converting escape sequences into their respective characters.

### Default Context:

- **encoding (str): = 'utf-8'**

    The string encoding format.
- **encoding_errors (str): = 'backslashreplace'**

    The policy for encoding errors. If set to 'ignore', errors will be ignored. If set to 'strict', encoding errors raise a UnicodeError. If set to 'replace', encoding errors are replaced with a replacement character. If set to 'backslashreplace', encoding errors are replaced with a backslash escape sequence.
- **decoding (str): = 'unicode_escape'**

    The decoding format.
- **decoding_errors (str): ='strict'**

    The policy for decoding errors.


```python
from scrapy_processors import UnicodeEscape

processor = UnicodeEscape()
processor.process_value('Hello\\nWorld!')  # 'Hello\nWorld!'
```

### [NormalizeWhitespace](#normalizewhitespace)
---
The `NormalizeWhitespace` processor is designed to turn any number of whitespaces (newlines, tabs, spaces, etc.) into a single space. It also normalizes whitespace around punctuation according to specific rules defined in the context.

### Default Context:
- **lstrip_chars (Set[str]):** Punctuation characters that should not have whitespace to their left.
- **lstrip_chars_add (Set[str]):** Additional punctuation characters that should not have whitespace to their left.
- **lstrip_chars_ignore (Set[str]):** Punctuation characters to ignore.
- **rstrip_chars (Set[str]):** Punctuation characters that should not have whitespace to their right.
- **rstrip_chars_add (Set[str]):** Additional punctuation characters that should not have whitespace to their right.
- **rstrip_chars_ignore (Set[str]):** Punctuation characters to ignore.
- **strip_chars (Set[str]):** Punctuation characters that should not have whitespace on either side.
- **strip_chars_add (Set[str]):** Additional punctuation characters that should not have whitespace on either side.
- **strip_chars_ignore (Set[str]):** Punctuation characters to ignore.

### Notes:
The default values are comprehensive, and it's unlikely they'll need to be overridden.
They're too verbose to list in documentation, but they can be found in the source code.

```python
from scrapy_processors import NormalizeWhitespace

processor = NormalizeWhitespace()
processor.process_value('This \n     is a \t\t   sentence !')  # 'This is a sentence!'
processor.process_value('$ 100')  # '$100'
processor(['    For the low, low price of $ 1,000,000 !!!'])  # ['For the low, low price of $1,000,000!!!']
```
### [CharWhitespacePadding](#charwhitespacepadding)
---
The `CharWhitespacePadding` processor takes a string and adds padding around specific characters. This class is useful for numeric expressions (e.g., "1 > 2", "7 - 3 = 4") where padding around operators enhances readability.

### Default Context:
- **chars (Set[str]) = set()**
     The characters around which to add padding.
- **lpad (int): = 1**
    The number of spaces to add to the left of the character.
- **rpad (int): = 1**
    The number of spaces to add to the right of the character.

```python
from scrapy_processors import CharWhitespacePadding

processor = CharWhitespacePadding(('-', '='), lpad=1, rpad=1)
processor.process_value('7   - 3  = 4')  # '7 - 3 = 4'

processor = CharWhitespacePadding(chars=('*', '-', '='), lpad=1, rpad=1)
processor.process_value(['7*3=21', '7-3=4'])  # ['7 * 3 = 21', '7 - 3 = 4']
```
### [StripQuotes](#stripquotes)
---
The `StripQuotes` processor removes any leading or trailing quote/tick marks from a given string. It handles multiple encodings such as UTF-8, UTF-16, ASCII, or Latin-1, and uses a regex pattern to detect and strip quote marks at the start and end of the string. It's best practice to use a `str.strip` processor before this one to remove any leading or trailing whitespace.

### Default Context:
- **quotes (Set[str]):** A set of quote marks to remove.
- **quotes_add (Set[str]):** Additional quote marks to remove.
- **quotes_ignore (Set[str]):** Quote marks to ignore.
- **ticks (Set[str]):** A set of tick marks to remove.
- **ticks_add (Set[str]):** Additional tick marks to remove.
- **ticks_ignore (Set[str]):** Tick marks to ignore.
- **symbols_ignore (Set[str]):** Either quote marks or tick marks to ignore.

### Notes:
The default values are comprehensive, and it's unlikely they'll need to be overridden.
They're too verbose to list in documentation, but they can be found in the source code.

```python
from scrapy_processors import StripQuotes

processor = StripQuotes()
processor.process_value('"Hello, world!"')  # 'Hello, world!'
```

### [RemoveHTMLTags](#removehtmltags)
---
The `RemoveHTMLTags` processor is contexless and removes all HTML tags from a string. This processor is useful when you have text data embedded in HTML and you want to extract only the text content. The BeautifulSoup library is used to parse and remove the HTML tags.


```python
from scrapy_processors import RemoveHTMLTags

processor = RemoveHTMLTags()
processor.process_value('<p>Hello, world!</p>')  # 'Hello, world!'
processor(['<p>Foo</p>', '<div>Bar</div>', '<span>Baz</span>'])  # ['Foo', 'Bar', 'Baz']
```

### [Demojize](#demojize)
---
The `Demojize` processor replaces Unicode emojis in a string with emoji shortcodes using the `emoji` library.

### Default Context:

None

### Additional Context:
- **delimiters: (Optional[Tuple[str, str]]) = (':', ':')**

    The delimiters used to identify emojis.
- **language: (Optional[str]) = 'en'**

    The language used for shortcodes. Default is 'en'.
- **version: (Optional[Union[str, int]]) = None**

    The emoji version.
- **handle_version: (Optional[Union[str, Callable[[str, dict], str]]]) = None**

    A custom function to handle versions.

```python
from scrapy_processors import Demojize

processor = Demojize()
processor.process_value('Hello, world! 😄') # 'Hello, world! :grinning_face_with_big_eyes:'
processor(['😂', '🥰', '👍']) # [':face_with_tears_of_joy:', ':smiling_face_with_hearts:', ':thumbs_up:']
```

### [RemoveEmojis](#removeemojis)
---
The `RemoveEmojis` processor removes all emojis from a given string. This processor uses the `emoji` library to detect and remove emojis from the input string.

### Default Context:

None

### Additional Context:
- **replace (Optional[Union[str, Callable[[str, dict], str]]]) = '' # Empty string**

    Replacement value for emojis.
- **version (Optional[int]): = -1 # all versions**

    Emoji version to consider.

```python
from scrapy_processors import RemoveEmojis

processor = RemoveEmojis()
processor.process_value('Hello, world! 😄')  # 'Hello, world! '
processor(['😂', 'I love you! 🥰', '👍'])  # ['', 'I love you! ', '']
```

### [ExtractDigits](#extractdigits)
---
The `ExtractDigits` processor extracts numbers in various formats from a string, such as numerical values, prices, phone numbers, etc. This processor uses regular expressions to find sequences of digits in the input string, optionally separated by the specified separators. The found numbers are returned as strings.

### Default Context:
- **separators (Iterable[str]): = {",", "."} # (comma and period)**

    A set of characters used as separators in the numbers.


```python
from scrapy_processors import ExtractDigits

processor = ExtractDigits()
processor.process_value("Price: $123,456.78, Phone: +123-456-7890")  # ['123,456.78', '123', '456', '7890']
processor.process_value("In stock (22 available)")  # ['22'], from books.toscrape.com
```
### [NormalizeNumericString](#normalizenumericstring)
---
The `NormalizeNumericString` processor takes a string representing a number and formats it in a standard way. This class is useful for standardizing numeric expressions in different formats. For example, it can handle thousands and decimal separators in various styles (1 000 000,00 or 1,000,000.00 or 1.000.000,00) and convert them into a consistent format.

### Default Context:
- **thousands_separator (str): = ""**

    The thousands separator to use in the output string.
- **decimal_separator (str): ="."**

    The decimal separator to use in the output string.
- **decimal_places (Optional[int]): = None # no rounding**

    The number of decimal places to maintain in the output string.
- **keep_trailing_zeros (bool): = False**

    If False, trailing zeros after the decimal point are removed.
- **input_decimal_separator (Optional[str]): = None**

    The decimal separator used in the input string. Default is None, leaving PriceParser.fromstring to guess.


```python
from scrapy_processors import NormalizeNumericString

processor = NormalizeNumericString(thousands_sep=',', decimal_sep='.', decimal_places=2)
processor.process_value('1 000 000,00')  # '1,000,000.00'
```
### [PriceParser](#priceparser)
---
The `PriceParser` processor takes a string representing a price and returns a `price_parser.Price` object. This processor is useful when you have price data in string format and you want to extract the price information, such as the amount and currency.

The conversion relies on the `price_parser.Price.fromstring` method.

### Default Context:

None

### Additional Context:
- **currency_hint (Optional[str]): = None**

    A string representing the currency to use when parsing the price. If not provided, the currency will be guessed by the price_parser library.
- **decimal_separator (Optional[str]): = None**

    The decimal separator to use when parsing the price. If not provided, the decimal separator will be guessed by the price_parser library.

```python
from scrapy_processors import PriceParser

processor = PriceParser()
result = processor.process_value('$19.99')  # passing a single string to the instance
print(result.amount)  # Output: 19.99
print(result.currency)  # Output: '$'
```
### [ToFloat](#tofloat)
---
The `ToFloat` processor converts a string to a float using the price_parser library. The conversion relies on the `price_parser.Price.fromstring` method.

### Default Context:
- **decimal_places (Optional[int]): = None**

    The number of decimal places to round the result to. If not provided, the result will not be rounded.

### Additional Context:
- **decimal_separator (Optional[str]): = None**

    The decimal separator to use when parsing the price. If not provided, the decimal separator will be guessed by the price_parser library.


```python
from scrapy_processors import ToFloat

processor = ToFloat(decimal_places=2)
processor.process_value("$123.456")  # 123.46
```
### [DateTimeExtraordinaire](#datetimeextraordinaire)
---
The `DateTimeExtraordinaire` processor converts a string to a datetime object using the dateparser library and standardizes the datetime object in a specified timezone (defaults to UTC). This class is more flexible than the DateTime class because it can handle a wider variety of date and time formats without the need to pass context on slight changes in formats.

### Default Context:
- **output_tz: pytz.BaseTzInfo = pytz.UTC**

    The timezone to convert the datetime object to.

### Additional Context (All default to `None`):
- **date_formats (Optional[List[str]]):**

    A list of format strings using directives as given.
- **languages (Optional[List[str]]):**

    A list of language codes, e.g. ['en', 'es', 'zh-Hant'].
- **locales (Optional[List[str]]):**

    A list of locale codes, e.g. ['fr-PF', 'qu-EC', 'af-NA'].
- **region (Optional[str]):**

    A region code, e.g. 'IN', '001', 'NE'.
- **settings (Optional[Union[Settings, Dict[str, Any]]]):**

    Configure customized behavior using settings defined in :mod:`dateparser.conf.Settings`.
- **detect_languages_function (Optional[Callable[[str, float], List[str]]]):**

    A function for language detection that takes as input a string (the `date_string`) and ...


```python
from scrapy_processors import DateTimeExtraordinaire

processor = DateTimeExtraordinaire()
processor.process_value("12/12/12")  # datetime.datetime(2012, 12, 12, 6, 0, 0, tzinfo=<UTC>)
processor.process_value("Le 11 Décembre 2014 à 09:00")  # datetime.datetime(2014, 12, 11, 15, 0, 0, tzinfo=<UTC>)
```
### [DateTime](#datetime)
---
The `DateTime` processor converts a string representing a date and time into a datetime object. This class uses the `strptime()` method to convert a string into a datetime object based on a specified format. By default, the format is set to '%Y-%m-%d, %H:%M:%S'.

### Default Context:
- **format (str): ='%Y-%m-%d, %H:%M:%S'**

    The date and time format string.
- **input_tz (pytz.BaseTzInfo): =  pytz.timezone(str(tzlocal.get_localzone()))**

    The timezone for input datetime. Defaults to the local timezone. In the future
    this may be changed to take a response data, and use the url to help determine timezone.
    It's recommended to pass an `input_tz` to either `default_context` or `loader_context` here.
- **output_tz (pytz.BaseTzInfo): = pytz.UTC**

    The timezone to convert the datetime object to. Default is UTC.


```python
from scrapy_processors import DateTime

processor = DateTime()
processor.process_value('2023-05-22, 12:30:45')  # datetime.datetime(2023, 5, 22, 12, 30, 45)

processor = DateTime(format='%d/%m/%Y %H:%M')
processor(['22/05/2023 12:30', '23/05/2023 13:45'])  # [datetime.datetime(2023, 5, 22, 12, 30), datetime.datetime(2023, 5, 23, 13, 45)]
```
### [Date](#date)
---
The `Date` processor converts a string representing a date into a date object. This class uses the `strptime()` method to convert a string into a `datetime.date` object and then extracts the date component based on a specified format.

### Default Context:
- **format (str): = '%Y-%m-%d'**

    The date format string.


```python
from scrapy_processors import Date

processor = Date()
processor.process_value('2023-05-22')  # datetime.date(2023, 5, 22)

processor = Date(format='%d/%m/%Y')
processor(['22/05/2023', '23/05/2023'])  # [datetime.date(2023, 5, 22), datetime.date(2023, 5, 23)]
```
### [Time](#time)
---
The `Time` processor takes a string representing a time and returns a `datetime.time` object. This class is useful for converting time represented as a string into a Python time object.

### Default Context:
- **format (str): = '%H:%M:%S'**

    The format of the time string.

```python
from scrapy_processors import Time

processor = Time(format='%H:%M:%S')
processor.process_value('14:35:20')  # datetime.time(14, 35, 20)

processor = Time(format='%H:%M')
processor(['14:35', '18:40'])  # [datetime.time(14, 35), datetime.time(18, 40)]
```

### [Emails](#emails)
---
The `Emails` processor extracts email addresses from a given input string. It can optionally filter the extracted emails by a specific domain, or other content.

### Default Context:
- **domain (Optional[str]): = None**

    The email domain to filter by. If provided, only emails with this domain will be returned. Default is None, meaning that all email addresses will be extracted.
- **contains (Optional[str]): = None***

    A string that the extracted emails must contain. If provided, only emails containing this string will be returned.

### Returns:
List[str]: A list of extracted email addresses. If the 'domain' parameter is provided, only email addresses with that domain will be returned.

```python
from scrapy_processors import Emails

processor = Emails()
processor.process_value('Contact us at support@example.com and sales@example.com.') # ['support@example.com', 'sales@example.com']

processor_with_domain = Emails(domain="example.com")
processor_with_domain('Contact us at support@example.com and sales@other.com.') # ['support@example.com']
```
### [PhoneNumbers](#phonenumbers)
---
The `PhoneNumbers` processor extracts phone numbers from a given input string and returns them in the E.164 format. Note that this processor does not work on vanity numbers (e.g., 1-800-GOT-JUNK).

### Default Context:
- **region (str): = "US"**

    The region that the phone number is being dialed from. Default is "US".
- **num_format (phonenumbers.PhoneNumberFormat): = PhoneNumberFormat.E164**

    The format that the phone number should be returned in. Default is E.164. Other options are INTERNATIONAL, NATIONAL, and RFC3966.

### Additional Context:
- **leniency (phonenumbers.Leniency): =phonenumbers.Leniency.VALID**

    The leniency to use when matching phone numbers.
- **max_tries (int): = 65535**

    The maximum number of tries to attempt to match a phone number.

```python
from scrapy_processors import PhoneNumbers

processor = PhoneNumbers()
processor.process_value('Call us at +1 650-253-0000 or +44 20-7031-3000.') # ['+16502530000', '+442070313000']
```
### [Socials](#socials)
---
The `Socials` processor extracts social media links from a web page response that match specified domains. It takes a Scrapy Response object and filters links based on given social media domains. It can also optionally filter the links based on specific content.
Returns a dictionary with key being the domain and a list of links as the value.

### Default Context:
- **domains (List[str]): = ["facebook.com", "instagram.com", "twitter.com", "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com", "reddit.com"]**

    A list of social media domains to filter by.
- **contains (Optional[str]):= None**

    A string that the extracted links must contain. If provided, only links containing this string will be returned.
- **additional_domains (Optional[List[str]]): = None**

    Additional domains to be added to the default list for extraction.

```python
from scrapy_processors import Socials
from scrapy.http import Response

processor = Socials(domains=["facebook", "instagram"], contains="john")
response = Response(url="https://example.com", body='<a href="https://www.facebook.com/john"></a><a href="https://www.instagram.com/john"></a>')
result = processor.process_value(response)
# {
#     'facebook.com': ['https://www.facebook.com/john'],
#     'instagram.com': ['https://www.instagram.com/john']
# }
```
### [SelectJmes](#selectjmes)
---
The `SelectJmes` processor extracts specific values from a dictionary or list of dictionaries using JMESPath. It is useful for selecting specific values from nested or complex data structures.

### Default Context:
- **expression (str): = None**

    The JMESPath expression that defines the part of the data structure to be extracted.


```python
from scrapy_processors import SelectJmes

# Example with a single dictionary
processor = SelectJmes(expression='foo')
result = processor.process_value({'foo': 'bar'})  # Finds 'foo' in a value that's a dict
# Output: 'bar'

# Example with a list of dictionaries
processor = SelectJmes(expression='foo[*].bar')
result = processor.process_value([{'foo': {'bar': 1}}, {'foo': {'bar': 2}}])  # Finds 'bar' inside 'foo' in a list of dicts
# Output: [1, 2]
```
