
import scrapy
from pathlib import Path
from scrapy_project.item_loaders import (
    DateTimeItemLoader, NumericStringItemLoader, PriceItemLoader, TextItemLoader,
    JsonItemLoader, JsonItemLoader2
)


html_filepath = 'file://' + str(Path(__file__).parent.parent.parent / "dirty_data.html")


class DirtyDatesSpider(scrapy.Spider):
    name = "dirty"
    start_urls = [html_filepath]  # crawl the local file

    def parse(self, response):

        #######################################################################
        # Dates
        #######################################################################
        datetime_loader = DateTimeItemLoader(selector=response)
        datetime_loader.add_xpath('date', '//p[@id="iso-8601-datetime-1"]/text()')  # 2016-02-03, 17:04:27
        yield datetime_loader.load_item()  # {'date': '2016-02-03, 17:04:27'}

        datetime_loader = DateTimeItemLoader(selector=response)
        datetime_loader.add_xpath('date', '//p[@id="iso-8601-datetime-2"]/text()')  # 2019-12-23, 02:04:18
        yield datetime_loader.load_item()  # {'date': '2019-12-23, 02:04:18'}

        # Different format, so specify context
        context_datetime_loader = DateTimeItemLoader(
            selector=response,
            **{'format': '%A, %B %d, %Y %I%p'} # pass context to change the datetime format
        )
        context_datetime_loader.add_xpath('date', '//p[@id="datetime-context"]/text()') # Friday, December 25, 1992 12PM
        yield context_datetime_loader.load_item() # {'date': '1992-12-25 12:00:00'}

        #######################################################################
        # Numeric & Price
        #######################################################################
        numeric_loader = NumericStringItemLoader(selector=response)
        numeric_loader.add_xpath('number', '//p[@id="num-1"]/text()') # 1 000,00
        yield numeric_loader.load_item()  # {'number': '1000.00'}

        numeric_loader = NumericStringItemLoader(
            selector=response,
            **{'decimal_places': 2}  # Default is None (no rounding)
        )
        numeric_loader.add_xpath('number', '//p[@id="num-2"]/text()') # 100.00101
        yield numeric_loader.load_item()  # {'number': '100'}

        price_loader = PriceItemLoader(selector=response)
        price_loader.add_xpath('price', '//p[@id="price"]/text()') # ¥1,500.50
        yield price_loader.load_item() # {"price": {"amount": "1500.50", "currency": "¥", "amount_text": "1,500.50"}}

        #######################################################################
        # Text
        #######################################################################

        # html_text = (
        #     '  "" This Really    '
        #     '\n\n\n\n'
        #     'is a         \t\t\t\t            messy string  !!!   "'
        # )
        text_loader = TextItemLoader(selector=response)
        text_loader.add_xpath('text', '//p[@id="dirty-string"]/text()')
        yield text_loader.load_item() # {"text": "This really is a messy string!!!"}

        #######################################################################
        # JSON
        #######################################################################

        # html_json = {
        #     "foo": "This is some foo content.",
        #     "bar": {
        #         "sub_bar1": "This is the first sub-bar under bar.",
        #         "sub_bar2": "This is the second sub-bar under bar."
        #     },
        #     "baz": ["item1", "item2", "item3"],
        #     "name": "  \njoHn DOE\"\"  \t\t\t  \n\n\n\n"
        # }

        json_loader = JsonItemLoader(selector=response)
        json_loader.add_xpath('json', '//p[@id="json-1"]/text()')
        yield json_loader.load_item()  # {"json": "This is some foo content."}

        json_loader = JsonItemLoader2(selector=response)
        json_loader.add_xpath('json', '//p[@id="json-1"]/text()')
        yield json_loader.load_item()  # {"json": "John Doe"}
