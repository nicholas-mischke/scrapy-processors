# What's context?

Context is a mapping object (`dict` or `collections.ChainMap` normally), that can be thought of as largley analgous to `kwargs` in python. The difference
being that `context` is `kwargs` for one or more callables.

## Example of using context

Let's suppose we're scraping the below HTML file with our spider.
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
from scrapy import Spider
from itemloaders import ItemLoader
from scrapy_processors import Processor, TakeFirstTruthy

# Turn a string into a datetime object
class DateTimeProcessor(Processor):
    format = '%Y-%m-%d %H:%M:%S'
    def process_value(self, value, **context):
        return datetime.strptime(value, context['format'])

class DateLoader(ItemLoader):
    date_in = DateTimeProcessor()
    date_out = TakeFirstTruthy()

class DateSpider(Spider):
    # ... rest of code ...

    def parse(self, response):

        loader = DateLoader(selector=response)
        loader.add_xpath('date', '//p[@id="iso-8601-datetime-1"]/text()')
        yield loader.load_item() # {'date': datetime.datetime(1992, 12, 25, 12, 0)}

        # Pass the context to the ItemLoader
        # The ItemLoader will call the processor with the `loader_context`
        loader = DateLoader(selector=response, **{'format': '%A, %B %d, %Y %I%p'})
        loader.add_xpath('date', '//p[@id="datetime-context"]/text()')
        yield loader.load_item() # {'date': datetime.datetime(1992, 12, 25, 12, 0)}

    # ... rest of code ...
```
The above example demonstrates how we pass `loader_context` to a processor,
to adjust the `kwargs` that the processor receives, based on the context of a webpage.


### Changing the context of a Processor

In this package the `Processor` and `ProcessorCollections` can have a `default_context`.
The `default_context` of a class is set using class attributes. To change the
class's `default_context` you'd need to subclass that class. To change the
`default_context` of an instance you can pass in positional or keyword arguments
to the constructor. If using positional arguments pass them in the same order
the class attributes are defined in.

```python
# Same class as above, in the scraping example:
class DateTimeProcessor(Processor):
    format = '%Y-%m-%d %H:%M:%S'
    def process_value(self, value, **context):
        return datetime.strptime(value, context['format'])

# Subclass the DateTimeProcessor to change the default_context
class DateTimeProcessorII(DateTimeProcessor):
    format = '%A, %B %d, %Y %I%p'

# Initialize the DateTimeProcessor with a different default_context,

# Using positional arguments
processor = DateTimeProcessor('%A, %B %d, %Y %I%p')

# Using keyword arguments
processor = DateTimeProcessor(format='%A, %B %d, %Y %I%p')

# Providing additional context that isn't included in the default_context requires keyword arguments.
# Keeping in mind the above example class won't know how to use this context, but a more sophisticated class might.
processor = DateTimeProcessor(format='%A, %B %d, %Y %I%p', timezone='UTC')
```

### What's considered Default Context?

There are two ways in this package for a processor to get it's `default_context`.
One way is the above example (setting them explicitly as class attributes, or passing them to the constructor).
The other is the default values the callables inside the `process_value` method calls.

```python
from scrapy_processors import Processor
class SomeProcessor(Processor):
    def process_value(self, value, **context):
        def inner_func(value, a=1, b=2, c=3):
            return value * (a + b + c)
```

Here the `a, b, c = 1, 2, 3` isn't explicity set in class attributes, or passed to the constructor.
If different values are set in the class attributes, or passed to the constructor they'll be
used to override the default values of the callables. Please note that when passing
arguments to the constructor if they arguments aren't explicitly set in the class attributes
they need to be passed as keyword arguments. In the documentation and docstrings in the source code
the implicit `default_context` is typically referenced as `additional context`.


### Changing the context of an ItemLoader

To change the `loader_context` of an `ItemLoader` instance you can pass keyword arguments to the constructor,
or mutate it's `context` attr directly.
```python
loader = DateLoader(selector=response, **{'format': '%A, %B %d, %Y %I%p'})
loader = DateLoader(selector=response, format='%A, %B %d, %Y %I%p')

loader = DateLoader(selector=response)
loader.context['format'] = '%A, %B %d, %Y %I%p'
```

The above demonstrates how `context` works with a single callable (identical to `kwargs` in python).
Now let's look at how `context` works with multiple callables.

```python
from scrapy-processors import Processor

# For this example let's suppose the Processor class is SubClassed and
# it's process_value method calls two callables

def first_callable(value, a, b, c):
    return value + a + b + c

def second_callable(value, x, y, z):
    return value * x * y * z

def SomeProcessor(Processor):
    # Settings these class attributes, gives the processor a `default_context`
    # {'a': 1, 'b': 2, 'c': 3, 'x': 4, 'y': 5, 'z': 6}
    a, b, c = 1, 2, 3
    x, y, z = 4, 5, 6

    def process_value(self, value, **context):
        # Here using **context directly as **kwargs will raise a TypeError
        # The Processor class provides two methods for splitting the context
        # into kwargs to call a callable or to initailize a class.

        # self.call_with_context(func, **context)
            # If all necessary kwargs are in the context, this will call the callable
        # self.wrap_with_context(func, **context)
            # returns a functools.partial object, that "pre-loads"
            # the callable with the context, exposing an interface that
            # just needs to be passed the scraped value to call the callable.

        wrapped_first_callable = self.wrap_with_context(first_callable, **context)
        first_result = wrapped_first_callable(value)

        return self.wrap_with_context(second_callable, **context)(first_result)
```

We may also have multiple callables if a processor is a ProcessorCollection object.
Let's use a MapCompose instance as an example.

```python
from scrapy_processors import Processor, MapCompose

class FirstProcessor(Processor):
    multiply_by = 2
    def process_value(self, value, **context):
        # The Processor class provide a method for unpacking the context
        # Doing so returns a tuple of values, that are in the same order
        # default_context for the processor was defined in.
        multiply_by, *_ = self.unpack_context(**context)
        return value * multiply_by

class SecondProcessor(Processor):
    add_to = 1
    def process_value(self, value, **context):
        add_to, *_ = self.unpack_context(**context)
        return value + add_to

processor = MapCompose(FirstProcessor(), SecondProcessor())
processor(3, multiply_by=3, add_to=10) # 19
```