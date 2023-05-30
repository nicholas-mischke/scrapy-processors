
# Standard library imports
from collections import ChainMap
from copy import deepcopy
import inspect
from functools import wraps
from inspect import Parameter, Signature
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, Union, Tuple, TypeVar, Mapping

# itemloaders imports
from itemloaders.utils import arg_to_iter, get_func_args

# scrapy_processors imports
from scrapy_processors.common import V, ProcessorType, ProcessorCollectionType
from scrapy_processors.utils import get_processor, wrap_context


def iter_values_decorator(method: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to ensure the that the arg passed to a value/values parameter
    is always an iterable.
    str and dict aren't considered iterables, and will be wrapped in a list.

    :param method: The method to decorate.
    :return: The decorated method.
    """
    
    signature = inspect.signature(method)

    @wraps(method)
    def wrapper(self, *args, **kwargs) -> Callable[..., Any]:

        bound = signature.bind(self, *args, **kwargs)
        bound.apply_defaults()
        kwargs = bound.arguments
        
        if 'value' in kwargs:
            kwargs['value'] = arg_to_iter(kwargs['value'])
        elif 'values' in kwargs:
            kwargs['values'] = arg_to_iter(kwargs['values'])
        
        return method(**kwargs)

    return wrapper


def chainmap_context_decorator(method: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to ensure the context is always a ChainMap, where loader_context takes priority
    over default_context.

    :param method: The method to decorate.
    :return: The decorated method.
    """

    signature = inspect.signature(method)

    @wraps(method)
    def wrapper(self, *args, **kwargs) -> Callable[..., Any]:
    
        bound = signature.bind(self, *args, **kwargs)
        bound.apply_defaults()
        kwargs = bound.arguments
        
        if 'context' in kwargs:
            context = kwargs.get('context', None)

            if context is None:
                kwargs['context'] = ChainMap(self.default_context)
            else:
                kwargs['context'] = ChainMap(context, self.default_context)

        if 'loader_context' in kwargs:
            loader_context = kwargs.get('loader_context', None)
            
            if loader_context is None:
                kwargs['loader_context'] = ChainMap(self.default_context)
            else:
                kwargs['loader_context'] = ChainMap(loader_context, self.default_context)
        
        return method(**kwargs)

    return wrapper


def iter_values_chainmap_context_decorator(method: Callable[..., Any]) -> Callable[..., Any]:
    return iter_values_decorator(chainmap_context_decorator(method))


class ProcessorMeta(type):
    """
    Metaclass for Processor classes.

    This metaclass automatically collects class variables into the 
    default_context attribute. When a new instance of the Processor 
    subclass is created, the default_context is updated with the 
    arguments passed to the class constructor.

    Attributes:
        default_context (Dict[str, Any]): The default loader context for the processor, 
            which will be updated with instance-specific arguments upon initialization.

    Example:

        class Processor(metaclass=ProcessorMeta):
            pass

        class ExampleProcessor(Processor):
            some_arg: int = 10

        print(ExampleProcessor().default_context)  # {'some_arg': 10}
        print(ExampleProcessor(some_arg=20).default_context)  # {'some_arg': 20}

    """

    def __new__(mcs: Type, name: str, bases: tuple, attrs: Dict[str, Any]) -> 'ProcessorMeta':
        """
        Processor subclass class attributes turned into default_context.
        """
        attrs["default_context"] = {
            key: value
            for key, value in attrs.items()
            if not key.startswith("__") and not callable(value)
        }
        return super().__new__(mcs, name, bases, attrs)

    def __init__(cls: Type, name: str, bases: tuple, attrs: dict):
        """
        Prevents Processor subclasses from defining __init__().
        This prevents the Processor __init__() from being overridden, 
        which is used to update the default_context.
        """

        for attr_name, attr_value in attrs.items():
            if attr_name == "__call__":
                setattr(
                    cls,
                    attr_name,
                    iter_values_chainmap_context_decorator(attr_value)
                )
                # If the __call__ method is defined, make sure has loader_context
                # rather than context as a parameter
                parameters = get_func_args(attr_value)
                if "context" in parameters and "loader_context" not in parameters:
                    raise TypeError(
                        f"{cls.__name__}.__call__() should have `loader_context` rather than `context` as a parameter. "
                        "The itemloaders package looks specifically for `loader_context`, for a number of internal processes. "
                    )
            elif attr_name == "process_value":
                setattr(
                    cls,
                    attr_name,
                    chainmap_context_decorator(attr_value)
                )
            elif attr_name == "__init__":
                raise TypeError(
                    f"{cls.__name__} class should not define __init__(). "
                    "It overrides the MetaClass's functionality, which is used to "
                    "set the instance's default_context attr from class attrs, "
                    "And the arguments passed to the class constructor. "
                )

        super().__init__(name, bases, attrs)

    def __call__(cls: Type, *args: Any, **kwargs: Any) -> Any:
        """
        Use the args and kwargs to update the default_context.
        """
        # deepcopy the class default_context
        default_context = deepcopy(cls.default_context)

        # To check for TypeErrors, dynamically create a function signature
        #  ProcessorSubClass() takes 3 positional arguments but 4 were given
        #  ProcessorSubClass() got multiple values for argument 'arg'
        params = [
            Parameter(
                name,
                Parameter.POSITIONAL_OR_KEYWORD,
                default=default_context[name]
            ) for name in list(default_context.keys())
        ]
        signature = Signature(params)
        bound_args = signature.bind(*args, **kwargs).arguments

        # Update the default_context with the bound arguments
        default_context.update(bound_args)

        # Create the new instance and set its default_context
        instance = super().__call__()
        instance.default_context = default_context
        return instance


class ProcessorCollectionMeta(type):

    def __new__(mcs, name, bases, attrs):
        attrs["default_context"] = {
            key: value
            for key, value in attrs.items()
            if not key.startswith("__") and not callable(value)
        }
        return super().__new__(mcs, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        for attr_name, attr_value in attrs.items():
            if attr_name == "__call__":
                # If the __call__ method is defined, make sure has loader_context
                # rather than context as a parameter
                parameters = get_func_args(attr_value)
                if "context" in parameters and "loader_context" not in parameters:
                    raise TypeError(
                        f"{cls.__name__}.__call__() should have `loader_context` rather than `context` as a parameter. "
                        "The itemloaders package looks specifically for `loader_context`, for a number of internal processes. "
                    )
            elif attr_name == "__init__":
                raise TypeError(
                    f"{cls.__name__} class should not define __init__(). "
                    "It overrides the MetaClass's functionality, which is used to "
                    "set the instance's default_context attr from class attrs. "
                    "& set the instance's processors attr."
                )
        super().__init__(name, bases, attrs)

    def __call__(cls, *processors, **instance_default_context):
        
        # Make sure at least one processor is passed
        if not processors:
            raise TypeError(
                f"{cls.__name__}() must be called with at least one processor."
            )

        default_context = deepcopy(cls.default_context)
        default_context.update(instance_default_context)
        processors: Tuple[ProcessorType, ...] = tuple(
            get_processor(processor) for processor in processors
        )

        instance = super().__call__()
        instance.processors = processors
        instance.default_context = default_context

        return instance


class ContextMixin:

    @property
    def cls_name(self):
        """
        The name of the processor collection.

        :return: The name of the processor collection.
        """
        return self.__class__.__name__

    @chainmap_context_decorator
    def unpack_context(
        self,
        context: Optional[Mapping[str, Any]] = None,
        additional_keys: Optional[Iterable[str]] = tuple(),
    ) -> Union[Any, Tuple[Any, ...]]:
        """
        Unpack the context into a dictionary with optional additional keys.

        :param context: The context to unpack.
        :param additional_keys: Additional keys to include in the unpacked context.
        :return: The unpacked context.
        """
        relevent_keys = tuple(self.default_context.keys()) + additional_keys
        relevent_values = tuple(context[key] for key in relevent_keys)

        # If there is only one value, return it without the tuple
        if len(relevent_values) == 1:
            return relevent_values[0]
        return relevent_values

    @chainmap_context_decorator
    def context_to_kwargs(
        self,
        context: Mapping[str, Any],
        function: Callable
    ) -> Dict[str, Any]:
        """
        Extracts the values from a context dictionary that match the arguments of a callable.
        Only the arguments that are present in the context dictionary are included in the result.

        Typically used inside _process_value to extract the relevant arguments for a callable.

        Args:
            context: Context dictionary with potential arguments for the callable.
            callable: Callable function for which to extract relevant arguments.

        Returns:
            A dictionary with keys and values that match the arguments of the callable.

        Example:
            >>> context_to_kwargs({'x': 1, 'y': 2, 'z': 3}, lambda x, z: x + z)
            {'x': 1, 'z': 3}
        """
        keys = get_func_args(function)
        return {key: context[key] for key in keys if key in context}


class Processor(ContextMixin, metaclass=ProcessorMeta):
    """
    A Processor class that uses an optional context to process values.

    The Processor class is an abstract class that provides a structure for creating data 
    cleaning or transformation functionalities. Each Processor subclass should define 
    a specific data processing method in its `_process_value` function, which might
    optionally use a context.

    The `_process_value` method MUST be overridden in subclasses.

    When an instance of a `Processor` subclass is invoked (called as a function) with 
    an iterable of values and an optional context, it processes each value using the 
    `_process_value` method and returns a list of results. Single values are also accepted 
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

    # The metaclass decoractes this method with chainmap_context_decorator
    def process_value(
        self,
        value: V,
        context: Optional[Mapping[str, Any]] = None
    ) -> Any:
        """
        Process a single value using an optional context.

        This method is central to the functionality of the Processor class and should define 
        the specific data cleaning or transformation functionality in each subclass.

        Note:
        When calling this method directly, the `default_context` is not applied.

        :param value: The value to process.
        :param context: An optional context to use when processing the value. It can be a dictionary or a ChainMap.
        :return: The processed value.

        :raises NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `process_value` method. "
            "This method should be overridden in all subclasses to provide the processing logic."
        )

    # The metaclass decoractes this method with iter_values_chainmap_context_decorator
    # It also insure that the `loader_context` is passed as the second argument
    # rather than `context` so that the itemloaders package can use it.
    def __call__(
        self,
        values: Iterable[V],
        loader_context: Optional[Mapping[str, Any]] = None
    ) -> List[Any]:
        """
        Process a collection of values using an optional context.

        This method uses the `_process_value` method to process each value and returns a list of results.
        It's responsible for passing the context to the `_process_value` method.

        :param values: An iterable of values to process. If a single value is 
                       provided, it is converted into an iterable.
        :param loader_context: An optional context to use when processing the 
                               values. It can be either a dictionary or a 
                               ChainMap. If provided, it is merged with the 
                               default context where loader_context has 
                               priority.
        :return: A list of processed values.
        """
        processor = wrap_context(self.process_value, loader_context)
        return [processor(value) for value in values]

    def __str__(self):
        default_context_str = ", ".join([
            f"{k}={v}" for k, v in self.default_context.items()
        ])
        return f"{self.cls_name}({default_context_str})"

    # When in a processor collection class, helps with get, set, del methods
    def __eq__(self, other):
        if (
            type(self) is type(other)
            and self.default_context == other.default_context
        ):
            return True
        return False


class ProcessorCollection(ContextMixin, metaclass=ProcessorCollectionMeta):

    def __call__(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `__call__` method. "
            "This method should be overridden in all subclasses to provide the processing logic."
        )

    def __add__(self, other: Union[Callable, Iterable[Callable]]) -> ProcessorCollectionType:
        """
        Adds another Compose object, a callable, or a collection of processors 
        to the current Compose instance, and returns a new Compose instance.

        If `other` is not a Compose instance, it attempts to convert it into a 
        Compose instance before addition. If this conversion is not possible, 
        a TypeError is raised.

        During the addition, if the `default_loader_contexts` of the two Compose 
        objects have different values for shared keys a ValueError is raised.

        Args:
            other: Another Compose instance, a callable, or a collection of processors.

        Returns:
            Compose: A new Compose instance resulting from the addition.

        Raises:
            TypeError: If `other` cannot be converted to a Compose instance.
            ValueError: If the `default_loader_contexts` of the two Compose objects do not match.

        Example:
            To demonstrate addition of Compose objects:

            >>> compose_1 = Compose(sum)
            >>> compose_2 = Compose(lambda x: [x * 2])
            >>> compose_3 = compose_1 + compose_2
            >>> compose_3([1, 2, 3, 4, 5])
            [30]

            To add a single callable function to a Compose instance:

            >>> compose_1 = Compose(sum)
            >>> compose_2 = compose_1 + (lambda x: [x * 2])
            >>> compose_2([1, 2, 3, 4, 5])
            [30]

            To add a collection of processors to a Compose instance:

            >>> processors = [sum, lambda x: [x * 2]]
            >>> compose_1 = Compose(min, lambda x: [x])
            >>> compose_2 = compose_1 + processors
            >>> compose_2([1, 2, 3, 4, 5])
            [2]
        """

        if (
            isinstance(other, ProcessorCollection)
            and type(self) != type(other)
        ):
            raise TypeError(
                f"Cannot add {type(self).__name__} and {type(other).__name__} ProcessorCollection instances."
            )

        if not isinstance(other, type(self)):
            # single callable, or collection of callables
            potential_processors = arg_to_iter(other)

            processors, not_processors = [], []

            for potential_processor in potential_processors:
                try:
                    processors.append(get_processor(potential_processor))
                except TypeError:
                    not_processors.append(potential_processor)

            if not_processors:
                names = ', '.join(
                    [f"'{type(not_a_processor).__name__}'" for not_a_processor in not_processors]
                )
                raise TypeError(
                    f"Unsupported operand type(s) for +: '{type(self).__name__}' and {names}"
                )

            processors = self.processors + tuple(processors)
            return type(self)(*processors)
        else:
            return type(self)(*self.processors + other.processors)

    def append(self, processor) -> ProcessorCollectionType:
        """
        Similar to __add__ but returns a new instance instead of mutating.
        """
        return self + processor

    def extend(self, processors) -> ProcessorCollectionType:
        """
        Similar to __add__ but returns a new instance instead of mutating.
        """
        return self + processors

    def insert(self, index, processor) -> ProcessorCollectionType:
        """
        similar to __setitem__ but returns a new instance instead of mutating
        """
        processors = list(self.processors)
        processors.insert(index, get_processor(processor))
        return type(self)(*processors)

    def __getitem__(self, index) -> Union[ProcessorType, Iterable[ProcessorType]]:
        return self.processors[index]

    def replace_processor(self, index, processor) -> ProcessorCollectionType:
        """
        similar to __setitem__ but returns a new instance instead of mutating
        """
        processors = list(self.processors)
        processors[index] = get_processor(processor)
        return type(self)(*processors)

    def delete_processor(self, index) -> ProcessorCollectionType:
        """
        Similar to __delitem__ but returns a new instance instead of mutating.
        """
        processors = list(self.processors)
        del processors[index]
        
        if not processors:
            raise IndexError(
                f"{self.cls_name}() must keep at least one processor."
            )
        
        return type(self)(*processors)

    def __contains__(self, processor) -> bool:
        return processor in self.processors

    def __len__(self) -> int:
        return len(self.processors)

    def __str__(self) -> str:
        
        def processor_to_str(processor):
            if isinstance(processor, (Processor, ProcessorCollection)):
                return str(processor)
            else:
                # str.upper, etc
                name = processor.__qualname__
                if '<lambda>' in name:
                    return name.split('.')[0]
                return name
        
        processor_str = ', '.join([
            processor_to_str(processor) for processor in self.processors
        ])
        
        return f"{self.cls_name}({processor_str})"

    def __eq__(self, other) -> bool:
        if (
            type(self) is type(other)
            and self.default_context == other.default_context
            and self.processors == other.processors
        ):
            return True
        return False
