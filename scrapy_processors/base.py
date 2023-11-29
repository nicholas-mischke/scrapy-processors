# Standard Library Imports
from collections import ChainMap
from copy import deepcopy
from functools import partial, wraps
from inspect import isclass
from inspect import Parameter, Signature
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Tuple,
    Type,
    TypeVar,
    Union,
)

# 3rd 🎉 Imports
from misc_utils import ParamProbe

# Local Imports
from itemloaders.utils import arg_to_iter


# Typing variables
ValueType = TypeVar("ValueType")  # Single input value type
ValueOrValues = Union[
    ValueType, Iterable[ValueType]
]  # Single value or iterable of values
ContextType = Union[Mapping[str, Any], ChainMap]


class InValidSignatureException(Exception):
    ...


# Notes on the wrap_context Function and MetaClass Decorator Signature Modifications:
# ----------------------------------------------------------------------------------
# The `wrap_context` function handles the `loader_context` parameter, considering two distinct scenarios:

# 1. 'loader_context' as a Regular Keyword Parameter:
# 2. 'loader_context' as a Variable-Length Keyword Parameter:

# The 'itemloaders' package uses `itemloaders.common.wrap_loader_context` throughout its codebase,
# looking specifically for a keyword parameter named 'loader_context'. Using a variable keyword
# parameter in this case can lead to unexpected and difficult-to-debug results.
# >>> __call__(self, values, loader_context=None)

# In contrast, it is more Pythonic to use a variable-length keyword parameter, especially when
# considering that 'loader_context' is an optional dictionary.
# >>> __call__(self, values, **loader_context)

# To align with this practice while maintaining compatibility, a combination of the `wrap_context`
# function and metaclass decorators is used. This approach modifies the function's signature to
# account for both cases, whether 'loader_context' is a regular keyword parameter or a variable-length
# keyword parameter.
# Below is the signature the MetaClasses adjust __call__ to:
# >>> __call__(self, values, loader_context=None, **_loader_context)

# Additionally, this design handles the situation where the 'loader_context' parameter is named 'context'
# instead, ensuring broad compatibility and adherence to Pythonic practices.


def wrap_context(func, **context):
    """
    Description:
    -----------
    Wrap a function that has a parameter named `context` or `loader_context`,
    to contain the `context` "pre-loaded", exposing an interface that can be
    called by passing a single positional argument.

    Handles the case where the parameter is a variable length keyword parameter,
    or a regular keyword parameter.

    Parameters:
    -----------
    - func (Callable): The function to wrap.
    - context (Mapping[str, Any]): The context to wrap the function with.

    Returns:
    --------
    - A partial function with the context already applied.
    """

    probe = ParamProbe(func)
    names = probe.names

    if "context" in names and "loader_context" in names:
        raise ValueError(
            "The function cannot have both a `context` and `loader_context` parameter."
        )
    elif "context" in names:
        if probe["context"].is_var_kw:
            return partial(func, **context)
        else:
            return partial(func, context=context)
    elif "loader_context" in names:
        if probe["loader_context"].is_var_kw:
            return partial(func, **context)
        else:
            return partial(func, loader_context=context)
    else:
        return func


def chainmap_context(func: Callable) -> Callable:
    """
    Decorator Functionality:
    -----------------------
    - The decorator preserves the signature of the original method.

    >>> # the argument passed to the context parameter is combined with ``default_context``
    >>> **Chainmap(context, self.default_context)
    """

    @wraps(func)
    def wrapper(self, *args, **context):
        return func(self, *args, **ChainMap(context, self.default_context))

    return wrapper


class MetaMixin(type):
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

        reserved = ("item", "selector", "parent")
        violations = tuple(k for k in reserved if k in cls_attrs)
        if violations:
            raise ValueError(
                f"The class attribute(s) {', '.join(violations)} are reserved for the ItemLoader class, please choose a different name."
            )

        namespace["default_context"] = cls_attrs

        for k in cls_attrs:
            del namespace[k]

        return super().__new__(cls, name, bases, namespace)

    @staticmethod
    def validate_method_signature(cls_name: str, method: Callable) -> None:
        """
        Description:
        -----------
        Validate the signature of the given method (`__call__` or `process_value`).

        Signature Validation:
        --------------------
        The method can have a contextual or contextless signature.

        >>> # Contextless version
        >>> def process_value(self, value): ...
        >>> def __call__(self, values): ...
        ...
        >>> # Contextual versions (either `context` or `loader_context` as variable-length keyword parameter)
        >>> def process_value(self, value, **context): ...
        >>> def __call__(self, values, **loader_context): ...

        Rules:
        - Besides `self`, the method can have at most two parameters.
        - The first parameter must accept a positional argument.
        - The second parameter must be named `context` or `loader_context`.
        - The second parameter must be a variable-length keyword parameter.

        Raises:
        ------
        - InValidSignatureException: if the signature of the method breaks any of the rules above.
        """

        method_name = method.__name__
        probe = ParamProbe(method, remove_self=True)

        if len(probe) == 0:
            raise InValidSignatureException(
                f"The signature of `{cls_name}.{method_name}` must have at least one parameter. Found {len(probe)} parameters."
            )

        if probe[0].can_pass_pos_arg is False:
            raise InValidSignatureException(
                f"The first parameter after self in the signature of `{cls_name}.{method_name}` must be able to accept a positional argument. parameter `{probe[0].name}` is not a positional parameter, it's {probe[0].kind}."
            )
        del probe[0]

        if probe.get("VAR_KEYWORD", None) is not None:
            context = probe["VAR_KEYWORD"]
            if context.name not in ("context", "loader_context"):
                raise InValidSignatureException(
                    f"The second parameter after `self` in the signature of `{cls_name}.{method_name}` must be named `context` or `loader_context`, not `{context.name}`."
                )
            del probe["VAR_KEYWORD"]

        if "context" in probe or "loader_context" in probe:
            raise InValidSignatureException(
                f"The second parameter after `self` in the signature of `{cls_name}.{method_name}` must be a variable-length keyword parameter, not `{probe[0].name}`."
            )

        if len(probe) > 0:
            raise InValidSignatureException(
                f"The `{cls_name}.{method_name}` can have at most two parameters, not {len(probe) + 1}."
            )

    @staticmethod
    def dunder_call_decorator(func: Callable) -> Callable:
        """
        Decorator Functionality:
        -----------------------
        - The decorator changes the signature of the original method to.
        >>> __call__(self, values, loader_context=None, **_loader_context): ...
        To better understand why, see the large comment block near the top of this module.
        It may seem odd that a signature is enforced to be changed without reading the the comment block.

        >>> # If a single value is passed to ``values`` it's wrapped in a list.
        >>> values = arg_to_iter(values)
        ...
        >>> # The arguments passed to the `loader_context` parameter
        >>> # and/or `**_loader_context` is combined with `default_context`
        >>> **Chainmap(_loader_context, loader_context or {}, self.default_context)

        >>> proc([1, 2, 3])             # No loader context
        >>> proc([1, 2, 3], {'a': 1})   # With loader context passed as a positional argument
        >>> proc([1, 2, 3], a=1)        # With loader context passed as a keyword argument
        >>> proc([1, 2, 3], **{'a': 1}) # With loader context passed as a variable length keyword argument

        All results will be the same.
        """

        def wrapper(self, values, loader_context=None, **_loader_context):
            """
            >>> __call__(self, values, **loader_context): ...
            """
            values = arg_to_iter(values)
            loader_context = ChainMap(
                _loader_context, loader_context or {}, self.default_context
            )

            return func(self, values, **loader_context)

        return wrapper


class ProcessorMeta(MetaMixin):
    """
    Description:
    -----------
    - Collect all non-callable, non-dunder attributes from the class definition
    and add them to a new dictionary class attribute named `default_context`.
    - Add a constructor that updates the `default_context` with the arguments passed to the constructor.
    - Prohibts `__init__` from being defined, to not conflict with the constructor.
    - Validates the signature and adds a decorator to the `process_value` and `__call__` methods.
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
    >>>    def __init__(self, arg1=10, arg2=20, arg3=30, **kwargs):
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
    >>>        - Besides `self`, the method can have at most two parameters.
    >>>        - The first parameter must accept a positional argument.
    >>>        - The second parameter must be named `context` or `loader_context`.
    >>>        - The second parameter must be a variable-length keyword parameter.
    ...
    >>>        Decorator Functionality:
    >>>        -----------------------
    >>>        - Chainmap(context, self.default_context) is passed to the context parameter.
    >>>        \"""
    >>>        ...
    ...
    >>>    @decorator
    >>>    def __call__(self, values, loader_context=None, **_loader_context):
    >>>        \"""
    >>>        Signature Validation:
    >>>        --------------------
    >>>        - Besides `self`, the method can have at most two parameters.
    >>>        - The first parameter must accept a positional argument.
    >>>        - The second parameter must be named `context` or `loader_context`.
    >>>        - The second parameter must be a variable-length keyword parameter.
    ...
    >>>        Decorator Functionality:
    >>>        -----------------------
    >>>        - If the argument passed to `values` is a single value, it is wrapped in a list.
    >>>        - Chainmap(loader_context, self.default_context) is passed to the `loader_context` parameter.
    >>>        - The signature of the method is changed to:
    >>>        - __call__(self, values, loader_context=None, **_loader_context): ...
    >>>        To better understand why, see the large comment block near the top of this module.
    >>>        It may seem odd that a signature is enforced to be changed without reading the the comment block.
    >>>        \"""
    >>>        ...
    """

    def __init__(cls, name: str, bases: tuple, namespace: dict):
        """
        Description:
        ------------
        - Prohibts ``__init__`` from being defined, to not conflict with the ``__call__`` of this metaclass.
        - Validates the signature and adds a decorator to both the ``process_value`` and ``__call__`` methods.

        Raises:
        ------
        - TypeError:
            If the class defines an `__init__` method, as it is reserved for the ProcessorMeta metaclass.
        - InvalidSignatureError:
            If the signature of the ``process_value`` or ``__call__`` methods is invalid.
        """

        # Check if the class defines an __init__ method, and raise an error if it does
        if "__init__" in namespace:
            raise TypeError(
                f"{cls.__name__} class should not define __init__. "
                "The __init__ method is reserved for the ProcessorMeta metaclass. "
                "It takes the arguments passed to the Processor subclass's constructor "
                "and uses them to update the default_context attr."
            )

        if "process_value" in namespace:
            method = namespace["process_value"]

            ProcessorMeta.validate_method_signature(cls.__name__, method)
            setattr(cls, "process_value", chainmap_context(method))

        if "__call__" in namespace:
            method = namespace["__call__"]

            MetaMixin.validate_method_signature(cls.__name__, method)
            setattr(
                cls, "__call__", MetaMixin.dunder_call_decorator(namespace["__call__"])
            )

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
    and add them to a new dictionary class attribute named `default_context`.
    - Add a constructor that turns positional arguments into a list of processors,
    and uses keyword arguments to update the instance's `default_context` attribute.
    - Prohibts `__init__` from being defined, to not conflict with the constructor.
    - Validates the signature and adds a decorator to the `__call__` method.
    - More about the decorator in the `To This:` section below.

    From this:
    ---------
    >>> class MyProcessorCollection(ProcessorCollection):
    >>>    stop_on_none = False
    >>>    default = None
    ...
    >>>    def __call__(self, values, **loader_context):
    >>>        ...

    To This:
    ---------
    >>> class MyProcessorCollection(ProcessorCollection):
    >>>    default_context = {"stop_on_none": False, "default": None}
    ...
    >>>    def __init__(self, *processors, **default_context):
    >>>       self.processors = list(processors)
    >>>       self.default_context = deepcopy(self.default_context)
    >>>       self.default_context.update(default_context)
    ...
    >>>    @decorator
    >>>    def __call__(self, values, loader_context=None, **_loader_context):
    >>>        \"""
    >>>        Signature Validation:
    >>>        --------------------
    >>>        - Besides `self`, the method can have at most two parameters.
    >>>        - The first parameter must accept a positional argument.
    >>>        - The second parameter must be named `context` or `loader_context`.
    >>>        - The second parameter must be a variable-length keyword parameter.
    ...
    >>>        Decorator Functionality:
    >>>        -----------------------
    >>>        - If the argument passed to `values` is a single value, it is wrapped in a list.
    >>>        - Chainmap(loader_context, self.default_context) is passed to the `loader_context` parameter.
    >>>        - The signature of the method is changed to:
    >>>        - __call__(self, values, loader_context=None, **_loader_context): ...
    >>>        To better understand why, see the large comment block near the top of this module.
    >>>        It may seem odd that a signature is enforced to be changed without reading the the comment block.
    >>>        - the Chainmap above is used to wrap all processors in `self.processors` with the `wrap_context`
    >>>        function. These wrapped processors are then assigned to the instance attribute `wrapped_processors`.
    >>>        \"""
    >>>        ...
    """

    def __init__(cls, name: str, bases: tuple, namespace: dict):
        """
        Description:
        ------------
        - Prohibts ``__init__`` from being defined, to not conflict with the ``__call__`` of this metaclass.
        - Validates the signature and adds a decorator to the ``__call__`` method.

        Raises:
        ------
        - TypeError:
            If the class defines an `__init__` method, as it is reserved for the ProcessorCollectionMeta metaclass.
        - InvalidSignatureError:
            If the signature of the ``__call__`` method is invalid.
        """

        if "__init__" in namespace:
            raise TypeError(
                f"{cls.__name__} class should not define `__init__`. "
                "The `__init__` method is reserved for the ProcessorCollectionMeta metaclass."
            )

        if "__call__" in namespace:
            method = namespace["__call__"]
            MetaMixin.validate_method_signature(cls.__name__, method)

            def wrap_processors(func):
                def wrapper(self, values, **loader_context):
                    setattr(
                        self,
                        "wrapped_processors",
                        tuple(
                            wrap_context(processor, **loader_context)
                            for processor in self.processors
                        ),
                    )
                    return func(self, values, **loader_context)

                return wrapper

            setattr(
                cls,
                "__call__",
                MetaMixin.dunder_call_decorator(wrap_processors(method)),
            )

        super().__init__(name, bases, namespace)

    def __call__(cls, *processors, **default_context):
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
            Default context that will be applied to the instance.
        """

        # We don't want the default_context being shared between instances
        # of the class. So we make a deepcopy of the attribute, to avoid
        # modifying the context between classes.
        default_context_copy = deepcopy(cls.default_context)
        default_context_copy.update(default_context)

        instance = super().__call__()
        instance.processors = list(processors)
        instance.default_context = default_context_copy

        return instance


class ContextMixin:
    default_context: ContextType

    @property
    def cls_name(self):
        """The name of the processor subclass."""
        return self.__class__.__name__

    @chainmap_context
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
        relevant_keys = tuple(self.default_context.keys()) + additional_keys
        relevant_values = tuple(context[key] for key in relevant_keys)

        return relevant_values

    def _extract_kwargs(self, func: Union[Type, Callable], **context) -> dict:
        """Helper for ``call_with_context`` and ``wrap_with_context``."""

        if isclass(func):
            func = func.__init__

        params = ParamProbe(func).names

        if isclass(func):
            params = params[1:]  # Remove 'self'

        return {name: context[name] for name in params if name in context}

    @chainmap_context
    def call_with_context(self, func: Union[Type, Callable], **context) -> Any:
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
        return func(**self._extract_kwargs(func, **context))

    @chainmap_context
    def wrap_with_context(self, func: Union[Type, Callable], **context) -> partial:
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
        return partial(func, **self._extract_kwargs(func, **context))


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
        >>> - Besides 'self', the method can have at most two parameters.
        >>> - The first parameter must accept a positional argument.
        >>> - The second parameter must be named 'context' or 'loader_context'.
        >>> - The second parameter must be a variable-length keyword parameter.

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

        Signature Validation (Done by the metaclass):
        --------------------------------------------
        >>> - Besides 'self', the method can have at most two parameters.
        >>> - The first parameter must accept a positional argument.
        >>> - The second parameter must be named 'context' or 'loader_context'.
        >>> - The second parameter must be a variable-length keyword parameter.

        Decorator Functionality (Added by metaclass):
        -------------------------------------------
        >>> - If the argument passed to `values` is a single value, it is wrapped in a list.
        >>> - Chainmap(loader_context, self.default_context) is passed to the `loader_context` parameter.
        >>> - The signature of the method is changed to:
        >>> - __call__(self, values, loader_context=None, **_loader_context): ...
        >>> To better understand why, see the large comment block near the top of this module.
        >>> It may seem odd that a signature is enforced to be changed without reading the the comment block.

        Returns:
        --------
        List[Any]: Processed values.
        """
        process_value = wrap_context(self.process_value, **loader_context)
        return [process_value(value) for value in values]

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
    >>>     # The metclass applies a decorator that uses the loader_context to wrap
    >>>     # The instance's processors, and assigns the result to self.wrapped_processors.
    ...     def __call__(self, values, **loader_context):
    ...         for processor in self.wrapped_processors:
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

    def __call__(self, values, **loader_context) -> Any:
        """
        Description:
        ------------
        Defines how the collection processes a collection of values using a list of processors
        and an optional `loader_context`. This method should be overridden in subclasses to provide
        specific processing logic for the collection.

        Signature Validation (Done by metaclass):
        ----------------------------------------
        >>> - Besides `self`, the method can have at most two parameters.
        >>> - The first parameter must accept a positional argument.
        >>> - The second parameter must be named `context` or `loader_context`.
        >>> - The second parameter must be a variable-length keyword parameter.

        Decorator Functionality (Added by metaclass):
        -------------------------------------------
        >>> - If the argument passed to `values` is a single value, it is wrapped in a list.
        >>> - Chainmap(loader_context, self.default_context) is passed to the `loader_context` parameter.
        >>> - The signature of the method is changed to:
        >>> - __call__(self, values, loader_context=None, **_loader_context): ...
        >>> To better understand why, see the large comment block near the top of this module.
        >>> It may seem odd that a signature is enforced to be changed without reading the the comment block.
        >>> - the Chainmap above is used to wrap all processors in `self.processors` with the `wrap_context`
        >>> function. These wrapped processors are then assigned to the instance attribute `wrapped_processors`.

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

        Description:
        ------------
        Pass either an iterable of processors or another ProcessorCollection instance.
        Returns a new instance of the ProcessorCollection subclass with the new processors,
        without mutating the original instance.

        Parameters:
        ----------
        processors: Iterable[Processor] or ProcessorCollection
            An iterable of processors or another ProcessorCollection instance to extend the current collection.

        Returns:
        -------
        ProcessorCollection
            A new instance of the ProcessorCollection subclass with the extended processors.

        Example:
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
            processors = self.processors.copy()
            processors.append(processor)
        else:
            processors = self.processors.copy()
            processors.extend(arg_to_iter(processor))
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
