
# Standard library imports
from datetime import datetime, date, time
from typing import Any, Callable, Dict, List, Mapping, Optional, Union

# 3rd 🎉 imports
import dateparser
from dateparser.conf import Settings
import pytz
from tzlocal import get_localzone

# Local application/library specific imports
from scrapy_processors.base import Processor
from scrapy_processors.common import V


class StringToDateTimeExtraordinaire(Processor):
    """
    https://pypi.org/project/dateparser/
    """

    date_formats: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    locales: Optional[List[str]] = None
    region: Optional[str] = None
    settings: Union[Settings, Dict[str, Any]] = None  # Or settings instance
    detect_languages_function: Optional[Callable[[
        str, float], List[str]]] = None

    output_tz: str = pytz.UTC

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> datetime:

        kwargs = self.context_to_kwargs(context, dateparser.parse)
        datetime_obj = dateparser.parse(value, **kwargs)
        return datetime_obj.astimezone(self.output_tz)


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
    input_tz: str = pytz.timezone(str(get_localzone()))
    output_tz: str = pytz.UTC

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> datetime:

        datetime_format, input_tz, output_tz = self.unpack_context(context)

        # Get datetime object from string
        datetime_obj = datetime.strptime(value, format)

        # Convert to input timezone
        datetime_obj = input_tz.localize(datetime_obj)

        # Standardize to UTC (or other output timezone)
        return datetime_obj.astimezone(output_tz)


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

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
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

    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> time:
        # Get time object from string
        return datetime.strptime(value, context['format']).time()
