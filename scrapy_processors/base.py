# Standard library imports
from collections import ChainMap
from copy import deepcopy
from functools import wraps
from inspect import _empty as EMPTY
from inspect import isclass, signature
from inspect import Parameter, Signature
# fmt: off
from typing import Any, Callable, Dict, Iterable, List, Mapping, Tuple, Type, TypeVar, Union
# fmt: on

# 3rd 🎉 imports
from itemloaders.utils import arg_to_iter
from itemloaders.common import wrap_loader_context

# Typing variables
ValueType = TypeVar("ValueType")  # Single input value type
ValueOrValues = Union[
    ValueType, Iterable[ValueType]
]  # Single value or iterable of values
ContextType = Union[Mapping[str, Any], ChainMap]


class MetaMixin(type):
    RESERVED_ATTRS_MSG = "The class attribute '{}' is reserved for the ItemLoader class, please choose a different name."

    @staticmethod
    def param_is_pos(param: Parameter) -> bool:
        """Check if an argument can be passed as a positional argument to this parameter."""
        return str(param.kind).upper() not in ("KEYWORD_ONLY", "VAR_KEYWORD")

    def __new__(
        cls, name: str, bases: tuple, namespace: Dict[str, Any]
    ) -> "ProcessorMeta":
        """
        Create a new class with additional validations and attributes.

        This method gathers all class attributes that do not start with '__' and are not callable,
        and adds them to a dictionary named 'default_context' in the namespace.

        Parameters:
        ----------
        name : str
            The name of the class to be created.
        bases : tuple
            A tuple containing the base classes for the new class.
        namespace : Dict[str, Any]
            The namespace containing the class's attributes.

        Returns:
        -------
        ProcessorMeta
            The newly created class.

        Raises:
        ------
        - Raises ValueError if the class attributes include reserved names such as 'item' or 'selector'.
        """
        cls_attrs = {
            k: v
            for k, v in namespace.items()
            if not k.startswith("__") and not callable(v)
        }

        if "item" in cls_attrs:
            raise ValueError(MetaMixin.RESERVED_ATTRS_MSG.format("item"))
        if "selector" in cls_attrs:
            raise ValueError(MetaMixin.RESERVED_ATTRS_MSG.format("selector"))

        namespace["default_context"] = cls_attrs
        return super().__new__(cls, name, bases, namespace)


class ProcessorMeta(MetaMixin):
    """
    The ProcessorMeta metaclass transforms a class definition by gathering class attributes,
    into a dictionary named 'default_context', adding a constructor that updates the 'default_context'

    validating method signatures, and applying decorators to methods.

    From this:
    ---------
    class MyProcessor(Processor):
        arg1, arg2, arg3 = 10, 20, 30

        def process_value(self, value, **context):
            ...

        def __call__(self, values, loader_context):
            ...

    To this:
    ---------
    class MyProcessor(Processor):

        default_context = {"arg1": 10, "arg2": 20, "arg3": 30}

        def __init__(self, arg1, arg2, arg3, **kwargs):
            \"""
            This method takes *args and **kwargs.
            *args in turned into a dict with keys being the parameter names and values being the arguments.
            **kwargs is used to update the default_context.

            The functionality is a little different than what's below, but the outcome is the same.
            \"""

            self.default_context["arg1"] = arg1
            self.default_context["arg2"] = arg2
            self.default_context["arg3"] = arg3
            self.default_context.update(kwargs)

        @decorator
        def process_value(self, value, **context):
            \"""
            Signature Validation:
            --------------------
            - The first parameter after self must accept positional arguments.
                Typically this is called "value", but it can be called anything.
            - There must be a variable keyword parameter.
                Typically this is called "context", but it can be called anything.
            - Additional parameters are allowed, but they must have default values.

            Decorator Functionality:
            -----------------------
            - Chainmap(context, self.default_context) is passed to the variable keyword parameter.
            Instead of context by itself.
            \"""
            ...

        @decorator
        def __call__(self, values, loader_context=None):
            \"""
            Signature Validation:
            --------------------
            - The first parameter after self must accept positional arguments.
                Typically this is called "values", but it can be called anything.
            - The second parameter after self must be named "loader_context".
                The itemloader package will not pass loader_context to any other parameter.
            - Additional parameters are allowed, but they must have default values.

            Decorator Functionality:
            -----------------------
            - If the argument passed to values is a single value, it is wrapped in a list.
            - Chainmap(loader_context, self.default_context) is passed to loader_context.
            - loader_context is given a default value of `None`.
            \"""
            ...
    """

    @staticmethod
    def prepare_process_value(cls_name: str, func: Callable) -> Callable:
        """
        Prepare the process_value method by applying specific validations and a decorator.

        Signature Validation:
        --------------------
        process_value(self, value, **context) is the only valid signature

        Decorator Functionality:
        -----------------------
        The decorator allows you to call the method as expected

        process_value(self, value, **context), but the method will receive
        **Chainmap(context, self.default_context) instead of **context by itself.
        """

        sig = signature(func)
        params = list(sig.parameters.values())

        # Exception msg
        msg = f"Invalid signature `{cls_name}.process_value{sig}`. "

        if len(params) != 3:
            raise ValueError(
                msg
                + f"`{cls_name}.process_value(self, value, **context)` is the only valid signature."
            )

        self, value, context = params

        # Validate 'value' parameter
        if not MetaMixin.param_is_pos(value):
            raise TypeError(
                msg
                + f"The first parameter must be positional, not {str(value.kind).upper()}."
            )

        # Validate 'context' parameter
        if str(context.kind).upper() != "VAR_KEYWORD":
            raise TypeError(
                msg
                + "There must be a variable length keyword parameter. Typically named `context`, declared as **context."
            )

        def decorator(func):
            """
            A decorator to modify the behavior of the process_value method:
            passes ChainMap(context, self.default_context) to the variable keyword parameter.
            rather than context by itself.

            Parameters:
            ----------
            func : Callable
                The original function to be decorated.

            Returns:
            -------
            Callable
                The decorated function with modified behavior.
            """

            @wraps(func)
            def wrapper(self, value, **context):
                return func(self, value, **ChainMap(context, self.default_context))

            return wrapper

        return decorator(func)

    @staticmethod
    def prepare_dunder_call(cls_name: str, func: Callable) -> Callable:
        """
        Prepare the __call__ method by applying specific validations and a decorator.

        Parameters:
        ----------
        cls_name : str
            The name of the class the __call__ method belongs to.
        func : Callable
            The original __call__ method to be prepared.

        Returns:
        -------
        Callable
            A decorated version of the original __call__ method, with additional logic.

        Signature Validation:
        --------------------
        __call__(self, values, **loader_context) is the only valid signature.

        Decorator Functionality:
        -----------------------
        The decorator allows you to call the proecssor with

        >>> proc([1, 2, 3]) # No loader context
        >>> proc([1, 2, 3], {'a': 1}) # With loader context passed as a positional argument
        >>> proc([1, 2, 3], a=1) # With loader context passed as a keyword argument
        >>> proc([1, 2, 3], **{'a': 1}) # With loader context passed as a keyword argument

        All results will be the same.

        loader_context becomes ChainMap(kwargs, loader_context or {}, self.default_context)

        Raises:
        ------
        TypeError
            If the signature of the provided callable violates the rules.
        ValueError
            If there are non-optional parameters other than `values` and `loader_context`.
        """
        sig = signature(func)
        params = list(sig.parameters.values())

        msg = f"Invalid signature `{cls_name}.__call__{sig}`. "

        if len(params) != 3:
            raise ValueError(
                msg
                + f"`{cls_name}__call__(self, values, **loader_context)` is the only valid signature."
            )

        self, values, loader_context = params

        # Validate 'values' parameter
        if not MetaMixin.param_is_pos(values):
            raise TypeError(
                msg
                + f"The first parameter must be positional, not {str(values.kind).upper()}."
            )

        # Validate 'loader_context' parameter
        if str(loader_context.kind).upper() != "VAR_KEYWORD":
            raise TypeError(
                msg
                + f"The second parameter must be a variable length keyword parameter (typically named `loader_context`), not {str(loader_context.kind).upper()} with name `{loader_context.name}`."
            )

        def decorator(func: Callable) -> Callable:
            """
            A decorator to modify the behavior of the __call__ method.

            This decorator performs two main jobs:

            - If a single value is passed to the `values` parameter,
            it's placed into a list. This ensures that the subsequent code can always expect
            an iterable, even if only one value is provided.

            - Passes the `loader_context` to the method as ChainMap(loader_context, self.default_context).
            The `loader_context` takes priority over `default_context`, allowing for dynamic
            overrides of default values.

            Parameters
            ----------
            func : Callable
                The original function to be decorated.

            Returns
            -------
            Callable
                The decorated function with modified behavior.
            """

            def wrapper(self, values, loader_context=None, **kwargs):
                """
                Kwargs are a stand_in for loader_context allowing for both
                `__call__(self, values, loader_context)` and `__call__(self, values, **loader_context)`.
                """
                values = arg_to_iter(values)
                loader_context = ChainMap(
                    kwargs, loader_context or {}, self.default_context
                )

                return func(self, values, **loader_context)

            return wrapper

        return decorator(func)

    def __init__(cls, name: str, bases: tuple, namespace: dict):
        """
        Initialize a new class with additional validations and attributes.

        Parameters:
        ----------
        name : str
            The name of the class.
        bases : tuple
            A tuple containing the base classes for the class object.
        namespace : dict
            The dictionary of class attributes.

        Raises:
        ------
        TypeError
            If the class defines an `__init__` method, as it is reserved for the ProcessorMeta metaclass.

        Notes:
        -----
        This method performs the following operations:
        - Validates that the class does not define its own `__init__` method.
        - Prepares the `process_value` and `__call__` methods using the `prepare_process_value` and
        `prepare_dunder_call` static methods respectively.
        """

        # Check if the class defines an __init__ method, and raise an error if it does
        if "__init__" in namespace:
            raise TypeError(
                f"{cls.__name__} class should not define __init__. "
                "The __init__ method is reserved for the ProcessorMeta metaclass. "
                "It takes the arguments passed to the Processor subclass's constructor "
                "and uses them to update the default_context attr."
            )

        # Prepare the 'process_value' method using a static method
        if "process_value" in namespace:
            setattr(
                cls,
                "process_value",
                ProcessorMeta.prepare_process_value(
                    cls.__name__, namespace["process_value"]
                ),
            )

        # Prepare the '__call__' method using a static method
        if "__call__" in namespace:
            setattr(
                cls,
                "__call__",
                ProcessorMeta.prepare_dunder_call(cls.__name__, namespace["__call__"]),
            )

        # Call the parent class's __init__ method
        super().__init__(name, bases, namespace)

    def __call__(cls, *args, **kwargs) -> Any:
        """
        Create an instance of the Processor subclass and update the default_context.

        Parameters:
        ----------
        *args : tuple
            Positional arguments to be passed to the constructor.
        **kwargs : dict
            Keyword arguments to be passed to the constructor.

        Returns:
        -------
        Any
            An instance of the Processor subclass.

        Notes:
        -----
        This method performs the following operations:
        1. Copies the default_context attribute from the class.
        2. Dynamically creates a function signature based on the default_context, allowing for additional arguments.
        3. Binds the arguments passed to the constructor, ensuring they match the signature.
        4. Updates the default_context with the bound arguments.
        5. Creates a new instance of the Processor subclass and sets its default_context attribute.
        """

        # Create a copy of the default_context to avoid modifying the class-level attribute
        default_context = deepcopy(cls.default_context)
        params = ChainMap(kwargs, default_context)
        params = [
            Parameter(name, Parameter.POSITIONAL_OR_KEYWORD, default=value)
            for name, value in params.items()
        ]

        # Bind the arguments to the signature
        # This allows us to take *args and **kwargs and turn them into a
        # dictionary with parameter names as keys, and values as the arguments passed.
        sig = Signature(params)
        bound_args = sig.bind(*args, **kwargs).arguments

        # Update the default_context with the bound arguments
        default_context.update(bound_args)

        # Create a new instance and set its default_context attribute
        instance = super().__call__()
        instance.default_context = default_context

        return instance


class ProcessorCollectionMeta(MetaMixin):
    """
    The ProcessorCollectionMeta metaclass transforms a class definition by gathering class attributes
    into a dictionary named 'default_context', adding a constructor that updates the 'default_context',
    and applying validations.

    From this:
    ---------
    class MyProcessorCollection(ProcessorCollection):
        stop_on_none = False
        default = None

        def __call__(self, values, loader_context):
            ...

    To This:
    ---------
    class MyProcessorCollection(ProcessorCollection):
        default_context = {"stop_on_none": False, "default": None}

        def __init__(self, *processors, **default_context):
            self.processors = list(processors)
            self.default_context.update(default_context)

        @decorator
        def __call__(self, values, loader_context=None):
            \"""
            Signature Validation:
            --------------------
            - The first parameter after self must accept positional arguments.
                Typically this is called "values", but it can be called anything.
            - The second parameter after self must be named "loader_context".
                The itemloader package will not pass loader_context to any other parameter.
            - Additional parameters are allowed, but they must have default values.

            Decorator Functionality:
            -----------------------
            - If the argument passed to values is a single value, it is wrapped in a list.
            - Chainmap(loader_context, self.default_context) is passed to loader_context.
            - loader_context is given a default value of `None`.
            \"""
            ...
    """

    @staticmethod
    def prepare_dunder_call(cls_name: str, func: Callable) -> Callable:
        """
        Prepare the __call__ method by applying specific validations and a decorator.

        Parameters:
        ----------
        cls_name : str
            The name of the class the __call__ method belongs to.
        func : Callable
            The original __call__ method to be prepared.

        Returns:
        -------
        Callable
            A decorated version of the original __call__ method, with additional logic.

        Signature Validation:
        --------------------
        def __call__(self, values, *wrapped_processors, **loader_context): ... is the only valid signature.

        Decorator Functionality:
        -----------------------
        The decorator allows you to call the proecssor with

        >>> proc([1, 2, 3]) # No loader context
        >>> proc([1, 2, 3], {'a': 1}) # With loader context passed as a positional argument
        >>> proc([1, 2, 3], a=1) # With loader context passed as a keyword argument
        >>> proc([1, 2, 3], **{'a': 1}) # With loader context passed as a keyword argument

        All results will be the same.

        loader_context becomes ChainMap(kwargs, loader_context or {}, self.default_context)
        wrapped_processors are the instanes processors with the loader_context applied.

        Raises:
        ------
        TypeError
            If the signature of the provided callable violates the rules.
        ValueError
            If there are non-optional parameters other than `values`, `wrapped_proccessors` or `loader_context`.
        """
        sig = signature(func)
        params = list(sig.parameters.values())

        msg = f"Invalid signature `{cls_name}.__call__{sig}`. "

        if len(params) != 4:
            raise ValueError(
                msg
                + f"`{cls_name}.__call__(self, values, *wrapped_processors, **loader_context)` is the only valid signature."
            )

        self, values, wrapped_processors, loader_context = params

        # Validate `values`` parameter
        if not MetaMixin.param_is_pos(values):
            raise TypeError(
                msg
                + f"The first parameter must be positional, not {str(values.kind).upper()}."
            )

        # Validate `wrapped_processors` parameter
        if str(wrapped_processors.kind).upper() != "VAR_POSITIONAL":
            raise TypeError(
                msg
                + f"The second parameter must be a variable length positional parameter (typically named `wrapped_processors`), not {str(wrapped_processors.kind).upper()}."
            )

        # Validate `loader_context` parameter
        if str(loader_context.kind).upper() != "VAR_KEYWORD":
            raise TypeError(
                msg
                + f"The third parameter must be a variable length keyword parameter (typically named `loader_context`), not {str(wrapped_processors.kind).upper()}."
            )

        def decorator(func: Callable) -> Callable:
            """
            A decorator to modify the behavior of the __call__ method.

            This decorator performs two main jobs:

            - If a single value is passed to the `values` parameter,
            it's placed into a list. This ensures that the subsequent code can always expect
            an iterable, even if only one value is provided.

            - Passes the `loader_context` to the method as ChainMap(loader_context, self.default_context).
            The `loader_context` takes priority over `default_context`, allowing for dynamic
            overrides of default values.

            Parameters
            ----------
            func : Callable
                The original function to be decorated.

            Returns
            -------
            Callable
                The decorated function with modified behavior.
            """

            def wrapper(self, values, *, loader_context=None, **kwargs):
                """
                Kwargs are a stand_in for loader_context allowing for both
                `__call__(self, values, loader_context)` and `__call__(self, values, **loader_context)`.
                """

                values = arg_to_iter(values)
                loader_context = ChainMap(
                    kwargs, loader_context or {}, self.default_context
                )
                wrapped_processors = [
                    wrap_loader_context(p, loader_context) for p in self.processors
                ]

                return func(
                    self,
                    values,
                    *wrapped_processors,
                    **loader_context,
                )

            return wrapper

        return decorator(func)

    def __init__(cls, name: str, bases: tuple, namespace: dict):
        """
        Initialize a new class with additional validations and attributes for ProcessorCollectionMeta.

        Parameters:
        ----------
        name : str
            The name of the class.
        bases : tuple
            A tuple containing the base classes for the class object.
        namespace : dict
            The dictionary of class attributes.

        Raises:
        ------
        TypeError
            If the class defines an `__init__` method, as it is reserved for the ProcessorCollectionMeta metaclass.

        Notes:
        -----
        This method performs the following operations:
        - Validates that the class does not define its own `__init__` method.
        - Prepares the `__call__` method using the `prepare_dunder_call` static method from ProcessorMeta.
        - The variable length positional arguments passed to the constructor become the instance's processors.
        - The variable length keyword arguments are used to update the instance's default_context attribute.
        """

        if "__init__" in namespace:
            raise TypeError(
                f"{cls.__name__} class should not define __init__. "
                "The __init__ method is reserved for the ProcessorCollectionMeta metaclass. "
                "The variable length positional arguments passed to the constructor "
                "become the instance's processors. The variable length keyword arguments "
                "are used to update the instance's default_context attr."
            )

        if "__call__" in namespace:
            setattr(
                cls,
                "__call__",
                ProcessorCollectionMeta.prepare_dunder_call(
                    cls.__name__, namespace["__call__"]
                ),
            )

        super().__init__(name, bases, namespace)

    def __call__(cls, *args, **kwargs) -> Any:
        """
        Create an instance of the ProcessorCollection subclass and update the default_context.

        Parameters:
        ----------
        *args : tuple
            Variable length positional arguments passed to the constructor, representing the processors.
        **kwargs : dict
            Variable length keyword arguments passed to the constructor, used to update the instance's default_context attribute.

        Returns:
        -------
        Any
            An instance of the ProcessorCollection subclass.

        Notes:
        -----
        This method performs the following operations:
        1. Converts the variable length positional arguments into a list of processors.
        2. Copies the default_context attribute from the class.
        3. Updates the default_context with the keyword arguments.
        4. Creates a new instance of the ProcessorCollection subclass, sets its processors and default_context attributes.
        """
        processors = list(args)

        # Create a copy of the default_context to avoid modifying the class-level attribute
        default_context = deepcopy(cls.default_context)
        default_context.update(kwargs)

        # Create a new instance and set its processors and default_context attributes
        instance = super().__call__()
        instance.processors = processors
        instance.default_context = default_context

        return instance


class ContextMixin:
    default_context: ContextType

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
        **context,
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

    # Moved from now deleted utils.py. May or may not need it later.
    # def to_sets(*args: Any) -> Tuple[Set[Any], ...]:
    #     """
    #     Convert iterables to sets, place non-iterables into a set.
    #     Returns a tuple of sets
    #     """
    #     sets = []
    #     for arg in args:
    #         if arg is None:
    #             sets.append(set())
    #         elif isinstance(arg, (list, tuple, set)):
    #             sets.append(set(arg))
    #         else:
    #             sets.append({arg})

    #     if len(sets) == 1:
    #         return sets[0]
    #     return tuple(sets)

    def call_with_context(self, func: Union[Type, Callable], **context):
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
    A Processor class that uses an optional loader_context to process scraped values.

    The Processor class is an abstract class that provides a structure for creating data
    cleaning or transformation functionalities.

    The __call__ method can be overriden to process an iterable of values
    using an optional loader_context.

    Typically the abstract `process_value` method is overridden in subclasses to provide
    the specific data cleaning or transformation functionality.

    Example
    -------
    >>> from datetime import datetime
    >>> class DateProcessor(Processor):
    ...     format = "%Y-%m-%d"
    ...
    ...     def process_value(self, value, **context):
    ...         format = self.unpack_context(**context)
    ...         return datetime.strptime(value, format).date()

    >>> processor = DateProcessor() # default_context: {'format': '%Y-%m-%d'}
    >>> print(processor("2022-01-01")) # Output: datetime.date(2022, 1, 1)
    >>> print(processor("2022/01/01", loader_context={'format': "%Y/%m/%d"})) # Output: datetime.date(2022, 1, 1)

    >>> class JoinProcessor(Processor):
    ...     separator = ", "
    ...
    ...     def __call__(self, values, loader_context=None):
    ...         separator = self.unpack_context(loader_context)
    ...         return separator.join([str(value) for value in values])

    >>> join_processor = JoinProcessor(separator=',') # default_context: {'separator': ','}
    >>> print(join_processor(["apple", "banana", "cherry"])) # Output: "apple,banana,cherry"
    """

    def process_value(self, value, **context) -> Any:
        """
        Process a single value using context.

        This method is central to the functionality of the Processor class and should define
        the specific data cleaning or transformation functionality in each subclass.

        Signature Validation (Done by the metaclass):
        --------------------
        - The first parameter after self must accept positional arguments.
            Typically this is called "value", but it can be called anything.
        - There must be a variable keyword parameter.
            Typically this is called "context", but it can be called anything.
        - Additional parameters are allowed, but they must have default values.

        Decorator Functionality (Added by the metaclass):
        -----------------------
        - Chainmap(context, self.default_context) is passed to the variable keyword parameter.
        Instead of context by itself.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `process_value` method. "
            "This method should be overridden in all subclasses to provide the processing logic."
        )

    def __call__(self, values, **loader_context) -> List[Any]:
        """
        Process a collection of values using an optional loader_context.

        This method uses the `process_value` method to process each value and returns a list of results.
        It's responsible for passing the context to the `process_value` method.

        Signature Validation (Done by the metaclass)):
        --------------------
        - The first parameter after self must accept positional arguments.
            Typically this is called "values", but it can be called anything.
        - The second parameter after self must be named "loader_context".
            The itemloader package will not pass loader_context to any other parameter.
        - Additional parameters are allowed, but they must have default values.

        Decorator Functionality (Added by the metaclass):
        -----------------------
        - If the argument passed to values is a single value, it is wrapped in a list.
        - Chainmap(loader_context, self.default_context) is passed to loader_context.
        - loader_context is given a default value of `None`.
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
    An abstract class that provides a structure for creating a collection of processors.

    Subclasses can determine how the processors are called, in what order, or under what conditions.
    The `__call__` method is overridden in a subclass to define how the collection processes values.

    Provides a list-like interface, except that mutating methods return
    a new instance of the ProcessorCollection subclass without mutating
    the original instance.

    Example:
    -------
    >>> class MultiplyProcessor(Processor):
    ...     def process_value(self, value, **context):
    ...         return value * 2

    >>> class AddProcessor(Processor):
    ...     def process_value(self, value, **context):
    ...         return value + 3

    >>> class SubtractProcessor(Processor):
    ...     def process_value(self, value, **context):
    ...         return value - 1

    >>> class SimpleProcessorCollection(ProcessorCollection):
    ...     def __call__(self, values, loader_context=None):
    ...         for processor in self.processors:
    ...             values = [processor(value) for value in values]
    ...         return values

    >>> collection = SimpleProcessorCollection(MultiplyProcessor(), AddProcessor())
    >>> new_collection = collection + SubtractProcessor()

    >>> print(collection.processors) # Output: [MultiplyProcessor(), AddProcessor()]
    >>> print(new_collection.processors) # Output: [MultiplyProcessor(), AddProcessor(), SubtractProcessor()]

    >>> print(collection([1, 2, 3])) # Output: [5, 7, 9]
    >>> print(new_collection([1, 2, 3])) # Output: [4, 6, 8]
    """

    def __call__(self, values, *wrapped_processors, **loader_context) -> List[Any]:
        """
        Process a collection of values using a list of processors and an optional loader_context.

        This method is central to the functionality of the ProcessorCollection class and
        defines how the collection processes scraped values.

        Signature Validation (Done by the metaclass)):
        --------------------
        - The first parameter after self must accept positional arguments.
            Typically this is called "values", but it can be called anything.
        - The second parameter after self must be named "loader_context".
            The itemloader package will not pass loader_context to any other parameter.
        - Additional parameters are allowed, but they must have default values.

        Decorator Functionality (Added by the metaclass):
        -----------------------
        - If the argument passed to values is a single value, it is wrapped in a list.
        - Chainmap(loader_context, self.default_context) is passed to loader_context.
        - loader_context is given a default value of `None`.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `__call__` method. "
            "This method should be overridden in all subclasses of ProcessorCollection "
            "to provide the processing logic."
        )

    def _merge_default_context(self, other, method="extend"):
        """
        Merge the default_context attributes of two ProcessorCollection instances.

        This method is used to combine the default_context attributes of two instances,
        ensuring that shared keys have the same values. If shared keys have different values,
        a ValueError is raised to prevent unexpected behavior in the processors.

        Parameters:
        ----------
        other: ProcessorCollection
            Another ProcessorCollection instance with which to merge default_context.
        method: str, optional
            A string indicating the method that triggered the merge (e.g., "extend" or "__add__").
            Used in the exception message if there's a conflict. Default is "extend".

        Returns:
        -------
        dict
            A dictionary containing the merged default_context attributes.

        Raises:
        ------
        ValueError
            If the two instances have shared keys in default_context with different values,
            indicating a conflict that could lead to unexpected behavior.

        Example:
        --------
        self.default_context = {'a': 1, 'b': 2}
        other.default_context = {'b': 2, 'c': 3}
        merged = self._merge_default_context(other)  # Result: {'a': 1, 'b': 2, 'c': 3}
        """
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
        Extend the collection with new processors.

        Pass either an iterable of processors or another ProcessorCollection instance.
        Returns a new instance of the ProcessorCollection subclass with the new processors,
        without mutating the original instance.

        Parameters
        ----------
        processors: Iterable[Processor] or ProcessorCollection
            An iterable of processors or another ProcessorCollection instance to extend the current collection.

        Returns
        -------
        ProcessorCollection
            A new instance of the ProcessorCollection subclass with the extended processors.

        Example
        -------
        >>> collection = ProcessorCollection(MultiplyProcessor(), AddProcessor())
        >>> new_collection = collection.extend([SubtractProcessor()])
        >>> print(new_collection.processors) # Output: [MultiplyProcessor(), AddProcessor(), SubtractProcessor()]
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
