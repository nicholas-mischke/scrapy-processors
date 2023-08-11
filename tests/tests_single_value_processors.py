import pytest
import math
from scrapy.http import TextResponse
from phonenumbers import Leniency, PhoneNumberFormat

from scrapy_processors.single_value_processors import (
    # ... Numeric ...
    ExtractDigits,
    NormalizeNumericString,
    PriceParser,
    StringToFloat,
    # ... Contact ...
    Emails,
    Phone,
    Socials,
)


# ... Numeric ...
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


class TestStringToFloat:
    @pytest.fixture
    def processor(self):
        return StringToFloat()

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


class TestPhone:
    @pytest.fixture
    def processor(self):
        return Phone()

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
