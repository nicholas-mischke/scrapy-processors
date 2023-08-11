import pytest
import math
import random
from scrapy.http import TextResponse
from phonenumbers import PhoneNumberFormat
from datetime import datetime, date, time
import pytz

from scrapy_processors.single_value import (
    # ... String ...
    UnicodeEscape,
    NormalizeWhitespace,
    CharWhitespacePadding,
    StripQuotes,
    RemoveHTMLTags,
    Demojize,
    RemoveEmojis,
    # ... Numeric ...
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

# ... String ...
class TestUnicodeEscape:

    @pytest.fixture
    def processor(self):
        return UnicodeEscape()

    # English, Japanese & Russian strings in UTF-8, UTF-16, ASCII & Latin-1
    @pytest.mark.parametrize("input_value, expected_output",
        [
            # Escape newlines, tabs, etc.
            ("Escape\\n\\n\\t\\tCharacters", "Escape\n\n\t\tCharacters")
        ]
    )
    def test(self, processor, input_value, expected_output):
        assert processor.process_value(input_value) == expected_output


class TestNormalizeWhitespace:

    @pytest.fixture
    def processor(self):
        return NormalizeWhitespace()

    @pytest.mark.parametrize("input_value, expected_value", [
        # Check two base cases
        ("", ""),
        ("Properly Formatted String", "Properly Formatted String"),

        # Step 1: Remove zero-width characters
        (
            "\u200bZero\u200b\ufeffWidth\u200b\ufeffWhitespace\ufeff",
            "ZeroWidthWhitespace"
        ),
        ("Zero​Width​Whitespace", "ZeroWidthWhitespace"),

        # Step 2: Replace all whitespace characters with a single whitespace
        # All other whitespace characters are tested in a separate test
        ("   Multiple   Whitespaces   Here   ", "Multiple Whitespaces Here"),

        # Step 3: Normalize whitespace around punctuation
        # using lstrip, rstrip and strip constructor args
        ("This is a sentence  !", "This is a sentence!"),
        ("This is also a sentence ??", "This is also a sentence??"),

        ("$ 1,000,000.00", "$1,000,000.00"),
        ("{ Curly Brackets}", "{Curly Brackets}"),

        ("Sandwitch - The - Hyphens", "Sandwitch-The-Hyphens"),
        ("nmischkework @ proton.me", "nmischkework@proton.me"),

        # Using UTF-8 left and right double quotation marks
        ('“ Left & Right UTF-8 Quote Marks ”', '“Left & Right UTF-8 Quote Marks”'),

        # Step 4: Remove leading and trailing whitespace
        (" LeadingWhitespace", "LeadingWhitespace"),
        ("TrailingWhitespace ", "TrailingWhitespace"),
    ])
    def test_with_strings(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value

    @pytest.mark.parametrize("whitespace", [
        # This row may have chars that are repeated below
        '\n', '\t', '\r', '\f', '\v', ' ',

        # UTF-8 Whitespace Characters
        " ",        # Space
        "\u00A0",   # No-Break Space
        "\u2002",   # En Space
        "\u2003",   # Em Space
        "\u2004",   # Three-Per-Em Space
        "\u2005",   # Four-Per-Em Space
        "\u2006",   # Six-Per-Em Space
        "\u2007",   # Figure Space
        "\u2008",   # Punctuation Space
        "\u2009",   # Thin Space
        "\u200A",   # Hair Space
        "\u200B",   # Zero Width Space
        "\u202F",   # Narrow No-Break Space
        "\u205F",   # Medium Mathematical Space
        "\u3000"    # Ideographic Space

        # UTF-16 Whitespace Characters
        "\u2000",  # En Quad
        "\u2001",  # Em Quad
        "\u2002",  # En Space
        "\u2003",  # Em Space
        "\u2004",  # Three-Per-Em Space
        "\u2005",  # Four-Per-Em Space
        "\u2006",  # Six-Per-Em Space
        "\u2007",  # Figure Space
        "\u2008",  # Punctuation Space
        "\u2009",  # Thin Space
        "\u200A",  # Hair Space
        "\u202F",  # Narrow No-Break Space
        "\u205F",  # Medium Mathematical Space
        "\u3000",  # Ideographic Space

        # ASCII Whitespace Characters
        " ",    # Space
        "\f",   # Form Feed
        "\n",   # Line Feed
        "\r",   # Carriage Return
        "\t",   # Horizontal Tab
        "\v"    # Vertical Tab

        # Latin-1 Whitespace Characters
        "\x0A",   # Line Feed
        "\x0B",   # Vertical Tab
        "\x0C",   # Form Feed
        "\x0D",   # Carriage Return
        "\x09",   # Horizontal Tab
        "\x20"    # Space

        # Zero-width spaces
        "\u200b",     # Zero Width Space (ZWSP) (Repeat of UTF-8)
        "\ufeff",     # Zero Width No-Break Space (BOM) - UTF-16 only
    ])
    def test_whitespace_characters(self, processor, whitespace):
        input_value = f"Test  {whitespace}  String"
        assert processor(input_value)[0] == "Test String"

    def test_with_loader_context(self):
        string = "This is a sentence  .  "
        processor = NormalizeWhitespace()

        assert processor(string)[0] == "This is a sentence."
        assert processor(string, {'lstrip_chars_ignore': '.'})[
            0] == "This is a sentence ."


class TestCharWhitespacePadding:

    @pytest.fixture
    def math_formula_processor(self):
        return CharWhitespacePadding(
            chars=("=", "+", "-", "*", "<", ">"),
            lpad=1,
            rpad=1
        )

    @pytest.mark.parametrize("input_value, expected_value", [
        # Expected values are the same as the input values
        ("", ""),
        ("1 + 1 = 2", "1 + 1 = 2"),
        # Starts with no whitespace
        ("1+1=2", "1 + 1 = 2"),
        # Has way too much whitespace
        ("1   +  1  =  2", "1 + 1 = 2"),
        # Couple more for fun, using different chars
        ("1*1=1", "1 * 1 = 1"),
        ("1+1>0", "1 + 1 > 0"),
        ("1+1<3", "1 + 1 < 3"),
    ])
    def test_with_strings(self, math_formula_processor, input_value, expected_value):
        assert math_formula_processor(input_value)[0] == expected_value

    def test_with_loader_context(self):
        string = '1+1=2'
        processor = CharWhitespacePadding(('+', '='), 1, 1)

        assert processor(string)[0] == '1 + 1 = 2'
        assert processor(string, {'chars': '='})[0] == '1+1 = 2'


class TestStripQuotes:

    @pytest.fixture
    def processor(self):
        return StripQuotes()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("'Single quotes'", "Single quotes"),
        ('"Double quotes"', "Double quotes"),
        ("“There are only two ways to live your life. One is as though nothing is a miracle. The other is as though everything is a miracle.”",
         "There are only two ways to live your life. One is as though nothing is a miracle. The other is as though everything is a miracle."),
    ])
    def test_process_value_with_strings(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value

    quotes = [
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
    ]

    ticks = [
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
    ]

    symbols = quotes + ticks

    def generate_random_symbols(self):
        length = random.randint(1, len(self.symbols))
        return ''.join(random.choice(self.symbols) for i in range(length))

    @pytest.mark.parametrize("symbol", symbols)
    def test_process_value(self, processor, symbol):
        test_string = symbol + "Test" + symbol + "String" + symbol
        assert processor(test_string)[0] == "Test" + symbol + "String"

    def test_remove_all(self, processor):
        quotes = ''.join(TestStripQuotes.quotes)
        ticks = ''.join(TestStripQuotes.ticks)
        all = ticks + quotes + ticks + quotes

        test_string = all + "Test" + all + "String" + all

        assert processor(test_string)[0] == "Test" + all + "String"

    def test_random(self, processor):
        """"
        Just to be sure it can handle any random combination of quotes and ticks
        """
        for i in range(100):
            random_symbols = self.generate_random_symbols()
            test_string = random_symbols + "Test" + \
                random_symbols + "String" + random_symbols
            assert processor(test_string)[
                0] == "Test" + random_symbols + "String"


class TestRemoveHTMLTags:

    @pytest.fixture
    def processor(self):
        return RemoveHTMLTags()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("<p>Hello, <b>world</b>!</p>", "Hello, world!"),
        ("<h1>Title</h1><p>Paragraph</p>", "TitleParagraph"),
        ("No HTML tags", "No HTML tags"),
        ("", ""),
    ])
    def test_process_value(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value


class TestDemojize:

    @pytest.fixture
    def processor(self):
        return Demojize()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("Python is fun 👍", "Python is fun :thumbs_up:"),
        ("Hello 😊 World 🌍", "Hello :smiling_face_with_smiling_eyes: World :globe_showing_Europe-Africa:"),
        ("No emojis here", "No emojis here"),
        ("", ""),
    ])
    def test_process_value(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value

    def test_with_loader_context(self):
        string = 'Python is fun 👍'
        processor = Demojize()

        assert processor(string)[0] == 'Python is fun :thumbs_up:'
        assert processor(string, **{'delimiters': ('¿', '?')})[0] == \
            'Python is fun ¿thumbs_up?'


class TestRemoveEmojis:

    @pytest.fixture
    def processor(self):
        return RemoveEmojis()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("Python is fun 👍", "Python is fun "),
        ("Hello 😊 World 🌍", "Hello  World "),
        ("No emojis here", "No emojis here"),
        ("", ""),
    ])
    def test_process_value(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value

    def test_with_loader_context(self):
        string = 'Python is fun 👍'
        processor = RemoveEmojis()

        assert processor(string)[0] == 'Python is fun '
        assert processor(string, **{'replace': "ain't it?"})[0] == \
            "Python is fun ain't it?"


# ... Numeric / Numeric Strings ...
class TestExtractDigits:
    @pytest.fixture
    def processor(self):
        return ExtractDigits()

    def wrap_in_text(self, value):
        return f"This is some text {value} This is some more text"

    @pytest.mark.parametrize(
        "input_value",
        [
            "1000",
            "1,000",
            "1.000",
            "1,000.12",
            "1.000,12",
        ],
    )
    def test_process_value(self, processor, input_value):
        assert processor.process_value(self.wrap_in_text(input_value)) == [input_value]

    @pytest.mark.parametrize(
        "input_value, context",
        [
            ("1 000.12", [" ", "."]),
            ("123", {}),
            ("123-456-7890", ["-"]),  # phone number
            ("1234 5678 9012 3456", [" "]),  # credit card number
            ("2023-06-19 at 12:30", [" at ", "-", ":"]),  # date, time or datetime
            ("1:000-12", [":", "-"]),  # other format
        ],
    )
    def test_with_loader_context(self, processor, input_value, context):
        assert processor.process_value(
            self.wrap_in_text(input_value), **{"separators": context}
        ) == [input_value]


class TestNormalizeNumericString:
    # thousands_separator: comma, period, space or empty string
    # decimal_separator: comma or period
    # Test all combinations where they're not the same separator
    @pytest.mark.parametrize(
        "default_context, input_value, expected_value",
        [
            (
                {"thousands_separator": ",", "decimal_separator": "."},
                "1000.75",
                "1,000.75",
            ),
            (
                {"thousands_separator": ".", "decimal_separator": ","},
                "1000.75",
                "1.000,75",
            ),
            (
                {"thousands_separator": " ", "decimal_separator": "."},
                "1000.75",
                "1 000.75",
            ),
            (
                {"thousands_separator": " ", "decimal_separator": ","},
                "1000.75",
                "1 000,75",
            ),
            (
                {"thousands_separator": "", "decimal_separator": "."},
                "1000.75",
                "1000.75",
            ),
            (
                {"thousands_separator": "", "decimal_separator": ","},
                "1000.75",
                "1000,75",
            ),
        ],
    )
    def test_seperators(self, default_context, input_value, expected_value):
        processor = NormalizeNumericString(**default_context)
        assert processor(input_value)[0] == expected_value

    @pytest.mark.parametrize(
        "default_context, input_value, expected_value",
        [
            ({"decimal_places": 0}, "1000.75", "1001"),
            ({"decimal_places": 1}, "1000.75", "1000.8"),
            ({"decimal_places": 2}, "1000.75", "1000.75"),
            ({"decimal_places": 3}, "1000.75", "1000.75"),
        ],
    )
    def test_rounding(self, default_context, input_value, expected_value):
        processor = NormalizeNumericString(**default_context)
        assert processor(input_value)[0] == expected_value

    @pytest.mark.parametrize(
        "default_context, input_value, expected_value",
        [
            (
                {"keep_trailing_zeros": False, "input_decimal_separator": "."},
                "1,000.000",
                "1000",
            ),
            (
                {
                    "decimal_places": 2,
                    "keep_trailing_zeros": True,
                    "input_decimal_separator": ".",
                },
                "1,000.000",
                "1000.00",  # Rounded to 2 decimal places
            ),
        ],
    )
    def test_with_loader_context(self, default_context, input_value, expected_value):
        processor = NormalizeNumericString(**default_context)
        assert processor(input_value)[0] == expected_value


class TestPriceParser:
    @pytest.fixture
    def processor(self):
        return PriceParser()

    @pytest.mark.parametrize(
        "input_value, context, expected_amount, expected_currency",
        [
            ("USD 100.00", {}, 100.00, "USD"),  # United States Dollars
            ("$250,000.00", {}, 250000.00, "$"),  # United States Dollars
            ("EUR 50.99", {}, 50.99, "EUR"),  # Euros
            ("€22,90", {"decimal_separator": ","}, 22.90, "€"),  # Euros
            ("£75.50", {}, 75.50, "£"),  # British Pound Sterling
            ("¥1,500.50", {}, 1500.50, "¥"),  # Japanese Yen
        ],
    )
    def test_process_value(
        self, processor, input_value, context, expected_amount, expected_currency
    ):
        # Process the value
        price = processor(input_value, **context)[0]

        # Assert the attributes of the Price object
        assert math.isclose(price.amount, expected_amount, rel_tol=1e-9)
        assert price.currency == expected_currency

    @pytest.mark.parametrize(
        "input_value, context, expected_amount, expected_currency",
        [
            ("100.00", {"currency_hint": "USD"}, 100.00, "USD"),
            ("50.99", {"currency_hint": "EUR"}, 50.99, "EUR"),
            ("75.50", {"currency_hint": "£"}, 75.50, "£"),
        ],
    )
    def test_with_loader_context(
        self, processor, input_value, context, expected_amount, expected_currency
    ):
        processor = PriceParser(**context)

        price = processor(input_value)[0]
        assert math.isclose(price.amount, expected_amount, rel_tol=1e-9)
        assert price.currency == expected_currency


class TestToFloat:
    @pytest.fixture
    def processor(self):
        return ToFloat()

    @pytest.mark.parametrize(
        "input_values, expected_output",
        [
            ("1", 1.0),
            ("1.0", 1.0),
            ("1.5", 1.5),
            ("1,000", 1000.0),
        ],
    )
    def test(self, processor, input_values, expected_output):
        assert processor(input_values)[0] == expected_output

    @pytest.mark.parametrize(
        "input_values, context, expected_output",
        [
            ("100.000", {"decimal_separator": "."}, 100.0),
        ],
    )
    def test_with_loader_context(
        self, processor, input_values, context, expected_output
    ):
        assert processor(input_values, **context)[0] == expected_output


# ... Dates & Time ...
class TestDateTimeExtraordinaire:

    @pytest.fixture
    def processor(self):
        return DateTimeExtraordinaire()

    @pytest.mark.parametrize("input_value, expected_value", [
        (
            '12/12/12',
            datetime(2012, 12, 12, 6, 0, tzinfo=pytz.UTC)
        ),
        (
            'Fri, 12 Dec 2014 10:55:50',
            datetime(2014, 12, 12, 16, 55, 50, tzinfo=pytz.UTC)
        ),
        (
            'Le 11 Décembre 2014 à 09:00',
            datetime(2014, 12, 11, 15, 0, tzinfo=pytz.UTC)
        ),
    ])
    def test(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("input_value, context, expected_value", [
        (
            '2015, Ago 15, 1:08 pm',
            {'languages': ['pt', 'es']},
            datetime(2015, 8, 15, 18, 8, tzinfo=pytz.UTC)
        ),
        (
            '22 de mayo de 2023, 12:30:45',
            {'languages': ['es']},
            datetime(2023, 5, 22, 17, 30, 45, tzinfo=pytz.UTC)
        )
    ])
    def test_with_context(self, processor, input_value, context, expected_value):
        assert processor(input_value, **context)[0] == expected_value
        assert processor.process_value(input_value, **context) == expected_value


class TestDateTime:

    @pytest.fixture
    def processor(self):
        return DateTime(input_tz=pytz.UTC)

    @pytest.mark.parametrize("input_value, expected_value", [
        ("2022-01-01, 12:00:00", datetime(2022, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)),
        ("2023-05-15, 09:30:00", datetime(2023, 5, 15, 9, 30, 0, tzinfo=pytz.UTC))
    ])
    def test(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("input_value, context, expected_value", [
        (
            "2022-01-01, 12:00:00",
            {},
            datetime(2022, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        ),
        (
            "January 1, 2022 12:00:00",
            {'format': '%B %d, %Y %H:%M:%S'},
            datetime(2022, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        )
    ])
    def test_with_context(self, processor, input_value, context, expected_value):
        assert processor(input_value, **context)[0] == expected_value
        assert processor.process_value(input_value, **context) == expected_value

    def test_different_timezones(self):
        expected_datetime = datetime(2022, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)

        paris_tz = DateTime(
            input_tz=pytz.timezone('Europe/Paris')
        )
        new_york_tz = DateTime(
            input_tz=pytz.timezone('America/New_York')
        )
        los_angeles_tz = DateTime(
            input_tz=pytz.timezone('America/Los_Angeles')
        )

        assert paris_tz('2022-01-01, 13:00:00')[0] == expected_datetime
        assert new_york_tz('2022-01-01, 07:00:00')[0] == expected_datetime
        assert los_angeles_tz('2022-01-01, 04:00:00')[0] == expected_datetime


class TestDate:

    @pytest.fixture
    def processor(self):
        return Date()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("2022-01-01", date(2022, 1, 1)),
        ("2023-05-15", date(2023, 5, 15))
    ])
    def test(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("input_value, context, expected_value", [
        ('2022-01-01', {}, date(2022, 1, 1)),
        ('January 1, 2022', {'format': '%B %d, %Y'}, date(2022, 1, 1))
    ])
    def test_with_context(self, processor, input_value, context, expected_value):
        assert processor(input_value, **context)[0] == expected_value
        assert processor.process_value(input_value, **context) == expected_value


class TestTime:

    @pytest.fixture
    def processor(self):
        return Time()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("10:30:00", time(10, 30, 0)),
        ("22:45:30", time(22, 45, 30))
    ])
    def test(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("input_value, context, expected_value", [
        ("10:30:00", {}, time(10, 30, 0)),
        ("10:30:00 AM", {'format': '%I:%M:%S %p'}, time(10, 30, 0)),
        ("10:30:00 PM", {'format': '%I:%M:%S %p'}, time(22, 30, 0)),
    ])
    def test_with_context(self, processor, input_value, context, expected_value):
        assert processor(input_value, **context)[0] == expected_value
        assert processor.process_value(input_value, **context) == expected_value


# ... Contact ...
class TestEmails:
    @pytest.fixture
    def processor(self):
        return Emails()

    @pytest.mark.parametrize(
        "input_value, expected_output",
        [
            (
                "support@example.com sales@example.com",
                ["support@example.com", "sales@example.com"],
            ),
            ("Contact us at support@example.com.", ["support@example.com"]),
            ("No emails here.", []),
        ],
    )
    def test_process_value(self, processor, input_value, expected_output):
        assert processor.process_value(input_value) == expected_output

    @pytest.mark.parametrize(
        "input_value, domain, expected_output",
        [
            (
                "support@example.com sales@other.com",
                "example.com",
                ["support@example.com"],
            ),
            (
                "support@example.com sales@example.com",
                "example.com",
                ["support@example.com", "sales@example.com"],
            ),
            (
                "support@example.com sales@other.com",
                None,
                ["support@example.com", "sales@other.com"],
            ),
        ],
    )
    def test_with_domain(self, processor, input_value, domain, expected_output):
        assert processor.process_value(input_value, domain=domain) == expected_output

    @pytest.mark.parametrize(
        "input_value, contains, expected_output",
        [
            ("support@example.com sales@other.com", "example", ["support@example.com"]),
            ("support@example.com sales@other.com", "other", ["sales@other.com"]),
            ("support@example.com sales@other.com", "test", []),
        ],
    )
    def test_with_contains(self, processor, input_value, contains, expected_output):
        assert (
            processor.process_value(input_value, contains=contains) == expected_output
        )


class TestPhoneNumbers:
    @pytest.fixture
    def processor(self):
        return PhoneNumbers()

    @pytest.mark.parametrize(
        "input_value, expected_output",
        [
            (
                "Call us at +1 650-253-0000 or +44 20-7031-3000.",
                ["+16502530000", "+442070313000"],
            ),
            ("No phone numbers here.", []),
            (
                "+1 650-253-0000, 816.360.3390, 888-662-5572.",
                ["+16502530000", "+18163603390", "+18886625572"],
            ),
        ],
    )
    def test_default_behavior(self, processor, input_value, expected_output):
        assert processor.process_value(input_value) == expected_output

    @pytest.mark.parametrize(
        "context, input_value, expected_output",
        [
            (
                {"region": "GB", "num_format": PhoneNumberFormat.INTERNATIONAL},
                "Call us at +44 20-7031-3000.",
                ["+44 20 7031 3000"],
            ),
            (
                {"max_tries": 1},
                "+1 650-253-0000, 816.360.3390",
                ["+16502530000", "+18163603390"],
            ),
        ],
    )
    def test_with_custom_parameters(
        self, processor, context, input_value, expected_output
    ):
        assert processor.process_value(input_value, **context) == expected_output


class TestSocials:
    @pytest.fixture
    def processor(self):
        return Socials()

    def create_response(self, links):
        html = "<html><head></head><body>"
        for link in links:
            html += f'<a href="{link}">Link</a>'
        html += "</body></html>"
        return TextResponse(url="http://example.com", body=html, encoding="utf-8")

    @pytest.mark.parametrize(
        "links, expected_output",
        [
            (
                [
                    "https://www.facebook.com/john",
                    "https://www.instagram.com/john",
                    "https://www.unknown.com/john",
                ],
                {
                    "facebook.com": ["https://www.facebook.com/john"],
                    "instagram.com": ["https://www.instagram.com/john"],
                    "twitter.com": [],
                    "linkedin.com": [],
                    "youtube.com": [],
                    "tiktok.com": [],
                    "pinterest.com": [],
                    "reddit.com": [],
                },
            )
        ],
    )
    def test_default_behavior(self, processor, links, expected_output):
        response = self.create_response(links)
        assert dict(processor.process_value(response)) == expected_output

    @pytest.mark.parametrize(
        "context, links, expected_output",
        [
            (
                {"domains": ["facebook.com"], "contains": "john"},
                [
                    "https://www.facebook.com/john",
                    "https://www.facebook.com/mary",
                    "https://www.instagram.com/john",
                ],
                {"facebook.com": ["https://www.facebook.com/john"]},
            )
        ],
    )
    def test_with_custom_parameters(self, processor, context, links, expected_output):
        response = self.create_response(links)
        assert dict(processor.process_value(response, **context)) == expected_output

# ... Misc ...
class TestSelectJmes:

    @pytest.fixture
    def processor(self):
        return SelectJmes('foo')

    @pytest.mark.parametrize("input_values, expected_output", [
        (
            {'foo': 'bar'},
            'bar'
        ),
        (
            {'foo': {'bar': 'baz'}},
            {'bar': 'baz'}
        ),
        (
            {'foo': [{'bar': 'baz'}, {'bar': 'tar'}]},
            [{'bar': 'baz'}, {'bar': 'tar'}]
        ),
    ])
    def test(self, processor, input_values, expected_output):
        assert processor(input_values)[0] == expected_output

    def test_with_loader_context(self):
        processor = SelectJmes('foo.bar')
        assert processor({'foo': {'bar': 'baz'}})[0] == 'baz'

        assert processor(
            values = {'bar': {'bar': 'baz'}},
            **{'expression': 'bar'}
        )[0] == {'bar': 'baz'}
