
# Scrapy Processors

![License](https://img.shields.io/badge/license-MIT-blue.svg)
[![Python Versions](https://img.shields.io/badge/Python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue)](https://www.python.org/)
<!-- [![codecov](https://codecov.io/gh/nicholas-mischke/scrapy-processors/branch/master/graph/badge.svg)](https://codecov.io/gh/nicholas-mischke/scrapy-processors) -->

Scrapy Processors is a collection of Processor classes meant to work with
the [itemloaders](https://pypi.org/project/itemloaders/) package, commonly used with the [scrapy](https://pypi.org/project/Scrapy/) webscraping framework.

These processors are meant to extend / replace the provided processors in the [itemloaders](https://pypi.org/project/itemloaders/) package.

Additionally the provided Processor and ProcessorCollection classes can be extended to create custom processors.


## Installation

To install Scrapy Processors, simply use pip:

```bash
$ pip install scrapy-processors
```

## What's a processor?

In the Scrapy Processors package a processor is defined as a callable that takes
a scraped value and performs some kind of transformation on it (The T in ETL).

Valid callable signatures for a processor are as followes:
>>> def processor(value): ...
>>> def process(value, loader_context=None): ...
>>> def process(value, **loader_context): ...



Examples of processors that convert a string to uppercase:

```python
# Built-in processor
str.upper

# Lambda processor
lambda x: x.upper()

# Function processor
def upper(value):
    return value.upper()

# Class processor
class Upper:
    def __call__(self, value):
        return value.upper()

```



To understand the potential shortcomings of the above processors, let's define what
`context` is within this package and the itemloaders package.

In a general sense `context` can be thought of as analgous to `kwargs`.
The key differnce being that `context` is `kwargs` for multiple callables.

Here's an example of how `context` is used in the itemloaders package:

Let's suppose we're scraping the below HTML file with our spider
```html
<!DOCTYPE html>
<html>
<head>
    <title>Dates with Context</title>
</head>
<body>
    <div id="div-dates">
        <!-- ISO 8601 Format -->
        <!-- '%Y-%m-%d, %H:%M:%S' -->
        <p id="iso-8601-datetime-1">1992-12-25, 12:00:00</p>
        <!-- Day Month Year Hour Minute Second Timezone -->
        <!-- '%A, %B %d, %Y %p' -->
        <p id="datetime-context">Friday, December 25, 1992 12PM</p>
    </div>
</body>
</html>
```

```python
#python
from scrapy import Spider
from itemloaders import ItemLoader
from scrapy_processors import Processor, TakeFirstTruthy

# Turn a string into a datetime object
class DateTimeProcessor(Processor):
    format = '%Y-%m-%d %H:%M:%S'

    def process_value(self, value, **context):
        return datetime.strptime(value, context['format'])

class DateLoader(ItemLoader):
    default_item_class = dict

    date_in = DateTimeProcessor()
    date_out = TakeFirstTruthy()

class DateSpider(Spider):

    # ... rest of code ...

    def parse(self, response):

        loader = DateLoader(selector=response)
        loader.add_xpath('date', '//p[@id="iso-8601-datetime-1"]/text()')
        yield loader.load_item()

        # Pass the context to the ItemLoader
        # The ItemLoader will call the processor with the `loader_context`
        loader = DateLoader(selector=response, **{'format': '%A, %B %d, %Y %I%p'})
        loader.add_xpath('date', '//p[@id="datetime-context"]/text()')
        yield loader.load_item()

    # ... rest of code ...
```

Here's it's important to understand the Processor class. The processor
uses a metaclass to take the 'format' in the DateTimeProcessor and add it into
a dictionary called `default_context`. When the class is called via the ItemLoader
the `default_context` is merged with the `loader_context` and passed to the
`process_value` method. Using a metaclass means you don't need to pass all keys to
loader_context and you don't need to manually setup the ChainMap(loader_context, default_context)
in all subclasses. It's instead done for you, automatically.




```python

class Processor(ContextMixin, metaclass=ProcessorMeta):
    def process_value(self, value, **context) -> Any:
        ...

    def __call__(self, values, **loader_context) -> List[Any]:
        return [self.process_value(value, **loader_context) for value in values]

```

## Extending the Processor class


## Usage

Here is an overview of the processors available in the package:

`MapCompose`: A processor that allows you to specify a list of callables that will be applied sequentially to a value, or to each value in a list of values.
    It supports functions (regular functions, lambda or methods), objects with a `__call__` method or classes that once initialized return an object with a `__call__` method.
    This class inherits from itemloaders.processors.MapCompose and overrides its constructor and defines `__add__`.
- `Processor`: A base class for creating custom processors. Subclasses of `Processor` should implement the `process_value` method.
- `EnsureEncoding`: A processor that converts a string to a specified encoding, defaults to utf-8 & ignores errors.
- `NormalizeWhitespace`: A processor that normalizes whitespace in a string by
    removing zero-width spaces, replacing multiple whitespaces with a single whitespace, removing leading whitespace in front of punctuation and finally removing leading/trailing whitespaces.
    default punctuation=(',', '.', '!', '?', ';', ':')
- `PriceParser`: A processor that converts a string representing a price to a `Price` object using the `price_parser` library.
- `RemoveHTMLTags`: A processor that removes HTML tags from a string using the `BeautifulSoup` library.
- `Demojize`: A processor that replaces Unicode emojis in a string with emoji shortcodes using the `emoji` library.
- `RemoveEmojis`: A processor that removes emojis from a string using the `emoji` library.
- `StripQuotes`: A processor that removes any number of leading/trailing quotes or tick marks from a string.
- `StringToDateTime`: A processor that converts a string representing a date and time to a `datetime.datetime` object. default format='%Y-%m-%d, %H:%M:%S'
- `StringToDate`: A processor that converts a string representing a date to a `datetime.date` object. default format='%Y-%m-%d'
- `StringToTime`: A processor that converts a string representing a time to a `datetime.time` object. default format='%H:%M:%S'
- `TakeAll`: A processor that returns all values passed to it. This is a renaming of the built-in `Identity` processor.
- `TakeAllTruthy`: A processor that returns all truthy values passed to it. It also accepts a default value to return if no values are truthy.



```python
# example.py
from scrapy_processors import EnsureEncoding, MapCompose, NormalizeWhitespace, Processor


# Example usage of MapCompose
processor = MapCompose(NormalizeWhitespace, str.upper)
result = processor(['Hello   , World!\n', 'Hi!'])
print(result)  # Output: ['HELLO, WORLD!', 'HI!']

# Example usage of EnsureEncoding processor
processor = EnsureEncoding(encoding='utf-8', ignore=True)
result = processor('Hello')
print(result)  # Output: 'Hello'

# Example usage of custom Processor subclass
class MyProcessor(Processor):
    def process_value(self, value):
        return value + ' processed'

processor = MyProcessor()
result = processor(['Hello', 'World'])
print(result)  # Output: ['Hello processed', 'World processed']
```

## Opening an Issue

If you encounter a problem with the project or have a feature request, you can open an issue to let us know.

To open an issue, please follow these steps:

1. Go to the [Issues](https://github.com/nicholas-mischke/scrapy-processors/issues) tab on the github repository page.
2. Click on the "New Issue" button.
3. Provide a descriptive title for the issue.
4. In the issue description, provide detailed information about the problem you are experiencing or the feature you are requesting.
5. If applicable, include steps to reproduce the problem or any relevant code examples.
6. Add appropriate labels to categorize the issue (e.g., bug, enhancement, documentation).
7. Click on the "Submit new issue" button to create the issue.

Once you have opened an issue, our team will review it and provide assistance or discuss the requested feature.

Note: Before opening a new issue, please search the existing issues to see if a similar issue has already been reported. This helps avoid duplicates and allows us to focus on resolving existing problems.

## Contributing

Thank you for considering contributing to this project! We welcome your contributions to help make this project better.

To contribute to this project, please follow these steps:

1. Fork the repository by clicking on the "Fork" button at the top of the repository page. This will create a copy of the repository in your GitHub account.
2. Clone the forked repository to your local machine using Git:

    ```
    $ git clone https://github.com/your-username/scrapy-processors.git
    ```

3. Create a new branch for your changes:

    ```
    $ git checkout -b feature
    ```

4. Make your desired changes to the codebase.
5. Commit your changes with descriptive commit messages:

    ```
    $ git commit -m "Add new feature"
    ```

6. Push your changes to your forked repository:

    ```
    $ git push origin feature
    ```

7. Open a pull request (PR) from your forked repository to the original repository's `master` branch.
8. Provide a clear and descriptive title for your PR and explain the changes you have made.
9. Wait for the project maintainers to review your PR. You may need to make additional changes based on their feedback.
10. Once your PR is approved, it will be merged into the main codebase. Congratulations on your contribution!

If you have any questions or need further assistance, feel free to open an issue or reach out to the project maintainers.

Happy contributing!

## License
This project is licensed under the MIT License. See the LICENSE file for more details.