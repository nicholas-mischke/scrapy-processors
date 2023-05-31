
# Standard library imports
from typing import Any, Optional, Mapping

# 3rd 🎉 imports
from price_parser import Price

# Local application/library specific imports
from scrapy_processors.base import Processor
from scrapy_processors.common import V


class StringToFloat(Processor):
    """
    Convert a string to a float.
    """

    decimal_places: Optional[int] = None
    input_decimal_separator: Optional[str] = None

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> Any:
        decimal_places, input_decimal_separator = self.unpack_context(context)

        num = Price.fromstring(
            value,
            decimal_separator=input_decimal_separator
        ).amount_float

        return round(num, decimal_places) if decimal_places else num


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
    decimal_places: Optional[int] = None
    keep_trailing_zeros: bool = False

    input_decimal_separator: Optional[str] = None

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> str:

        context = self.unpack_context(context)

        thousands_separator, decimal_separator = context[:2]
        decimal_places, keep_trailing_zeros = context[2:4]
        input_decimal_separator = context[4]

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
        if decimal_places is not None:
            num = f'{num:,.{decimal_places}f}'
        else:
            num = f'{num:,}'

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

    currency_hint: Optional[str] = None
    decimal_separator: Optional[str] = None

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> Price:

        kwargs = self.context_to_kwargs(context, Price.fromstring)
        return Price.fromstring(value, **kwargs)
