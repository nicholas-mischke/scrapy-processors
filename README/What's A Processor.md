
## What's A Processor?

In the context of the itemloaders package a processor is a callable that has a specific interface. This interface can have two forms:
1. A single positional argument (typically declared as `value`)
2. A single positional argument and a `loader_context` argument

Either interface also allows for any number of optional parameters.

Here are examples of valid processors:

```
# valid processors with a single positional argument

# Built-in function
str.upper

# lambda function
lambda value: value.upper()

# user-defined function
def upper(value):
    return value.upper()

# class with a __call__ method
class Upper:
    def __call__(self, value):
        return value.upper()
```

```
# valid processors with a single positional argument and a loader_context argument

from datetime import datetime

# lambda
lambda value, loader_context: datetime.strptime(value, loader_context['format'])

# user-defined function
def parse_date(value, loader_context):
    return datetime.strptime(value, loader_context['format'])

# class with a __call__ method
class ParseDate:
    def __call__(self, value, loader_context):
        return datetime.strptime(value, loader_context['format'])
```

What happens when you want to use a function that has more than one required
parameter?

We're able to "wrap" these functions to provide a better interface

```
# chaning interface of a function to make it a valid processor

def silly_function(value, param1, param2):
    return value + param1 + param2

def processor(value, loader_context):
    return silly_function(
        value,
        loader_context.get('param1', 'default_value')
        loader_context.get('param2', 'default_value')
    )

class Processor:
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2

    def __call__(self, value):
        return silly_function(value, self.param1, self.param2)
```

This package provides a convenient way to wrap functions to make them valid processors. It also provides a set of built-in processors that can be used out of the box.


