
import pytest
import math
from scrapy_processors.numeric import *


class TestStringToFloat:

    @pytest.fixture
    def processor(self):
        return StringToFloat()

    @pytest.mark.parametrize("input_values, expected_output", [
        ('1', 1.0),
        ('1.0', 1.0),
        ('1.5', 1.5),
        ('1,000', 1000.0),
    ])
    def test(self, processor, input_values, expected_output):
        assert processor(input_values)[0] == expected_output

    @pytest.mark.parametrize("input_values, context, expected_output", [
        ('100.000', {'input_decimal_separator': '.'}, 100.0),
    ])
    def test_with_loader_context(
        self,
        processor,
        input_values,
        context,
        expected_output
    ):
        assert processor(input_values, context)[0] == expected_output


class TestNormalizeNumericString:

    # thousands_separator: comma, period, space or empty string
    # decimal_separator: comma or period
    # Test all combinations where they're not the same separator
    @pytest.mark.parametrize("processor_kwargs, input_value, expected_value", [
        (
            {"thousands_separator": ",", "decimal_separator": "."},
            "1000000.75", "1,000,000.75"
        ),
        (
            {"thousands_separator": ".", "decimal_separator": ","},
            "1000000.75", "1.000.000,75"
        ),
        (
            {"thousands_separator": " ", "decimal_separator": "."},
            "1000000.75", "1 000 000.75"
        ),
        (
            {"thousands_separator": " ", "decimal_separator": ","},
            "1000000.75", "1 000 000,75"
        ),
        (
            {"thousands_separator": "", "decimal_separator": "."},
            "1000000.75", "1000000.75"
        ),
        (
            {"thousands_separator": "", "decimal_separator": ","},
            "1000000.75", "1000000,75"
        ),
    ])
    def test_seperators(self, processor_kwargs, input_value, expected_value):
        processor = NormalizeNumericString(**processor_kwargs)
        assert processor(input_value)[0] == expected_value

    @pytest.mark.parametrize("processor_kwargs, input_value, expected_value", [
        ({'decimal_places': 0}, "1000.75", "1001"),
        ({'decimal_places': 1}, "1000.75", "1000.8"),
        ({'decimal_places': 2}, "1000.75", "1000.75"),
        ({'decimal_places': 3}, "1000.75", "1000.75"),
    ])
    def test_rounding(self, processor_kwargs, input_value, expected_value):
        processor = NormalizeNumericString(**processor_kwargs)
        assert processor(input_value)[0] == expected_value

    @pytest.mark.parametrize("processor_kwargs, input_value, expected_value", [
        (
            {
                'keep_trailing_zeros': False,
                'input_decimal_separator': '.'
            },
            "1,000.000",
            "1000"
        ),
        (
            {
                'decimal_places': 2,
                'keep_trailing_zeros': True,
                'input_decimal_separator': '.'

            },
            "1,000.000",
            "1000.00"  # Rounded to 2 decimal places
        ),
    ])
    def test_with_loader_context(self, processor_kwargs, input_value, expected_value):
        processor = NormalizeNumericString(**processor_kwargs)
        assert processor(input_value)[0] == expected_value


class TestPriceParser:

    @pytest.fixture
    def processor(self):
        return PriceParser()

    @pytest.mark.parametrize(
        "input_value, context, expected_amount, expected_currency",
        [
            ("USD 100.00", {}, 100.00, "USD"),      # United States Dollars
            ("EUR 50.99", {}, 50.99, "EUR"),        # Euros
            ("£75.50", {}, 75.50, "£"),           # British Pound Sterling
            ("$250,000.00", {}, 250000.00, "$"),  # United States Dollars
            ("€22,90", {'decimal_separator': ','},
             22.90, "€"),           # Euros
            ("¥1,500.50", {}, 1500.50, "¥"),      # Japanese Yen
        ],
    )
    def test_process_value(
        self, processor,
        input_value, context, expected_amount, expected_currency
    ):
        # Process the value
        price = processor(input_value, context)[0]

        # Assert the attributes of the Price object
        assert math.isclose(price.amount, expected_amount, rel_tol=1e-9)
        assert price.currency == expected_currency

    @pytest.mark.parametrize(
        "input_value, context, expected_amount, expected_currency",
        [
            ("100.00", {'currency_hint': 'USD'}, 100.00, "USD"),
            ("50.99", {'currency_hint': 'EUR'}, 50.99, "EUR"),
            ("75.50", {'currency_hint': '£'}, 75.50, "£"),
        ]
    )
    def test_with_loader_context(self, processor, input_value, context, expected_amount, expected_currency):
        processor = PriceParser(**context)

        price = processor(input_value)[0]
        assert math.isclose(price.amount, expected_amount, rel_tol=1e-9)
        assert price.currency == expected_currency


class TestExtractDigits:

    @pytest.fixture
    def processor(self):
        return ExtractDigits()

    def wrap_in_text(self, value):
        return f'This is some text {value} This is some more text'

    @pytest.mark.parametrize("input_value", [
        "1000",
        "1,000",
        "1.000",
        "1,000.12",
        "1.000,12",
    ])
    def test_process_value(self, processor, input_value):
        assert processor.process_value(self.wrap_in_text(input_value)) == [input_value]

    @pytest.mark.parametrize("input_value, context", [
        ("1 000.12", [' ', '.']),
        ("123", None),
        ("123-456-7890", ['-']),  # phone number
        ("1234 5678 9012 3456", [' ']),  # credit card number
        ("2023-06-19 at 12:30", [' at ', '-', ':']),  # date, time or datetime
        ("1:000-12", [':', '-']),  # other format
    ])
    def test_with_loader_context(self, processor, input_value, context):
        assert processor.process_value(
            self.wrap_in_text(input_value),
            context={'separators': context}
        ) == [input_value]
