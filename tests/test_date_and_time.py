
import pytest
from scrapy_processors.date_and_time import *


class TestStringToDateTimeExtraordinaire:

    @pytest.fixture
    def processor(self):
        return StringToDateTimeExtraordinaire()

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
        assert processor(input_value, context)[0] == expected_value
        assert processor.process_value(input_value, context) == expected_value


class TestStringToDateTime:

    @pytest.fixture
    def processor(self):
        return StringToDateTime(input_tz=pytz.UTC)

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
            {'datetime_format': '%B %d, %Y %H:%M:%S'},
            datetime(2022, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        )
    ])
    def test_with_context(self, processor, input_value, context, expected_value):
        assert processor(input_value, context)[0] == expected_value
        assert processor.process_value(input_value, context) == expected_value

    def test_different_timezones(self):
        expected_datetime = datetime(2022, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)

        paris_tz = StringToDateTime(
            input_tz=pytz.timezone('Europe/Paris')
        )
        new_york_tz = StringToDateTime(
            input_tz=pytz.timezone('America/New_York')
        )
        los_angeles_tz = StringToDateTime(
            input_tz=pytz.timezone('America/Los_Angeles')
        )

        assert paris_tz('2022-01-01, 13:00:00')[0] == expected_datetime
        assert new_york_tz('2022-01-01, 07:00:00')[0] == expected_datetime
        assert los_angeles_tz('2022-01-01, 04:00:00')[0] == expected_datetime


class TestStringToDate:

    @pytest.fixture
    def processor(self):
        return StringToDate()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("2022-01-01", date(2022, 1, 1)),
        ("2023-05-15", date(2023, 5, 15))
    ])
    def test(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("input_value, context, expected_value", [
        ('2022-01-01', {}, date(2022, 1, 1)),
        ('January 1, 2022', {'date_format': '%B %d, %Y'}, date(2022, 1, 1))
    ])
    def test_with_context(self, processor, input_value, context, expected_value):
        assert processor(input_value, context)[0] == expected_value
        assert processor.process_value(input_value, context) == expected_value


class TestStringToTime:

    @pytest.fixture
    def processor(self):
        return StringToTime()

    @pytest.mark.parametrize("input_value, expected_value", [
        ("10:30:00", time(10, 30, 0)),
        ("22:45:30", time(22, 45, 30))
    ])
    def test(self, processor, input_value, expected_value):
        assert processor(input_value)[0] == expected_value
        assert processor.process_value(input_value) == expected_value

    @pytest.mark.parametrize("input_value, context, expected_value", [
        ("10:30:00", {}, time(10, 30, 0)),
        ("10:30:00 AM", {'time_format': '%I:%M:%S %p'}, time(10, 30, 0)),
        ("10:30:00 PM", {'time_format': '%I:%M:%S %p'}, time(22, 30, 0)),
    ])
    def test_with_context(self, processor, input_value, context, expected_value):
        assert processor(input_value, context)[0] == expected_value
        assert processor.process_value(input_value, context) == expected_value
