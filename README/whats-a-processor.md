
## What's A Processor?

In this package and the itemloaders package a processor is a callable that has a specific interface.
The role of this callable is to transform a scraped value into a desired output.

Rules for the interface of a processor:
- The interface must have a parameter that can accept a positional argument.
The argument passed will be the scraped value, or the output from another processor.
- It can be contextless or contextual, allowing it to have a second argument.

1. Contextless interface
    - A processor that does not have a `context` or `loader_context` argument
    ```python
    # Both the itemloaders and scrapy-processors packages recognize this interface.
    # A callable that accepts a single positional argument.
    def processor(value): ...
    ```

2. Contextual interface
    - A processor that has a `context` or `loader_context` argument
    ```python

    # What the itemloader package expects, and the only contextual interface it recognizes.
    # scrapy-processors also recognize this interface.
    def processor(value, loader_context=None): ...

    # More pythonic way of writing the above, and recognized by the scrapy-processors package.
    def processor(value, **loader_context): ...

    # Also recognized by the scrapy-processors package.
    def processor(value, context=None): ...

    # More pythonic way of writing the above, and recognized by the scrapy-processors package.
    def processor(value, **context): ...
    ```

Examples of processors:

```python
from scrapy-processors import Processor

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

# scrapy-processors.Processor subclass
class UpperProcessor(Processor):
    def process_value(self, value):
        return value.upper()

# scrapy-processors.Processor subclass with a context argument
class DateTimeProcessor(Processor):
    format = '%Y-%m-%d %H:%M:%S'
    def process_value(self, value, **context):
        return datetime.strptime(value, context['format'])
```
