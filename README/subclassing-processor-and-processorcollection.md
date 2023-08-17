
# Defining your own Processors by subclassing Processor and ProcessorCollection

This package provides a convient way to define your own processors by subclassing,
`Processor` and `ProcessorCollection`. These two classes are Abstract classes.

Subclasses of `Processor` must implement the `process_value` method.
Alternatively, subclasses of `Processor` can implement the `__call__` method,
in which case they may or may not need to implement the `process_value` method.

Subclasses of `ProcessorCollection` must implement the `__call__` method.

```python
class SimpleProcessor(Processor):
    def process_value(self, value, **context) -> Any:
        return value + 1

processor = SimpleProcessor()
processor([1, 5, 98]) # Output: [2, 6, 99]

class SimpleProcessorCollection(ProcessorCollection):
    def __call__(self, values, **loader_context) -> List[Any]:
        first_processor = self.wrapped_processors[0]
        second_processor = self.wrapped_processors[1]

        values = [first_processor(value) for value in values]
        return second_processor(values)

processor_collection = SimpleProcessorCollection(SimpleProcessor(), sum)
processor_collection([1, 5, 98]) # Output: 107
```

## Understanding the ProcessorMeta & ProcessorCollectionMeta metaclasses

You will not need to understand how to write metaclasses to use this package, but
here's a short description of what metaclasses are.

A metaclass in Python is a class of a class that defines how a class behaves. A class is itself an instance of a metaclass. While in most object-oriented programming languages, a class defines how an instance of the class behaves, in Python, a metaclass defines how a class behaves. It's a higher-level concept of encapsulation and can be used to apply certain principles or patterns across multiple classes.

Or read this excellent breakdown: https://stackoverflow.com/questions/100003/what-are-metaclasses-in-python#:~:text=The%20metaclass%20is%20determined%20by,the%20class%20to%20instantiate%20it.


### The ProcessorMeta metaclass

This is how you define a Processor subclass in this package:

```python
from scrapy_processor_api import Processor

class MyProcessor(Processor):
    # Class attrs are used to set class' 'default_context'.
    arg1, arg2, arg3 = 10, 20, 30

    # This is an abstract method, which is overridden
    # to provide the logic for the processor.
    def process_value(self, value, **context):
        ...

    # This can be overridden, but typically isn't
    def __call__(self, values, **loader_context):
        ...

```

The metaclass will turn the above class into this:
```python
class MyProcessor(Processor):

    default_context = {"arg1": 10, "arg2": 20, "arg3": 30}

    def __init__(self, arg1=10, arg2=20, arg3=30, **kwargs):
        arg_dict = {"arg1": arg1, "arg2": arg2, "arg3": arg3}
        self.default_context.update(arg_dict)
        self.default_context.update(kwargs)

    @process_value_decorator
    def process_value(self, value, **context):
        ...

    @dunder_call_decorator
    def __call__(self, values, loader_context=None, **_loader_context):
        ...
```
Let's discuss the changes in detail.

1. Collect all non-callable, non-dunder attributes and add them to `default_context`.
2. Enforce the signatures of `process_value` and `__call__` to be valid processor
interfaces. (see section `What's a processor?`)
3. Prohibt `__init__` from being defined, as it's central to dealing with `default_context`.
4. Decorates `process_value` with a decorator that does the following:
    - Takes the `context` passed to the method and convert it into
    `collections.ChainMap(context, self.default_context)` before passing it to the method.
    This prevents the need to pass the full context to the method each time it's called
    from the ItemLoader, by utilizing `default_context`.
5. Decorates `__call__` with a decorator that does the following:
    - Takes the `loader_context` passed to the method and convert it into
    `collections.ChainMap(loader_context, self.default_context)` before passing it to the method.
    This prevents the need to pass the full context to the method each time it's called
    from the ItemLoader, by utilizing `default_context`.
    - Takes the argument passed to `values` and ensures it's a list.
    If a single value is passed, it's wrapped in a list before calling.
    - Modiying the signature of `__call__` to the following:
    ```python
    def call(self, values, loader_context=None, **_loader_context)
    ```

That last one may seem a bit silly. Why enforce a signature, then modify it to something else?

This is because the `itemloaders` package uses `itemloaders.common.wrap_loader_context` throughout its codebase.
The function looks specifically for a keyword parameter named `loader_context`. Using a variable-length keyword
parameter in this case can lead to unexpected and difficult-to-debug results.
```python
def __call__(self, values, loader_context=None)
```

In contrast, it is more Pythonic to use a variable-length keyword parameter, especially when
considering that `loader_context` is an optional dictionary.
```python
def __call__(self, values, **loader_context)
```

To align with this practice while maintaining compatibility, the decorator changes the signature
to accept either `loader_context` or `**loader_context`. The decorator then converts the
arguments passed into a `collections.ChainMap(loader_context, self.default_context)` before
passing it to the method.


### The ProcessorCollectionMeta metaclass

This is how you define a ProcessorCollection subclass in this package:

```python
class MyProcessorCollection(ProcessorCollection):
    arg1, arg2, arg3 = 10, 20, 30

    # This is an abstract method, which is overridden to determine
    # how the processors are called, in what order, or under
    # what conditions.
    def __call__(self, values, **loader_context):
        ...
```

The metaclass will turn the above class into this:
```python
class MyProcessorCollection(ProcessorCollection):
    default_context = {'arg1': 10, 'arg2': 20, 'arg3': 30}

    @dunder_call_decorator
    def __call__(self, values, loader_context=None, **_loader_context):
        ...
```

This metaclass functions almost identically to the `ProcessorMeta` metaclass.
The differences being this class doesn't define a `process_value` method,
and the decorator of the `__call__` method sets the instance attribute
`wrapped_processors`, by using the `loader_context` to "pre-load" the processors
before calling them with the scraped value(s).

### Conclusion on Metaclasses

Metaclasses in Python are a powerful tool that offers flexibility and control over class behavior. The benefits of the above metaclasses can be summarized in four key aspects:

1. **Defining Default Context**: Metaclasses provide a more readable way to define the `default_context`, using class attributes. Additionally they prevent overriding of the `__init__` method, which is essential to the proper functioning of the `default_context`.

2. **Automatic Decorators for Abstract Methods**: By utilizing metaclasses, decorators can be applied to abstract methods automatically across all subclasses. This removes the need for manual repetition and ensures consistency across different parts of the codebase.

3. **Error Handling during Class Definition**: Metaclasses enable validation of subclass signatures at the class definition stage. This helps in catching errors early in the development process, preventing potential issues such as a spider failing to collect scraped data due to a minor mistake.

4. **Signature Modification of `__call__` Method**: Metaclasses allow for the modification of the `__call__` method's signature. This ensures compatibility with the `itemloaders` package and allows for declarations that adhere to Pythonic conventions.
