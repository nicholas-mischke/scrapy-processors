
import pytest
import inspect


def pytest_pycollect_makeitem(collector, name, obj):
    if inspect.isclass(obj) and name.startswith('test'):
        return pytest.Class.from_parent(collector, name=name)


@pytest.fixture
def reverse_processor():
    return lambda x: x[::-1]


@pytest.fixture
def lower_processor():
    return lambda x: x.lower()


@pytest.fixture
def upper_processor():
    return lambda x: x.upper()

@pytest.fixture
def title_processor():
    return lambda x: x.title()


@pytest.fixture
def strip_processor():
    return lambda x: x.strip()


@pytest.fixture
def get_first_processor():
    return lambda x: x[0]


@pytest.fixture
def get_length_processor():
    return lambda x: len(x)
