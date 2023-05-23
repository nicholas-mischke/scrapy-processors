
# Standard Imports
import math
import random
from datetime import date, datetime, time

# 3rd 🎉 imports
import pytest
from itemloaders.utils import get_func_args

# Local Imports
from scrapy_processors.processors import *


class TestProcessor:

    def test_process_value(self):
        processor = Processor()
        with pytest.raises(NotImplementedError):
            processor.process_value('value')

    @pytest.fixture
    def processor(self):
        class ProcessorSubClass(Processor):
            def process_value(self, value):
                return value.upper()
        return ProcessorSubClass()

    @pytest.mark.parametrize("input_values, expected_output", [
        (["hello", "world"], ["HELLO", "WORLD"]),
        (["python", "programming"], ["PYTHON", "PROGRAMMING"]),
        ([], []),
    ])
    def test__call__(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output


class TestContextProcessor:

    def test_process_value(self):
        processor = ContextProcessor()
        with pytest.raises(NotImplementedError):
            processor.process_value('value')

    def test_loader_context_param(self):
        processor = ContextProcessor()
        assert 'loader_context' in get_func_args(processor.__call__)

    @pytest.fixture
    def processor_cls(self):
        class ContextProcessorSubClass(ContextProcessor):
            def process_value(self, value, context):
                if context.get('uppercase') is True:
                    return value.upper()

                if context.get('lowercase') is True:
                    return value.lower()

                return value

        return ContextProcessorSubClass

    @pytest.mark.parametrize(
        ("default_loader_context, loader_context, input_values, expected_output"),
        [
            (
                {}, {},
                ["heLLo", "World"], ["heLLo", "World"]
            ),
            (
                {'uppercase': True}, {},
                ["heLLo", "World"], ["HELLO", "WORLD"]
            ),
            (
                {'uppercase': True}, {'uppercase': False},
                ["heLLo", "World"], ["heLLo", "World"]
            ),  # Override
            (
                {}, {'lowercase': True},
                ["heLLo", "World"], ["hello", "world"]
            ),
        ]
    )
    def test__call__(
        self,
        processor_cls,
        default_loader_context,
        loader_context,
        input_values,
        expected_output
    ):
        processor = processor_cls(**default_loader_context)
        assert processor(input_values, loader_context) == expected_output


class TestEnsureEncoding:

    # English, Japanese & Russian strings in UTF-8, UTF-16, ASCII & Latin-1
    @pytest.mark.parametrize("input_value, expected_value, encoding, ignore", [
        # UTF-8 (Default encoding), English
        ("I Love Python", "I Love Python", "utf-8", True),

        # UTF-8 (Default encoding), Japanese
        ("日本語が大好きです", "日本語が大好きです", "utf-8", True),

        # UTF-8 (Default encoding), Russian
        ("Я люблю Python", "Я люблю Python", "utf-8", True),

        # UTF-16 (Default encoding), English
        ("I Love Python", "I Love Python", "utf-16", True),

        # UTF-16 (Default encoding), Japanese
        ("日本語が大好きです", "日本語が大好きです", "utf-16", True),

        # UTF-16 (Default encoding), Russian
        ("Я люблю Python", "Я люблю Python", "utf-16", True),

        # ASCII (Default encoding), English
        ("I Love Python", "I Love Python", "ascii", True),

        # ASCII (Default encoding), Japanese (Raises UnicodeEncodeError)
        ("日本語が大好きです", "ascii cannot encode", "ascii", False),

        # ASCII (Default encoding), Russian (Raises UnicodeEncodeError)
        ("Я люблю Python", "ascii cannot encode", "ascii", False),

        # Latin-1 (Default encoding), English
        ("I Love Python", "I Love Python", "latin-1", True),

        # Latin-1 (Default encoding), Japanese (Raises UnicodeEncodeError)
        ("日本語が大好きです", "latin-1 cannot encode", "latin-1", False),

        # Latin-1 (Default encoding), Russian (Raises UnicodeEncodeError)
        ("Я люблю Python", "latin-1 cannot encode", "latin-1", False),
    ])
    def test_process_value(self, input_value, expected_value, encoding, ignore):
        processor = EnsureEncoding(encoding, ignore)

        if expected_value.endswith("cannot encode"):
            with pytest.raises(UnicodeEncodeError):
                processor.process_value(input_value)
        else:
            assert processor.process_value(input_value) == expected_value


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
        assert processor.process_value(input_value) == expected_value

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
        assert processor.process_value(input_value) == "Test String"


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
        assert math_formula_processor.process_value(
            input_value) == expected_value


class TestNormalizeNumericString:

    # thousands_sep: comma, period, space or empty string
    # decimal_sep: comma or period
    # Test all combinations where they're not the same separator
    @pytest.mark.parametrize("processor_kwargs, input_value, expected_value", [
        (
            {"thousands_sep": ",", "decimal_sep": "."},
            "1000000.75", "1,000,000.75"
        ),
        (
            {"thousands_sep": ".", "decimal_sep": ","},
            "1000000.75", "1.000.000,75"
        ),
        (
            {"thousands_sep": " ", "decimal_sep": "."},
            "1000000.75", "1 000 000.75"
        ),
        (
            {"thousands_sep": " ", "decimal_sep": ","},
            "1000000.75", "1 000 000,75"
        ),
        (
            {"thousands_sep": "", "decimal_sep": "."},
            "1000000.75", "1000000.75"
        ),
        (
            {"thousands_sep": "", "decimal_sep": ","},
            "1000000.75", "1000000,75"
        ),
    ])
    def test_seperators(self, processor_kwargs, input_value, expected_value):
        processor = NormalizeNumericString(**processor_kwargs)
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("processor_kwargs, input_value, expected_value", [
        ({'decimal_places': 0}, "1000.75", "1001"),
        ({'decimal_places': 1}, "1000.75", "1000.8"),
        ({'decimal_places': 2}, "1000.75", "1000.75"),
        ({'decimal_places': 3}, "1000.75", "1000.75"),
    ])
    def test_rounding(self, processor_kwargs, input_value, expected_value):
        processor = NormalizeNumericString(**processor_kwargs)
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("processor_kwargs, input_value, expected_value", [
        (
            {'keep_trailing_zeros': False},
            "1,000.000",
            "1000"
        ),
        (
            {'keep_trailing_zeros': True},
            "1,000.000",
            "1000.00"  # Rounded to 2 decimal places
        ),
    ])
    def test_keep_trailing_zeros(self, processor_kwargs, input_value, expected_value):
        processor = NormalizeNumericString(**processor_kwargs)
        assert processor.process_value(input_value) == expected_value


class TestPriceParser:

    @pytest.fixture
    def processor(self):
        return PriceParser()

    @pytest.mark.parametrize(
        "value, expected_amount, expected_currency",
        [
            ("USD 100.00", 100.00, "USD"),      # United States Dollars
            ("EUR 50.99", 50.99, "EUR"),        # Euros
            ("£75.50", 75.50, "£"),           # British Pound Sterling
            ("$250,000.00", 250000.00, "$"),  # United States Dollars
            ("€22,90", 22.90, "€"),           # Euros
            ("¥1,500.50", 1500.50, "¥"),      # Japanese Yen
        ],
    )
    def test_process_value(
        self, processor,
        value, expected_amount, expected_currency
    ):

        # Process the value
        price = processor.process_value(value)

        # Assert the attributes of the Price object
        assert math.isclose(price.amount, expected_amount, rel_tol=1e-9)
        assert price.currency == expected_currency


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
        assert processor.process_value(input_value) == expected_value


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
        assert processor.process_value(input_value) == expected_value


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
        assert processor.process_value(input_value) == expected_value


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
        assert processor.process_value(input_value) == expected_value

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
        assert processor.process_value(
            test_string) == "Test" + symbol + "String"

    def test_remove_all(self, processor):
        quotes = ''.join(TestStripQuotes.quotes)
        ticks = ''.join(TestStripQuotes.ticks)
        all = ticks + quotes + ticks + quotes

        test_string = all + "Test" + all + "String" + all

        assert processor.process_value(test_string) == "Test" + all + "String"

    def test_random(self, processor):
        """"
        Just to be sure it can handle any random combination of quotes and ticks
        """
        for i in range(100):
            random_symbols = self.generate_random_symbols()
            test_string = random_symbols + "Test" + \
                random_symbols + "String" + random_symbols
            assert processor.process_value(
                test_string) == "Test" + random_symbols + "String"


class TestStringToDateTime:

    @pytest.fixture
    def processor(self):
        return StringToDateTime()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("2022-01-01, 12:00:00", datetime(2022, 1, 1, 12, 0, 0)),
        ("2023-05-15, 09:30:00", datetime(2023, 5, 15, 9, 30, 0))
    ])
    def test_process_value(self, processor, input_value, expected_value):
        assert processor.process_value(input_value) == expected_value


class TestStringToDate:

    @pytest.fixture
    def processor(self):
        return StringToDate()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("2022-01-01", date(2022, 1, 1)),
        ("2023-05-15", date(2023, 5, 15))
    ])
    def test_process_value(self, processor, input_value, expected_value):
        assert processor.process_value(input_value) == expected_value


class TestStringToTime:

    @pytest.fixture
    def processor(self):
        return StringToTime()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("10:30:00", time(10, 30, 0)),
        ("22:45:30", time(22, 45, 30))
    ])
    def test_process_value(self, processor, input_value, expected_value):
        assert processor.process_value(input_value) == expected_value


class TestTakeAllTruthy:

    @pytest.fixture
    def processor(self):
        return TakeAllTruthy(default=[])

    @pytest.mark.parametrize("input_values, expected_output", [
        (
            [True, 123, 'abc', [1, 2, 3]],
            [True, 123, 'abc', [1, 2, 3]]
        ),
        (
            [None, False, '', [], 0],
            []
        ),
        (
            [0, '', False, 7, [], None, 'empty'],
            [7, 'empty']
        ),
        ([], []),
    ])
    def test_process_value(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output
