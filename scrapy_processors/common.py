
from typing import Any, Dict, Iterable, Tuple, Union

# This should become a decorator, that allows for any processor to take
# return_attrs in it's default context

# Add a ephemeral_context attr for processors. The call should look at this, and
# if ca
def unpack_return_attrs(obj: Any, **context) -> Dict[str, Any]:
    """
    Return a tuple of attribute names to return from a loader.

    Args:
    ----
    return_attrs (Union[str, Iterable[str]]): The name(s) of the attribute(s) to return.

    Returns:
    -------
    Tuple[str, ...]: The attribute name(s) to return.

    Example:
    --------
    >>> unpack_return_attrs('name')
    ('name',)
    >>> unpack_return_attrs(['name', 'age'])
    ('name', 'age')
    """
    if isinstance(return_attrs, str):
        return_attrs = (return_attrs,)
    return return_attrs