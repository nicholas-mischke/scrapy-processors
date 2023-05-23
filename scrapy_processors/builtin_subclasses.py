
from typing import Callable, Dict, Tuple, Any

from itemloaders.processors import Identity
from itemloaders.processors import Compose as BuiltInCompose
from itemloaders.processors import MapCompose as BuiltInMapCompose
from itemloaders.utils import arg_to_iter

from scrapy_processors.utils import get_callable, merge_context_dicts


class MapCompose(BuiltInMapCompose):
    """
    A subclass of itemloaders.processors.MapCompose.

    This Processor is used to apply a sequence of callables to each value in a collection of values.
    This behavior distinguishes it from the Compose Processor, which applies a sequence of 
    callables to a collection as a whole.

    The constructor of this Processor accepts any callable object, or any class that becomes 
    callable once instantiated, assuming the class's constructor doesn't require arguments.

    Additionally, the __add__ method allows adding other MapCompose objects, individual 
    callables, or collections of callables to an existing MapCompose instance.
    The result is a new MapCompose instance containing the callables and 
    default_loader_contexts of both original objects.

    Args:
        callables: Any number of callable objects or classes.
        default_loader_context: A dictionary containing default context data for the loader.

    Returns:
        MapCompose: A new MapCompose object with enhanced functionality.

    Example:
        Consider you wish to remove superfluous whitespace in a string and then convert the 
        string to lowercase. This can be achieved using the NormalizeWhitespace Processor 
        from this package and Python's built-in str.lower function. They can be chained 
        together using the MapCompose Processor:

        >>> processor = MapCompose(NormalizeWhitespace, str.lower)
        >>> processor([' Hello', 'World '])
        ['hello', 'world']

        The processor also works on single values, asumming they're not iterable,
        or on strings / dictionaries, which are treated as single non iterable.
        >>> processor(' Hello') 
        ['hello']

        To demonstrate addition of MapCompose objects:

        >>> map_compose_1 = MapCompose(NormalizeWhitespace)
        >>> map_compose_2 = MapCompose(str.lower)
        >>> map_compose_3 = map_compose_1 + map_compose_2
        >>> map_compose_3([' Hello', 'World '])
        ['hello', 'world']

        To add a single callable function to a MapCompose instance:

        >>> map_compose_1 = MapCompose(NormalizeWhitespace, str.lower)
        >>> map_compose_2 = map_compose_1 + str.upper
        >>> map_compose_2([' Hello', 'World '])
        ['HELLO', 'WORLD']

        To add a collection of callables to a MapCompose instance:

        >>> callables = [str.upper, str.capitalize]
        >>> map_compose_1 = MapCompose(NormalizeWhitespace, str.lower)
        >>> map_compose_2 = map_compose_1 + callables
        >>> map_compose_2([' Hello', 'World '])
        ['Hello', 'World']
    """

    def __init__(self, *callables: Callable[..., Any], **default_loader_context: Dict[str, Any]):
        self.functions: Tuple[Callable[..., Any], ...] = tuple(
            get_callable(callable) for callable in callables
        )
        self.default_loader_context: dict = default_loader_context

    def __add__(self, other: Any) -> 'MapCompose':
        """
        Adds another MapCompose object, a callable, or a collection of callables 
        to the current MapCompose instance, and returns a new MapCompose instance.

        If `other` is not a MapCompose instance, it attempts to convert it into a 
        MapCompose instance before addition. If this conversion is not possible, 
        a TypeError is raised.

        During the addition, if the `default_loader_contexts` of the two MapCompose 
        objects have different values for shared keys a ValueError is raised.

        Args:
            other: Another MapCompose instance, a callable, or a collection of callables.

        Returns:
            MapCompose: A new MapCompose instance resulting from the addition.

        Raises:
            TypeError: If `other` cannot be converted to a MapCompose instance.
            ValueError: If the `default_loader_contexts` of the two MapCompose objects do not match.

        Example:
            To demonstrate addition of MapCompose objects:

            >>> map_compose_1 = MapCompose(NormalizeWhitespace, default_val='example')
            >>> map_compose_2 = MapCompose(str.lower, default_val='example')
            >>> map_compose_3 = map_compose_1 + map_compose_2
            >>> map_compose_3([' Hello', 'World '])
            ['hello', 'world']

            To add a single callable function to a MapCompose instance:

            >>> map_compose_1 = MapCompose(NormalizeWhitespace, str.lower)
            >>> map_compose_2 = map_compose_1 + str.upper
            >>> map_compose_2([' Hello', 'World '])
            ['HELLO', 'WORLD']

            To add a collection of callables to a MapCompose instance:

            >>> callables = [str.upper, str.capitalize]
            >>> map_compose_1 = MapCompose(NormalizeWhitespace, str.lower)
            >>> map_compose_2 = map_compose_1 + callables
            >>> map_compose_2([' Hello', 'World '])
            ['Hello', 'World']
        """

        if not isinstance(other, MapCompose):
            others = arg_to_iter(other)

            callables, uncallables = [], []

            for callable in others:
                try:
                    callables.append(get_callable(callable))
                except TypeError:
                    uncallables.append(callable)

            if uncallables:
                uncallable_names = ', '.join(
                    [f"'{type(uncallable).__name__}'" for uncallable in uncallables]
                )
                raise TypeError(
                    f"Unsupported operand type(s) for +: 'MapCompose' and {uncallable_names}"
                )

            other = MapCompose(*callables)

        try:
            merged_contexts = merge_context_dicts(
                self.default_loader_context,
                other.default_loader_context
            )
        except ValueError as e:
            raise ValueError(
                "Cannot add MapCompose objects when the shared keys in their "
                "default_loader_contexts have different values.\n"
                f"{str(e)}"
            ) from e

        return MapCompose(
            *self.functions + other.functions,
            **merged_contexts
        )


class Compose(BuiltInCompose):
    """
    A subclass of itemloaders.processors.Compose.

    This Processor is used to apply a sequence of callables to a 
    single value of a collection of values.
    This behavior distinguishes it from the MapCompose Processor, which 
    applies a sequence of callables to each value in a collection.
    
    Args:
        callables: Callable objects to be applied to the input.
        default_loader_context: Optional dictionary with default values for the loader context.

    Examples:
        To demonstrate the addition of Compose objects:

        >>> compose_1 = Compose(sum)
        >>> compose_2 = Compose(lambda x: x * 2)
        >>> compose_3 = compose_1 + compose_2
        >>> compose_3([1, 2, 3, 4, 5])
        30

        To add a single callable function to a Compose instance:

        >>> compose_1 = Compose(sum)
        >>> compose_2 = compose_1 + (lambda x: x * 2)
        >>> compose_2([1, 2, 3, 4, 5])
        30

        To add a collection of callables to a Compose instance:

        >>> callables = [sum, lambda x: x * 2]
        >>> compose_1 = Compose(min, lambda x: [x])
        >>> compose_2 = compose_1 + callables
        >>> compose_2([1, 2, 3, 4, 5])
        2
        
        Note that above if lambda x: x * 2 is replaced with
        lambda x: [x * 2] a list will be returned instead of an int.
        This may or may not be desirable depending on the use case. 
    """

    def __init__(self, *callables: Callable[..., Any], **default_loader_context: Dict[str, Any]):
        self.functions: Tuple[Callable[..., Any], ...] = tuple(
            get_callable(callable) for callable in callables
        )
        self.stop_on_none = default_loader_context.get("stop_on_none", True)
        self.default_loader_context: dict = default_loader_context

    def __add__(self, other: Any) -> 'Compose':
        """
        Adds another Compose object, a callable, or a collection of callables 
        to the current Compose instance, and returns a new Compose instance.

        If `other` is not a Compose instance, it attempts to convert it into a 
        Compose instance before addition. If this conversion is not possible, 
        a TypeError is raised.
        
        During the addition, if the `default_loader_contexts` of the two Compose 
        objects have different values for shared keys a ValueError is raised.

        Args:
            other: Another Compose instance, a callable, or a collection of callables.

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

            To add a collection of callables to a Compose instance:

            >>> callables = [sum, lambda x: [x * 2]]
            >>> compose_1 = Compose(min, lambda x: [x])
            >>> compose_2 = compose_1 + callables
            >>> compose_2([1, 2, 3, 4, 5])
            [2]
        """
        
        if not isinstance(other, Compose):
            others = arg_to_iter(other)

            callables, uncallables = [], []

            for callable in others:
                try:
                    callables.append(get_callable(callable))
                except TypeError:
                    uncallables.append(callable)

            if uncallables:
                uncallable_names = ', '.join(
                    [f"'{type(uncallable).__name__}'" for uncallable in uncallables]
                )
                raise TypeError(
                    f"Unsupported operand type(s) for +: 'Compose' and {uncallable_names}"
                )

            other = Compose(*callables)
        
        try:
            merged_contexts = merge_context_dicts(
                self.default_loader_context,
                other.default_loader_context
            )
        except ValueError as e:
            raise ValueError((
                "Cannot add Compose objects when the shared keys in their "
                "default_loader_contexts have different values.\n"
                f"{str(e)}"
            )) from e

        return Compose(
            *self.functions + other.functions,
            **merged_contexts
        )


class TakeAll(Identity):
    """
    Renaming of itemloaders.processors.Identity Processor.
    The name is more intutive when using the processor as a output processor.
    """
    pass
