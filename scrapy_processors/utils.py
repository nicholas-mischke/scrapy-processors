
from inspect import isclass


def get_callable(arg):
    if (
        callable(arg)
        and not isclass(arg)  # classes need to be instantiated
    ):
        return arg

    if isclass(arg):
        arg = arg()

    if hasattr(arg, '__call__'):
        return arg.__call__
    else:
        raise TypeError(
            f"Unsupported callable type: '{type(arg).__name__}'"
        )


def merge_context_dicts(dict1, dict2):
    shared_keys = set(dict1.keys()) & set(dict2.keys())

    error_msg = ''
    for key in shared_keys:
        if dict1[key] != dict2[key]:
            error_msg += f"Key: {key}, self[{key}]: {dict1[key]}, other[{key}]: {dict2[key]}\n"
    if error_msg:
        error_msg = (
            "Cannot add Compose or MapCompose objects with mismatched "
            "key, value pairs in their default_loader_context\n"
        ) + error_msg
        raise ValueError(error_msg.strip())

    # Combine default_loader_contexts
    default_loader_context = dict1.copy()
    default_loader_context.update(dict2)

    return default_loader_context
