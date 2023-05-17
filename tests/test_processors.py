
import pytest
import random
import math
from datetime import datetime, date, time
from scrapy_processors.processors import *


class TestMapCompose:

    @pytest.fixture
    def reverse_upper_processor(self):
        return MapCompose(lambda x: x[::-1], str.upper)

    @pytest.fixture
    def lower_processor(self):
        return MapCompose(str.lower)

    @pytest.fixture
    def clean_processor(self):
        return MapCompose(str.strip, str.title)

    @pytest.mark.parametrize("input_values, expected_reverse_upper, expected_lower, expected_clean", [
        (["hello", "world"], 
         ["OLLEH", "DLROW"], ["hello", "world"], ["Hello", "World"]),
        (["apPlE", "baNAna"], 
         ["ELPPA", "ANANAB"], ["apple", "banana"], ["Apple", "Banana"]),
        (["this is a string", "this is another string"],
         ["GNIRTS A SI SIHT", "GNIRTS REHTONA SI SIHT"],
         ["this is a string", "this is another string"],
         ["This Is A String", "This Is Another String"]),
    ])
    def test_process_value(
        self,
        reverse_upper_processor,
        lower_processor,
        clean_processor,
        input_values,
        expected_reverse_upper,
        expected_lower,
        expected_clean
    ):
        assert reverse_upper_processor(input_values) == expected_reverse_upper
        assert lower_processor(input_values) == expected_lower
        assert clean_processor(input_values) == expected_clean

    def test__add__(self):
        def str_upper(value):
            return value.upper()
        
        def str_reverse(value):
            return value[::-1]
        
        map1 = MapCompose(str_upper, **{'foo': 'bar'})
        map2 = MapCompose(str_reverse, **{'foo': 'bar'})

        result = map1 + map2

        assert isinstance(result, MapCompose)
        assert result.functions == (str_upper, str_reverse)
        assert result.default_loader_context == {'foo': 'bar'}

    def test__add__with_incompatible_operands(self):
        map1 = MapCompose(lambda x: x.upper(), foo='bar')
        other = 'some string'

        with pytest.raises(TypeError) as error:
            result = map1 + other

        assert str(error.value) == (
            "Unsupported operand type for +: 'MapCompose' and 'str'"
        )
    
    def test_add_with_different_loader_context(self):
        map1 = MapCompose(lambda x: x.upper(), foo='bar')
        map2 = MapCompose(lambda x: x.lower(), foo='baz')

        with pytest.raises(ValueError) as error:
            result = map1 + map2

        assert str(error.value) == (
            "Cannot add MapCompose objects with mismatched "
            "key, value pairs in their loader default_loader_context\n"
            "Key: foo, self[foo]: bar, other[foo]: baz"
        )


class TestProcessor:

    @pytest.fixture
    def processor(self):
        class ProcessorSubClass(Processor):
            def process_value(self, value):
                return value.upper()
        return ProcessorSubClass()

    def test_process_value(self):
        processor = Processor()
        with pytest.raises(NotImplementedError):
            processor.process_value('value')

    @pytest.mark.parametrize("input_values, expected_output", [
        (["hello", "world"], ["HELLO", "WORLD"]),
        (["python", "programming"], ["PYTHON", "PROGRAMMING"]),
        ([], []),
    ])
    def test__call__(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output


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
        ("Hello, World!", "Hello, World!"),
        ("   NoWhitespace   ", "NoWhitespace"),
        (" LeadingWhitespace", "LeadingWhitespace"),
        ("TrailingWhitespace ", "TrailingWhitespace"),
        ("   Multiple   Whitespace    Here   ", "Multiple Whitespace Here"),
        ("", ""),
        ("\t\tTab\t\tSpaces\t\t", "Tab Spaces"),
        ("\n\nNew\n\nLines\n\n", "New Lines"),
        ("  Leading  \t\t and \n\n Trailing with Tabs & New Lines  .",
         "Leading and Trailing with Tabs & New Lines."),
        #
        ("\n\t\rHello,  World   ! 😂", "Hello, World! 😂"),
        ("This is a . sample ! text ? with whitespace ; around : the punctuation marks  ",
         "This is a. sample! text? with whitespace; around: the punctuation marks"
         ),
    ])
    def test_with_strings(self, processor, input_value, expected_value):
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("whitespace", [
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

    quotes = [
        # UTF-8
        '\u2018',  # Left Single Quotation Mark ('‘')
        '\u2019',  # Right Single Quotation Mark ('’')
        '\u201C',  # Left Double Quotation Mark ('“')
        '\u201D',  # Right Double Quotation Mark ('”')

        # UTF-16
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

    @pytest.fixture
    def processor(self):
        return StripQuotes()

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
        return TakeAllTruthy(default=None)

    @pytest.mark.parametrize("input_values, expected_output", [
        (
            [True, 123, 'abc', [1, 2, 3]],
            [True, 123, 'abc', [1, 2, 3]]
        ),
        (
            [None, False, '', [], 0],
            None
        ),
        (
            [0, '', False, 7, [], None, 'empty'],
            [7, 'empty']
        ),
        ([], None),
    ])
    def test_process_value(self, processor, input_values, expected_output):
        assert processor(input_values) == expected_output
