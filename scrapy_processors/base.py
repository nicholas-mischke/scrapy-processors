# Standard Library Imports
from collections import ChainMap
from copy import deepcopy
from functools import partial, wraps
from inspect import isclass, signature
from inspect import Parameter, Signature
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

# Local Imports
from itemloaders.common import wrap_loader_context
from itemloaders.utils import arg_to_iter


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
        Description:
        -----------
        Collect all non-callable, non-dunder attributes from the class definition
        and add them to a new dictionary class attribute named ``default_context``.

        Example:
        --------

        >>> # From this:
        >>> class SomeClass:
        >>>    a = 1
        >>>    b = 2
        >>>    __c = 3
        >>>    def some_method(self):
        >>>        ...

        >>> # To this:
        >>> class SomeClass:
        >>>    default_context = {"a": 1, "b": 2}
        >>>    __c = 3
        >>>    def some_method(self):
        >>>        ...

        Raises:
        ------
        - Raises ValueError if the class attributes include reserved names
            such as ``item`` or ``selector``.
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

        for k in cls_attrs:
            del namespace[k]

        return super().__new__(cls, name, bases, namespace)


class ProcessorMeta(MetaMixin):
    """
    Description:
    -----------
    - Collect all non-callable, non-dunder attributes from the class definition
    and add them to a new dictionary class attribute named `default_context`.
    - Add a constructor that updates the `default_context` with the arguments passed to the constructor.
    - Prohibts `__init__` from being defined, to not conflict with the constructor.
    - Validates the signature of the `process_value` method & adds a decorator to the method.
    - Validates the signature of the `__call__` method & adds a decorator to the method.
    - More about the two decorators in the `To This:` section below.

    From This:
    ---------
    >>> class MyProcessor(Processor):
    ...    arg1, arg2, arg3 = 10, 20, 30
    ...
    ...    def process_value(self, value, **context):
    ...        ...
    ...
    ...    def __call__(self, values, **loader_context):
    ...        ...

    To This:
    ---------
    >>> class MyProcessor(Processor):
    ...
    >>>    default_context = {"arg1": 10, "arg2": 20, "arg3": 30}
    ...
    >>>    def __init__(self, arg1, arg2, arg3, **kwargs):
    >>>        \"""
    >>>        This method takes *args and **kwargs.
    >>>        args in turned into a dict with keys being the parameter names and values being the arguments.
    >>>        The arg_dict and kwargs are then used to update the default_context.
    ...
    >>>        The functionality is a little different than what's below, but the outcome is the same.
    >>>        \"""
    >>>        arg_dict = {"arg1": arg1, "arg2": arg2, "arg3": arg3}
    >>>        self.default_context.update(arg_dict)
    >>>        self.default_context.update(kwargs)
    ...
    >>>    @decorator
    >>>    def process_value(self, value, **context):
    >>>        \"""
    >>>        Signature Validation:
    >>>        --------------------
    >>>        - The signature must be exactly what is above.
    >>>        - The first parameter `value` must be positional or keyword.
    >>>        - The second parameter `context` must be a variable length keyword parameter.
    ...
    >>>        Decorator Functionality:
    >>>        -----------------------
    >>>        - Chainmap(context, self.default_context) is passed to the context parameter.
    >>>        \"""
    >>>        ...
    ...
    >>>    @decorator
    >>>    def __call__(self, values, **loader_context):
    >>>        \"""
    >>>        Signature Validation:
    >>>        --------------------
    >>>        - The signature must be exactly what is above.
    >>>        - The first parameter `values` must be positional or keyword.
    >>>        - The second parameter `loader_context` must be a variable length keyword parameter.
    ...
    >>>        Decorator Functionality:
    >>>        -----------------------
    >>>        - If the argument passed to `values` is a single value, it is wrapped in a list.
    >>>        - Chainmap(loader_context, self.default_context) is passed to the `loader_context` parameter.
    >>>        - Adjusts signature so `loader_context` is optional, and allows it to be passed as a keyword argument or as a variable length keyword argument.
    >>>             This allows this extension to more easily integrate with the itemloaders package.
    >>>        \"""
    >>>        ...
    """

    @staticmethod
    def prepare_process_value(cls_name: str, func: Callable) -> Callable:
        """
        Description:
        -----------
        Validate the signature of the ``process_value`` method and add a decorator to the method.

        Signature Validation:
        --------------------
        >>> process_value(self, value, **context): ... # only valid signature

        - The first parameter `value` must be positional or keyword.
        - The second parameter `context` must be a variable length keyword parameter.

        Decorator Functionality:
        -----------------------
        - The decorator preserves the signature of the original method.

        >>> # the argument passed to the context parameter is combined with ``default_context``
        >>> **Chainmap(context, self.default_context)

        Raises:
        ------
        TypeError:
        - If ``value`` isn't a positional or keyword parameter.
        - If ``context`` isn't a variable length keyword parameter.

        ValueError:
        - If too few or too many parameters are defined.
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
                + f"Parameter ``value`` must be positional, not {str(value.kind).upper()}."
            )

        # Validate 'context' parameter
        if str(context.kind).upper() != "VAR_KEYWORD":
            raise TypeError(
                msg
                + f"Parameter ``context`` must be a variable length keyword parameter, not {str(context.kind).upper()}."
            )

        def decorator(func):
            """
            Passes the ``context`` to the method as ``ChainMap(context, self.default_context)``.
            """

            @wraps(func)
            def wrapper(self, value, **context):
                return func(self, value, **ChainMap(context, self.default_context))

            return wrapper

        return decorator(func)

    @staticmethod
    def prepare_dunder_call(cls_name: str, func: Callable) -> Callable:
        """
        Description:
        -----------
        Validate the signature of the ``__call__`` method and add a decorator to the method.

        Signature Validation:
        --------------------
        >>> __call__(self, values, **loader_context): ... # only valid signature

        - The first parameter `values` must be positional or keyword.
        - The second parameter `loader_context` must be a variable length keyword parameter.

        Decorator Functionality:
        -----------------------
        - The decorator changes the signature of the original method to

        >>> __call__(self, values, loader_context=None, **kwargs): ...

        This is because the itemloader package expects the following signature:

        >>> __call__(self, values, loader_context=None): ...

        It uses ``functools.partial`` to pass the loader_context as a keyword argument.

        Allowing either a keyword argument or a variable length keyword argument
        allows for more intuitive calling outside the itemloaders package (testing, etc).

        >>> # If a single value is passed to ``values`` is wrapped in a list.
        >>> values = arg_to_iter(values)
        ...
        >>> # The arguments passed to the ``loader_context`` parameter and/or ``**kwargs`` is combined with ``default_context``
        >>> **Chainmap(kwargs, loader_context or {}, self.default_context)

        >>> proc([1, 2, 3]) # No loader context
        >>> proc([1, 2, 3], {'a': 1}) # With loader context passed as a positional argument
        >>> proc([1, 2, 3], a=1) # With loader context passed as a keyword argument
        >>> proc([1, 2, 3], **{'a': 1}) # With loader context passed as a variable length keyword argument

        All results will be the same.

        Raises:
        ------
        TypeError:
        - If ``values`` isn't a positional or keyword parameter.
        - If ``loader_context`` isn't a variable length keyword parameter.

        ValueError:
        - If too few or too many parameters are defined.
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
                + f"Parameter ``values`` must be positional, not {str(values.kind).upper()}."
            )

        # Validate 'loader_context' parameter
        if str(loader_context.kind).upper() != "VAR_KEYWORD":
            raise TypeError(
                msg
                + f"Parameter ``loader_context`` must be a variable length keyword parameter, not {str(loader_context.kind).upper()}."
            )

        def decorator(func: Callable) -> Callable:
            """
            Description:
            -----------
            - Modifies the signature of the original method to:

            >>> __call__(self, values, loader_context=None, **kwargs): ...

            - If the argument passed to ``values`` is a single value, it is wrapped in a list.
            - Passes the ``loader_context`` to the method as ``ChainMap(kwargs, loader_context or {} , self.default_context)``.
            """

            def wrapper(self, values, loader_context=None, **kwargs):
                """
                ``**kwargs`` is a stand_in for ``**loader_context`` allowing for both:
                >>> __call__(self, values, loader_context): ...
                >>> __call__(self, values, **loader_context): ...
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
        Description:
        ------------
        - Prohibts ``__init__`` from being defined, to not conflict with the ``__call__`` of this metaclass.
        - Validates the signature of the ``process_value`` method & adds a decorator to the method.
        - Validates the signature of the ``__call__`` method & adds a decorator to the method.

        Raises:
        ------
        TypeError
            If the class defines an `__init__` method, as it is reserved for the ProcessorMeta metaclass.
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
        Description:
        ------------
        - Creates a deepcopy of the ``default_context`` attribute from the class.
        - Dynamically creates a function signature using the ``default_context`` keys & any keyword passed to ``kwargs``.
        - Binds ``args`` and ``kwargs`` to the signature, and uses the bound_arguments dict to update ``default_context``.
        - Sets the instance's ``default_context`` attribute to the updated ``default_context``.
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
    Description:
    -----------
    - Collect all non-callable, non-dunder attributes from the class definition
    and add them to a new dictionary class attribute named ``default_context``.
    - Validates the signature of the ``__call__`` method & adds a decorator to the method.
        More about the decorator in the ``To This:`` section below.

    From this:
    ---------
    >>> class MyProcessorCollection(ProcessorCollection):
    >>>    stop_on_none = False
    >>>    default = None
    ...
    >>>    def __call__(self, values, *wrapped_processors, **loader_context):
    >>>        ...

    To This:
    ---------
    >>> class MyProcessorCollection(ProcessorCollection):
    >>>    default_context = {"stop_on_none": False, "default": None}
    ...
    >>>    @decorator
    >>>    def __call__(self, values, *wrapped_processors, **loader_context):
    >>>        \"""
    >>>        Signature Validation:
    >>>        --------------------
    >>>        - The signature must be exactly what is above.
    >>>        - The first parameter `values` must be a positional or keyword parameter.
    >>>        - The second parameter `wrapped_processors` must be a variable length positional parameter.
    >>>        - The third parameter `loader_context` must be a variable length keyword parameter.
    ...
    >>>        Decorator Functionality:
    >>>        -----------------------
    >>>        - If the argument passed to `values` is a single value, it is wrapped in a list.
    >>>        - Chainmap(loader_context, self.default_context) is passed to the `loader_context` parameter.
    >>>        - the Chainmap above is used to wrap all processors in `self.processors` and pass these
    >>>             wrapped processors to the `wrapped_processors` parameter.
    >>>        \"""
    >>>        ...
    """

    @staticmethod
    def prepare_dunder_call(cls_name: str, func: Callable) -> Callable:
        """
        Description:
        -----------
        Validate the signature of the ``__call__`` method and add a decorator to the method.

        Signature Validation:
        --------------------
        >>> def __call__(self, values, *wrapped_processors, **loader_context): # Only valid signature

        - The first parameter ``values`` must be positional or keyword.
        - The second parameter ``wrapped_processors`` must be a  variable length positional parameter.
        - The third parameter ``loader_context`` must be a variable length keyword parameter.

        Decorator Functionality:
        -----------------------
        - The decorator changes the signature of the original method to

        >>> __call__(self, values, *, loader_context=None, **kwargs): ...

        This is because the itemloader package expects the following signature:

        >>> __call__(self, values, loader_context=None): ...

        It uses ``functools.partial`` to pass the loader_context as a keyword argument.

        Allowing either a keyword argument or a variable length keyword argument
        allows for more intuitive calling outside the itemloaders package (testing, etc).

        >>> # If a single value is passed to ``values`` is wrapped in a list.
        >>> values = arg_to_iter(values)
        ...
        >>> # The arguments passed to the ``loader_context`` parameter and/or ``**kwargs`` is combined with ``default_context``
        >>> **Chainmap(kwargs, loader_context or {}, self.default_context)

        The Chaimap above is then used to wrap the processors in ``self.processors``
        and pass those to the ``*wrapped_processors`` parameter.

        >>> proc([1, 2, 3]) # No loader context
        >>> proc([1, 2, 3], {'a': 1}) # With loader context passed as a positional argument
        >>> proc([1, 2, 3], a=1) # With loader context passed as a keyword argument
        >>> proc([1, 2, 3], **{'a': 1}) # With loader context passed as a variable length keyword argument

        All results will be the same.

        Raises:
        ------
        TypeError:
        - If ``values`` isn't a positional or keyword parameter.
        - If ``wrapped_processors`` isn't a variable length positional parameter.
        - If ``loader_context`` isn't a variable length keyword parameter.

        ValueError:
        - If too few or too many parameters are defined.
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

        # Validate 'values' parameter
        if not MetaMixin.param_is_pos(values):
            raise TypeError(
                msg
                + f"Parameter ``values`` must be positional, not {str(values.kind).upper()}."
            )

        # Validate `wrapped_processors` parameter
        if str(wrapped_processors.kind).upper() != "VAR_POSITIONAL":
            raise TypeError(
                msg
                + f"Parameter ``wrapped_processors`` must be a variable length positional parameter, not {str(wrapped_processors.kind).upper()}."
            )

        # Validate 'loader_context' parameter
        if str(loader_context.kind).upper() != "VAR_KEYWORD":
            raise TypeError(
                msg
                + f"Parameter ``loader_context`` must be a variable length keyword parameter, not {str(loader_context.kind).upper()}."
            )

        def decorator(func: Callable) -> Callable:
            """
            Description:
            -----------
            - Modifies the signature of the original method to:

            >>> __call__(self, values, *, loader_context=None, **kwargs): ...

            - If the argument passed to ``values`` is a single value, it is wrapped in a list.
            - Passes the ``loader_context`` to the method as ``ChainMap(kwargs, loader_context or {} , self.default_context)``.
            - Uses the above ChainMap to wrap all processors in ``self.processors`` and pass these
                wrapped processors to the ``wrapped_processors`` parameter.
            """

            def wrapper(self, values, *, loader_context=None, **kwargs):
                """
                ``**kwargs`` is a stand_in for ``**loader_context`` allowing for both:
                >>> __call__(self, values, loader_context): ...
                >>> __call__(self, values, **loader_context): ...
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
        Validates the signature of the ``__call__`` method & adds a decorator to the method.
        """

        if "__call__" in namespace:
            setattr(
                cls,
                "__call__",
                ProcessorCollectionMeta.prepare_dunder_call(
                    cls.__name__, namespace["__call__"]
                ),
            )

        super().__init__(name, bases, namespace)


class ContextMixin:
    default_context: ContextType

    @property
    def cls_name(self):
        """The name of the processor subclass."""
        return self.__class__.__name__

    def unpack_context(
        self,
        *additional_keys: str,
        **context,
    ) -> Tuple[Any, ...]:
        """
        Unpacks the context to extract relevant keys and values.

        Description:
        ------------
        The ``context`` parameter, analogous to ``kwargs``, contains key-value pairs
        corresponding to parameter-argument pairs for callables within the ``process_value``
        or ``__call__`` methods of ``Processor`` objects.

        This creates two problems:
        - There are multiple callables within the ``process_value`` or ``__call__``
            methods. Then the  context needs to be split into multiple mappings.
            ``call_with_context`` and ``wrap_with_context`` handle this case.
        - The processor can be a part of a processor collection and ``context``
            may have irrelevant key-value pairs. This method filters out the irrelevant keys.

        This method takes the keys from ``self.default_context`` and ``additional_keys``
        and extracts their values from ``ChainMap(context, self.default_context)``.

        Parameters:
        -----------
        - additional_keys (str): Additional keys to be extracted from the context.
        - context (dict): Context containing the key-value pairs to be extracted.

        Returns:
        --------
        Tuple[Any, ...]: A tuple of values that correspond with the keys in ``self.default_context`` and ``additional_keys``.

        Raises:
        ------
        KeyError: If a key in ``additional_keys`` is not in ``context``.

        Example:
        --------
        >>> default_context = {'a': 1, 'b': 2} # Assume this is self.default_context
        >>> unpack_context(**{'a': 1, 'b': 3, 'c': 4})
        (1, 3)
        """
        context = ChainMap(context, self.default_context)

        relevant_keys = tuple(self.default_context.keys()) + additional_keys
        relevant_values = tuple(context[key] for key in relevant_keys)

        return relevant_values

    def call_with_context(self, func: Union[Type, Callable], **context):
        """
        Calls a callable or initializes a type with a context.

        Description:
        ------------
        When methods like ``process_value`` or ``__call__`` contain multiple callables,
        the context must be split. This method extracts relevant key-value pairs from
        the context and calls the given callable or initializes the given type.

        Parameters:
        -----------
        func (Union[Type, Callable]): The callable or type to be called or initialized.
        context (dict): Context containing key-value pairs.

        Returns:
        --------
        The result of calling the given callable or initializing the given type.
        """
        context = ChainMap(context, self.default_context)

        cls = None
        if isclass(func):
            cls = func
            func = cls.__init__

        parameters = list(signature(func).parameters.keys())

        if cls:
            parameters.pop(0)  # Remove self
            return cls(
                **{name: context[name] for name in parameters if name in context}
            )
        return func(**{name: context[name] for name in parameters if name in context})

    def wrap_with_context(self, func: Callable, **context) -> partial:
        """
        Wraps a callable with a context.

        Description:
        ------------
        This method returns a partial of the given callable, with the relevant
        keys in ``default_context`` and the provided ``context`` as kwargs.

        Parameters:
        -----------
        func (Callable): The callable to be wrapped.
        context (dict): Context containing key-value pairs.

        Returns:
        --------
        partial: A partial of the given callable, with context applied as kwargs.
        """
        context = ChainMap(context, self.default_context)
        parameters = list(signature(func).parameters.keys())
        return partial(
            func, **{name: context[name] for name in parameters if name in context}
        )


class Processor(ContextMixin, metaclass=ProcessorMeta):
    """
    Description:
    ------------
    This class is an abstract class that provides a structure for creating data
    cleaning or transformation functionalities on scraped values using ``context``.

    Subclasses typically override the abstract ``process_value`` method to provide
    specific data cleaning or transformation functionality.

    The `__call__` method can also be overridden to process an iterable of values
    using an optional ``loader_context``.

    Attributes:
    -----------
    default_context (dict): A dictionary containing the default values for the context.
        This attribute is constructed by the metaclass from the non-callable, non-dunder class attributes

    Example:
    -------
    >>> from datetime import datetime
    >>> class DateProcessor(Processor):
    ...     format = "%Y-%m-%d"
    ...     def process_value(self, value, **context):
    ...         return datetime.strptime(value, context['format']).date()
    ...
    >>> processor = DateProcessor()
    >>> processor.process_value("2022-01-01"))
    datetime.date(2022, 1, 1)
    >>> processor("2022/01/01", **{'format': "%Y/%m/%d"}))
    [datetime.date(2022, 1, 1)]
    ...
    >>> class JoinProcessor(Processor):
    ...     separator = ", "
    ...     def __call__(self, values, **loader_context):
    ...         return context['separator'].join([str(value) for value in values])

    >>> join_processor = JoinProcessor(separator=',') # default_context: {'separator': ','}
    >>> join_processor(["apple", "banana", "cherry"]))
    "apple,banana,cherry"
    """

    def process_value(self, value, **context) -> Any:
        """
        Process a single scraped value using ``context``.

        Description:
        ------------
        This method is central to the functionality of the Processor class and should be
        overridden in each subclass to define specific data cleaning or transformation functionality.

        Signature Validation (Done by the metaclass):
        --------------------------------------------
        >>> process_value(self, value, **context): ... # only valid signature

        - The first parameter `value` must be positional or keyword.
        - The second parameter `context` must be a variable length keyword parameter.

        Decorator Functionality (Added by the metaclass):
        -----------------------------------------------
        - The decorator preserves the signature of the original method.

        >>> # the argument passed to the context parameter is combined with ``default_context``
        >>> **Chainmap(context, self.default_context)

        Raises:
        -------
        NotImplementedError: If not implemented in a subclass.

        Note:
        -----
        If a subclass overrides ``__call__`` this method may not need to be overridden.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `process_value` method. "
            "This method should be overridden in all subclasses to provide the processing logic."
        )

    def __call__(self, values, **loader_context) -> List[Any]:
        """
        Process a collection of scraped values using an optional ``loader_context``.

        Description:
        ------------
        This method uses the `process_value` method to process each value and returns a list of results.
        It's responsible for passing the context to the `process_value` method.

        Signature Validation (Done by metaclass):
        ----------------------------------------
        >>> __call__(self, values, **loader_context): ... # only valid signature

        - The first parameter `values` must be positional or keyword.
        - The second parameter `loader_context` must be a variable length keyword parameter.

        Decorator Functionality (Added by metaclass):
        -------------------------------------------
        - The decorator changes the signature of the original method to

        >>> __call__(self, values, loader_context=None, **kwargs): ...

        This is because the itemloader package expects the following signature:

        >>> __call__(self, values, loader_context=None): ...

        It uses ``functools.partial`` to pass the loader_context as a keyword argument.

        Allowing either a keyword argument or a variable length keyword argument
        allows for more intuitive calling outside the itemloaders package (testing, etc).

        >>> # If a single value is passed to ``values`` is wrapped in a list.
        >>> values = arg_to_iter(values)
        ...
        >>> # The arguments passed to the ``loader_context`` parameter and/or ``**kwargs`` is combined with ``default_context``
        >>> **Chainmap(kwargs, loader_context or {}, self.default_context)

        >>> proc([1, 2, 3]) # No loader context
        >>> proc([1, 2, 3], {'a': 1}) # With loader context passed as a positional argument
        >>> proc([1, 2, 3], a=1) # With loader context passed as a keyword argument
        >>> proc([1, 2, 3], **{'a': 1}) # With loader context passed as a variable length keyword argument

        All results will be the same.

        Returns:
        --------
        List[Any]: Processed values.
        """
        return [self.process_value(value, **loader_context) for value in values]

    def __str__(self):
        default_context_str = ", ".join(
            [f"{k}={v}" for k, v in self.default_context.items()]
        )
        return f"{self.cls_name}({default_context_str})"

    def __eq__(self, other):
        if type(self) is type(other) and self.default_context == other.default_context:
            return True
        return False


class ProcessorCollection(ContextMixin, metaclass=ProcessorCollectionMeta):
    """
    Description:
    ------------
    This class is an abstract class that provides structure for creating a
    collection of processors.

    Subclasses can define how the processors are called, in what order, or under
    what conditions by overriding the abstract `__call__` method.

    The class provides a list-like interface, such as append, extend, etc.
    The difference is that these methods return a new instance of the class,
    rather than mutating the existing instance.

    Attributes:
    -----------
    - processors: List[Processor]
        A list of processors within the collection.
    - default_context (dict): A dictionary containing the default values for the context.
        This attribute is constructed by the metaclass from the non-callable, non-dunder class attributes

    Example:
    -------
    >>> class MultiplyProcessor(Processor):
    ...     def process_value(self, value, **context):
    ...         return value * 2
    ...
    >>> class AddProcessor(Processor):
    ...     def process_value(self, value, **context):
    ...         return value + 3
    ...
    >>> class SubtractProcessor(Processor):
    ...     def process_value(self, value, **context):
    ...         return value - 1
    ...
    >>> class SimpleProcessorCollection(ProcessorCollection):
    >>>     # Note that *wrapped_processors doesn't need to be passed by the user
    >>>     # The metclass applies a decorator that uses the loader_context to wrap
    >>>     # The instance's processors, and it passes them to this method.
    ...     def __call__(self, values, *wrapped_processors, **loader_context):
    ...         for processor in wrapped_processors:
    ...             values = [processor(value) for value in values]
    ...         return values
    ...
    >>> # Demonstrating "list-like" interface
    >>> collection = SimpleProcessorCollection(MultiplyProcessor(), AddProcessor())
    >>> new_collection = collection + SubtractProcessor()
    ...
    >>> collection.processors
    [MultiplyProcessor(), AddProcessor()]
    >>> new_collection.processors
    [MultiplyProcessor(), AddProcessor(), SubtractProcessor()]
    ...
    >>> collection([1, 2, 3])
    [5, 7, 9]
    >>> new_collection([1, 2, 3])
    [4, 6, 8]
    """

    def __init__(self, *processors, **default_context):
        """
        It's important that the processors are stored as a list, not a tuple.
        The __getattr__ method of this class uses the attributes of the list
        to provide the list-like interface, allowing for operations like adding
        and extending the processors.

        Parameters:
        -----------
        - processors: Processor, ...
            Zero or more Processor instances to be included in the collection.
        - default_context: dict, optional
            Default context that will be applied to all processors in the class.
        """
        self.processors = list(processors)

        # We don't want the default_context being shared between instances
        # of the class. So we make a deepcopy of the attribute, to avoid
        # modifying the context between classes.
        default_context_copy = deepcopy(self.__class__.default_context)
        default_context_copy.update(default_context)
        self.default_context = default_context_copy

    def __call__(self, values, *wrapped_processors, **loader_context) -> List[Any]:
        """
        Description:
        ------------
        Defines how the collection processes a collection of values using a list of processors
        and an optional loader_context. This method should be overridden in subclasses to provide
        specific processing logic for the collection.

        Signature Validation (Done by metaclass):
        ----------------------------------------
        >>> def __call__(self, values, *wrapped_processors, **loader_context): # Only valid signature

        - The first parameter ``values`` must be positional or keyword.
        - The second parameter ``wrapped_processors`` must be a  variable length positional parameter.
        - The third parameter ``loader_context`` must be a variable length keyword parameter.

        Decorator Functionality (Added by metaclass):
        -------------------------------------------
        - The decorator changes the signature of the original method to

        >>> __call__(self, values, *, loader_context=None, **kwargs): ...

        This is because the itemloader package expects the following signature:

        >>> __call__(self, values, loader_context=None): ...

        It uses ``functools.partial`` to pass the loader_context as a keyword argument.

        Allowing either a keyword argument or a variable length keyword argument
        allows for more intuitive calling outside the itemloaders package (testing, etc).

        >>> # If a single value is passed to ``values`` is wrapped in a list.
        >>> values = arg_to_iter(values)
        ...
        >>> # The arguments passed to the ``loader_context`` parameter and/or ``**kwargs`` is combined with ``default_context``
        >>> **Chainmap(kwargs, loader_context or {}, self.default_context)

        The Chaimap above is then used to wrap the processors in ``self.processors``
        and pass those to the ``*wrapped_processors`` parameter.

        >>> proc([1, 2, 3]) # No loader context
        >>> proc([1, 2, 3], {'a': 1}) # With loader context passed as a positional argument
        >>> proc([1, 2, 3], a=1) # With loader context passed as a keyword argument
        >>> proc([1, 2, 3], **{'a': 1}) # With loader context passed as a variable length keyword argument

        All results will be the same.

        Raises:
        -------
        NotImplementedError: If not implemented in a subclass.

        Returns:
        --------
        List[Any]: Processed values.

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} has not implemented the `__call__` method. "
            "This method should be overridden in all subclasses of ProcessorCollection "
            "to provide the processing logic."
        )

    def _merge_default_context(self, other, method="extend"):
        """
        Merge the ``default_context`` attributes of two ProcessorCollection instances.

        Description:
        ------------
        This method is used to combine the ``default_context`` attributes of two instances,
        ensuring that shared keys have the same values. If shared keys have different values,
        a ValueError is raised to prevent unexpected behavior in the processors.

        Parameters:
        ----------
        - other: ProcessorCollection
            Another ProcessorCollection instance with which to merge ``default_context``.
        - method: str, optional
            A string indicating the method that triggered the merge (e.g., ``extend`` or ``__add__``).
            Used in the exception message if there's a conflict. Default is ``extend``.

        Returns:
        -------
        dict
            A dictionary containing the merged default_context attributes.

        Raises:
        ------
        ValueError
            If the two instances have shared keys in ``default_context`` with different values,
            indicating a conflict that could lead to unexpected behavior.

        Example:
        --------
        >>> self.default_context = {'a': 1, 'b': 2}
        >>> other.default_context = {'b': 2, 'c': 3}
        >>> self._merge_default_context(other)
        {'a': 1, 'b': 2, 'c': 3}
        ...
        >>> other.default_context = {'a': 2}
        >>> self._merge_default_context(other)
        ValueError: Shared keys in default_context attrs have different values. Key: a, self: 1, other: 2
        """
        self_context = self.default_context
        other_context = other.default_context

        shared_keys  = tuple(set(self_context.keys()) & set(other_context.keys()))
        self_values  = tuple(self_context[key] for key in shared_keys)
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

        Description:
        ------------
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
        >>> new_collection.processors
        [MultiplyProcessor(), AddProcessor(), SubtractProcessor()]
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
                **self._merge_default_context(processor, method="__add__"),
            )

        processors = self.processors.copy() + list(arg_to_iter(processor))
        return self.__class__(*processors, **self.default_context)

    def __str__(self) -> str:
        def processor_to_str(processor):
            if isinstance(processor, (Processor, ProcessorCollection)):
                return str(processor)
            if hasattr(processor, "__qualname__"):
                # str.upper, etc
                name = processor.__qualname__
                if "<lambda>" in name:
                    return "lambda_processor"
                    # return name.split(".")[0]
                return name
            else:
                return str(processor)

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
        if not hasattr(self.processors, name):
            raise AttributeError(f"'{self}' object has no attribute '{name}'")

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

    def replace(self, index, processor):
        """
        Replace the processor at the given index with the provided processor.
        """
        processors = self.processors.copy()
        processors[index] = processor
        return self.__class__(*processors, **self.default_context)

