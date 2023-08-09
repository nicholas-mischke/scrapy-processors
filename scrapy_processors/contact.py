from bs4 import BeautifulSoup
from typing import Union, Iterable

from phonenumbers import format_number
from phonenumbers import PhoneNumberMatcher, Leniency, PhoneNumberFormat

from scrapy_processors.base import Processor
from scrapy.http import Response

from scrapy.utils.misc import arg_to_iter


class Name(Processor):
    pass

class Phone(Processor):

    region: str = "US"
    lenient = Leniency.VALID
    max_extract: int = 65535

    def process_value(self, value, context):
        """
        Extract phone numbers from a string.
        """
        numbers = []
        for match in self.init_with_context(PhoneNumberMatcher, value, self.region, self.lenient, self.max_extract):
            numbers.append(format_number(match.number, PhoneNumberFormat.E164))
        return numbers


class Email(Processor):

    def process_value(self, value, context):
        ...


class Address(Processor):

    def process_value(self, value, context):
        ...


class Socials(Processor):
    """
    Extract social media links from a list of links.
    """

    domain: Union[str, Iterable[str]] = None

    def process_value(self, value: Response, context):
        domains = arg_to_iter(self.unpack_context(context))

        soup = BeautifulSoup(value.body, "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True)]

        return {
            domain: [link for link in links if domain in link] for domain in domains
        }
