# Standard library imports
from collections import ChainMap
from copy import deepcopy
from functools import wraps
from inspect import _empty as EMPTY
from inspect import isclass, signature
from inspect import Parameter, Signature

from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

# Third-party library imports
from itemloaders.utils import arg_to_iter

V = TypeVar("V")  # Single input value type
Values = Union[V, Iterable[V]]  # Single value or iterable of values
Context = Union[Mapping[str, Any], ChainMap]


class MetaMixin(type):
    @staticmethod
    def param_is_pos(param):
        return str(param.kind).upper() not in ("KEYWORD_ONLY", "VAR_KEYWORD")

    def __new__(
        cls, name: str, bases: tuple, namespace: Dict[str, Any]
    ) -> "ProcessorMeta":
        cls_attrs = {
            k: v
            for k, v in namespace.items()
            if not k.startswith("__") and not callable(v)
        }

        msg = "The class attribute '{}' is reserved for the ItemLoader class, please choose a different name."
        if "item" in cls_attrs:
            raise ValueError(msg.format("item"))
        if "selector" in cls_attrs:
            raise ValueError(msg.format("selector"))

        namespace["default_context"] = cls_attrs
        return super().__new__(cls, name, bases, namespace)

    @staticmethod
    def prepare_dunder_call(cls_name: str, func: Callable) -> Callable:
        """
        Prepare the __call__ method.

        @chainmap_context
        def __call__(self, values, loader_context): ...
        """
        sig = signature(func)
        params = list(sig.parameters.values())

        self = params.pop(0)
        values = params.pop(0)
        loader_context = params.pop(0)

        # Exception msg
        msg = f"Invalid signature `{cls_name}.__call__{sig}`. "

        # Validate 'values' parameter
        if not MetaMixin.param_is_pos(values):
            raise TypeError(
                msg
                + f"The first parameter must be positional, not {str(values.kind).upper()}"
            )

        # Validate 'loader_context' parameter
        if loader_context.name != "loader_context":
            raise TypeError(
                msg
                + f"The second parameter must be named `loader_context`, not `{loader_context.name}`"
            )

        for param in params:
            if param.default == EMPTY:
                raise ValueError(
                    msg
                    + "The method can take other parameters besides `values` and `loader_context`, but they must be optional parameters."
                )

        def decorator(func):
            """
            Pass the loader_context to the method as a ChainMap.
            The loader_context takes priority over default_context.

            If a single value is passed to values, it's placed into a list.
            """

            @wraps(func)
            def wrapper(self, values, loader_context=None, **kwargs):
                return func(
                    self,
                    arg_to_iter(values),
                    ChainMap(loader_context or {}, self.default_context),
                    **kwargs,
                )

            return wrapper

        return decorator(func)


class ProcessorMeta(MetaMixin):
    """
    From this:

    class MyProcessor(Processor):

        arg1 = 10
        arg2 = 20
        arg3 = 30

        def process_value(self, value, context):
            ...

        def __call__(self, values, loader_context):
            ...

    To this:

    class MyProcessor(Processor):

        default_context = {"arg1": 10, "arg2": 20, "arg3": 30}

        def __init__(self, arg1, arg2, arg3, **kwargs):
            # Update default context with *args and **kwargs passed to constructor

            self.default_context["arg1"] = arg1
            self.default_context["arg2"] = arg2
            self.default_context["arg3"] = arg3
            self.default_context.update(kwargs)

        @chainmap_context # prioritizes context over default_context
        def process_value(self, value, context):
            # The first parameter after self can be named anything but must be positional

            # The second parameter after self must be named context

            # If additional parameters are present, they must be optional
            ...

        @chainmap_context    # priortizes loader_context over default_context
        @to_iterable         # If a single value is passed, it's placed into a list
        def __call__(self, values, loader_context):
            # The first parameter after self can be named anything but must be positional

            # The second parameter after self must be named loader_context
            # any other name and it will be ignored by the itemloaders package

            # If additional parameters are present, they must be optional
            ...
    """

    @staticmethod
    def prepare_process_value(cls_name: str, func: Callable) -> Callable:
        """
        Prepare the process_value method.

        @chainmap_context
        def process_value(self, value, **context): ...
        """
        sig = signature(func)
        params = list(sig.parameters.values())

        self = params.pop(0)
        value = params.pop(0)
        context = params.pop(-1)

        # Exception msg
        msg = f"Invalid signature `{cls_name}.process_value{sig}`. "

        # The first parameter is typically named `value`, but can take any name.
        # Must be positional
        if not MetaMixin.param_is_pos(value):
            raise TypeError(
                msg
                + f"The first parameter must be positional, not {str(value.kind).upper()}"
            )

        # There must be a variable keyword parameter, typically named `context`.
        if str(context.kind).upper() != "VAR_KEYWORD":
            raise TypeError(
                msg
                + "There must be a variable length keyword parameter. Typically named `context`, declared as **context."
            )

        for param in params:
            if param.default == EMPTY:
                raise ValueError(
                    msg
                    + "The method can take other parameters besides `values` and `loader_context`, but they must be optional parameters."
                )

        def decorator(func):
            """
            Passes the context to the function as a ChainMap.
            The context takes priority over default_context.
            """

            @wraps(func)
            def wrapper(self, *args, **context):
                return func(self, *args, **ChainMap(context, self.default_context))

            return wrapper

        return decorator(func)

    def __init__(cls, name: str, bases: tuple, namespace: dict):
        if "__init__" in namespace:
            raise TypeError(
                f"{cls.__name__} class should not define __init__. "
                "The __init__ method is reserved for the ProcessorMeta metaclass. "
                "It takes the arguments passed to the Processor subclass's constructor "
                "and uses them to update the default_context attr."
            )

        if "process_value" in namespace:
            setattr(
                cls,
                "process_value",
                ProcessorMeta.prepare_process_value(
                    cls.__name__, namespace["process_value"]
                ),
            )

        if "__call__" in namespace:
            setattr(
                cls,
                "__call__",
                ProcessorMeta.prepare_dunder_call(cls.__name__, namespace["__call__"]),
            )

        super().__init__(name, bases, namespace)

    def __call__(cls, *args, **kwargs) -> Any:
        """
        Create an instance of the Processor subclass.

        Use arguments passed to the constructor to update the default_context.
        """
        default_context = deepcopy(cls.default_context)

        # Dynamically create a function signature to check for TypeErrors
        params = [
            Parameter(
                name, Parameter.POSITIONAL_OR_KEYWORD, default=default_context[name]
            )
            for name in default_context.keys()
        ]

        existing_param_names = {param.name for param in params}
        for key, value in kwargs.items():
            if key not in existing_param_names:
                params.append(
                    Parameter(key, Parameter.POSITIONAL_OR_KEYWORD, default=value)
                )

        sig = Signature(params)
        bound_args = sig.bind(*args, **kwargs).arguments

        # Update the default_context with the bound arguments
        default_context.update(bound_args)

        instance = super().__call__()
        instance.default_context = default_context
        return instance


class ProcessorCollectionMeta(MetaMixin):
    """
    From this:

    class MyProcessorCollection(ProcessorCollection):

        stop_on_none = False
        default = None

        def __call__(self, values, loader_context):
            ...

    To This:

    class MyProcessorCollection(ProcessorCollection):

        default_context = {"stop_on_none": False, "default": None}

        def __init__(self, *processors, **default_context):
            self.processors = list(processors)
            self.default_context.update(default_context)

        @chainmap_context
        @to_iterable
        def __call__(self, values, loader_context):
            # The first parameter after self can be named anything but must be positional

            # The second parameter after self must be named loader_context
            # any other name and it will be ignored by the itemloaders package

            # If additional parameters are present, they must be optional
            ...
    """

    def __init__(cls, name: str, bases: tuple, namespace: dict):
        if "__init__" in namespace:
            raise TypeError(
                f"{cls.__name__} class should not define __init__. "
                "The __init__ method is reserved for the ProcessorCollectionMeta metaclass. "
                "The variable length positional arguments passed to the constructor "
                "become the instances processors. The variable length keyword arguments "
                "are used to update the instances default_context attr."
            )

        if "__call__" in namespace:
            setattr(
                cls,
                "__call__",
                ProcessorMeta.prepare_dunder_call(cls.__name__, namespace["__call__"]),
            )

        super().__init__(name, bases, namespace)

    def __call__(cls, *args, **kwargs) -> Any:
        """
        Create an instance of the Processor subclass.

        Use arguments passed to the constructor to update the default_context.
        """
        processors = list(args)

        default_context = deepcopy(cls.default_context)
        default_context.update(kwargs)

        instance = super().__call__()
        instance.processors = processors
        instance.default_context = default_context
        return instance


class ContextMixin:
    @property
    def cls_name(self):
        """
        The name of the processor subclass.

        :return: The name of the processor subclass.
        """
        return self.__class__.__name__

    def unpack_context(
        self,
        *additional_keys: str,
        **context: Context,
    ) -> Union[Any, Tuple[Any, ...]]:
        """
        If loader_context can be seen as a master kwargs if the processor
        is in a ProcessorCollection.

        Extract the values from context that correspond to the keys in
        default_context and additional_keys.
        """
        context = ChainMap(context, self.default_context)

        relevent_keys = tuple(self.default_context.keys()) + additional_keys
        relevent_values = tuple(context[key] for key in relevent_keys)

        # If there is only one value, return it without the tuple
        if len(relevent_values) == 1:
            return relevent_values[0]
        return relevent_values

    def call_with_context(self, func: Union[Type, Callable], **context: Context):
        """
        default_context can be viewed as master kwargs, for the functions
        nested in the process_value method.

        loader_context can be viewed as master kwargs for all the functions
        in a processor collection.

        This method unpacks the relevant keys from the context passed
        and calls the function with them as kwargs.
        """
        context = ChainMap(context, self.default_context)

        cls = None
        if isclass(func):
            cls = func
            func = cls.__init__

        parameters = list(signature(func).parameters.keys())

        if cls:
            parameters.pop(0)
            return cls(
                **{name: context[name] for name in parameters if name in context}
            )
        return func(**{name: context[name] for name in parameters if name in context})


class Processor(ContextMixin, metaclass=ProcessorMeta):
    """
    A Processor class that uses an optional context to process values.

    The Processor class is an abstract class that provides a structure for creating data
    cleaning or transformation functionalities. Each Processor subclass should define
    a specific data processing method in its `process_value` method, which might
    optionally use a context.

    The `process_value` method MUST be overridden in subclasses.

    When an instance of a `Processor` subclass is invoked (called as a function) with
    an iterable of values and an optional context, it processes each value using the
    `process_value` method and returns a list of results. Single values are also accepted
    and processed in the same manner.

    Example:

    import random

    class ScrambleProcessor(Processor):
        random_order = False
        reverse = False

        def _process_value(self, value, context):
            if context['reverse']:
                return value[::-1]
            elif context['random_order']:
                return "".join(random.shuffle(list(value)))
            else:
                return value

    # Values passed as loader_context from ItemLoader
    processor = ReverserProcessor() # {'random_order': False, 'reverse': False}
    values = ["hello", "world"]

    print(processor(values)) # Output: ['hello', 'world']
    print(processor(values, {'reverse': True})) # Output: ['olleh', 'dlrow']
    print(processor(values, {'random_order': True})) # Output: ['ehllo', 'dlorw']
    """

    # The metaclass decorates this method to insure `context`
    # is passed as a chainmap with `context` taking priority over `default_context`
    def process_value(self, value, **context) -> Any:
        """
        Process a single value using an optional context.

        This method is central to the functionality of the Processor class and should define
        the specific data cleaning or transformation functionality in each subclass.

        :param value: The value to process.
        :param context: An optional context to use when processing the value. It can be a dictionary or a ChainMap.
        :return: The processed value.

        :raises NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `process_value` method. "
            "This method should be overridden in all subclasses to provide the processing logic."
        )

    # The metaclass decoractes this method with iter_values_chainmaped_context
    # It also insure that the `loader_context` is passed as the second argument
    # rather than `context` so that the itemloaders package can use it.
    def __call__(self, values, loader_context=None) -> List[Any]:
        """
        Process a collection of values using an optional context.

        This method uses the `process_value` method to process each value and returns a list of results.
        It's responsible for passing the context to the `process_value` method.

        :param values: An iterable of values to process. If a single value is
                       provided, it is converted into an iterable.
        :param loader_context: An optional context to use when processing the
                               values. It can be either a dictionary or a
                               ChainMap. If provided, it is merged with the
                               default context where loader_context has
                               priority.
        :return: A list of processed values.
        """
        return [self.process_value(value, **loader_context) for value in values]

    def __str__(self):
        default_context_str = ", ".join(
            [f"{k}={v}" for k, v in self.default_context.items()]
        )
        return f"{self.cls_name}({default_context_str})"

    # When in a processor collection class, helps with get, set, del methods
    def __eq__(self, other):
        if type(self) is type(other) and self.default_context == other.default_context:
            return True
        return False


class ProcessorCollection(ContextMixin, metaclass=ProcessorCollectionMeta):
    """
    Contains a collection of processors which are called sequentially
    when the ProcessorCollection instance is called as a function.

    Provides a list like interface, except that mutating methods return
    a new instance of the ProcessorCollection subclass without mutating
    the original instance.
    """

    def __call__(self, values, loader_context=None) -> List[Any]:
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `__call__` method. "
            "This method should be overridden in all subclasses of ProcessorCollection "
            "to provide the processing logic."
        )

    def _merge_default_context(self, other, method="extend"):
        self_context = self.default_context
        other_context = other.default_context

        shared_keys = tuple(set(self_context.keys()) & set(other_context.keys()))
        self_values = tuple(self_context[key] for key in shared_keys)
        other_values = tuple(other_context[key] for key in shared_keys)

        if self_values == other_values:
            return {**self_context, **other_context}

        exception_msg = (
            f"Cannot call `{method}` method on {self.__class__.__name__} instance with {other.__class__.__name__} instance. "
            "Shared keys in default_context attrs have different values. "
        )

        mismatched_keys = [
            key for key in shared_keys if self_context[key] != other_context[key]
        ]

        if mismatched_keys:
            details = ", ".join(
                f"Key: {key}, self: {self_context[key]}, other: {other_context[key]}"
                for key in mismatched_keys
            )
            exception_msg += details

        raise ValueError(exception_msg)

    def extend(self, processors):
        """
        Pass either an iterable of processors, or another ProcessorCollection instance.

        Returns a new instance of the ProcessorCollection subclass with the new processors
        without mutating the original instance.
        """
        if isinstance(processors, ProcessorCollection):
            return self.__class__(
                *self.processors,
                *processors.processors,
                **self._merge_default_context(processors, method="extend"),
            )

        return self.__class__(*self.processors, *processors, **self.default_context)

    def __add__(self, processor):
        """
        Add one or more processors to the end of the processors list.
        """
        if isinstance(processor, ProcessorCollection):
            return self.__class__(
                *self.processors,
                *processor.processors,
                self._merge_default_context(processor, method="__add__"),
            )

        processors = self.processors.copy() + list(arg_to_iter(processor))
        return self.__class__(*processors, **self.default_context)

    def __str__(self) -> str:
        def processor_to_str(processor):
            if isinstance(processor, (Processor, ProcessorCollection)):
                return str(processor)
            else:
                # str.upper, etc
                name = processor.__qualname__
                if "<lambda>" in name:
                    return "lambda_processor"
                    # return name.split(".")[0]
                return name

        processors_str = ", ".join(
            [processor_to_str(processor) for processor in self.processors]
        )

        return f"{self.cls_name}({processors_str})"

    def __eq__(self, other) -> bool:
        return (
            type(self) is type(other)
            and self.default_context == other.default_context
            and self.processors == other.processors
        )

    def __getattr__(self, name):
        """
        delegates attribute/method calls to the internal processors list,
        and returns a new object when a list-mutating method is called
        """
        attr = getattr(self.processors, name)

        if callable(attr):

            @wraps(attr)
            def wrapper(*args, **kwargs):
                processors = self.processors.copy()

                attr = getattr(processors, name)
                result = attr(*args, **kwargs)

                if processors == self.processors:  # non-mutating method
                    return result
                else:  # mutating method
                    return self.__class__(*processors, **self.default_context)

            return wrapper
        else:
            return attr  # non-callable attribute
