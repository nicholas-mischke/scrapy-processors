
import pytest
import random

from scrapy_processors.string import *


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
        assert processor(string, {'delimiters': ('¿', '?')})[0] == \
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
        assert processor(string, {'replace': "ain't it?"})[0] == \
            "Python is fun ain't it?"
