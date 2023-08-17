
## Built-in ProcessorCollection Subclasses

### [Compose](#compose)
---
Applies a collection of processors to a list of values, one after the other.
If a processor returns a list, or another object the next processor is called with the returned object.

#### Default Context:
1. **stop_on_none = True**:

    If a processor returns `None`, the processing stops and the default value is returned.
2. **default = None**:

    The default value to return if the processing stops.

```python
class CubeProcessor(Processor):
        def process_value(self, value, **context):
            return value ** 3

compose = Compose(sum, CubeProcessor())
compose([1, 2, 3, 4, 5]) # 225

```

### [MapCompose](#mapcompose)
---
Applies a collection of processors to each individual element in a list, one after the other, flattening lists if necessary.
The next processor is called on each element of the possibly flattened list.


```python
class StripProcessor(Processor):
    def process_value(self, value, **context):
        return value.strip()

map_compose = MapCompose(StripProcessor(), str.upper)
map_compose([' hello', 'world ']) # ['HELLO', 'WORLD']
```

### Compose vs MapCompose
---
The important distinction between Compose & MapCompose is that Compose works on
the entire list of values, while MapCompose works on each individual element of the list.

```python
def reverse(iterable):
    return iterable[::-1]

map_compose = MapCompose(reverse)
compose = Compose(reverse)

map_compose(['hello', 'world']) # ['olleh', 'dlrow']
compose(['hello', 'world'])     # ['world', 'hello']
```

### List-Like Interface
---
The above two classes are nearly identical to their counterparts with the same
name that are included in the `itemloaders` package. The major difference
comes in their list-like interface.

This interface is useful for creating reusable processors that can be extended by other processors.
The interface is list-like because all the methods and attributes for a built-in python list are available to the ProcessorCollection subclasses, but they don't mutate the original object, instead returning a new instance
of the class.

Differences between methods of list and ProcessorCollection subclasses:
1. **`__add__`:** This method can add either a single object, or a list of objects to the collection.
2. **extend:** This method can either extend the list of processors using an iterable of processors,
or combine two ProcessorCollection processors together, provided that every shared key
in the `default_context` of the two instances shares the same value.
3. **replace:** This may not be a list method, but it uses index subscription, to
take an index and a new processor as arguments, and replace the old processor at that index
with a new one.


```python
# Compose Example
compose = Compose(sum)
compose_with_square = compose + (lambda x: x ** 2)

compose([1, 2, 3, 4, 5]) # 15
compose_with_square([1, 2, 3, 4, 5]) # 55

# MapCompose Example
map_compose = MapCompose(lambda x: x[::-1])
map_compose_two = map_compose + str.upper

map_compose(['hello', 'world'])     # ['olleh', 'dlrow']
map_compose_two(['hello', 'world']) # ['OLLEH', 'DLROW']

# Addition vs Extend
map_compose_three = map_compose_two + int + compose_with_square
# MapCompose(lambda x: x[::-1], str.upper, int, Compose(sum, lambda x: x ** 2)))

map_compose_four = (map_compose_two + int).extend(compose_with_square)
# MapCompose(lambda x: x[::-1], str.upper, int, sum, lambda x: x ** 2))

# replace
replace_compose = compose_with_square.replace(1, lambda x: x ** 3)
# Compose(sum, lambda x: x ** 3)
```

Here's how to use the list-like interface on `https://quotes.toscrape.com/`

```python
import attr
from itemloaders import ItemLoader
from scrapy_processors import (
    DateTime, MapCompose, NormalizeWhitespace, RemoveHTMLTags,
    StripQuotes, TakeAll, UnicodeEscape
)

@attr.s
class QuoteItem:
    text = attr.ib(default="")
    author = attr.ib(default="")
    tags = attr.ib(default=attr.Factory(list))

@attr.s
class AuthorItem:
    name = attr.ib(default="")
    birthday = attr.ib(default="")
    bio = attr.ib(default="")

clean_string = MapCompose(
    UnicodeEscape(),
    RemoveHTMLTags(),
    str.strip,
    StripQuotes(),
    NormalizeWhitespace(),
)

class QuoteLoader(ItemLoader):
    default_item_class = QuoteItem

    text_in   = clean_string
    author_in = clean_string + str.title
    tags_in   = clean_string + str.lower

    tags_out = TakeAll()

class AuthorLoader(ItemLoader):
    default_item_class = AuthorItem

    name_in = clean_string + str.title
    birthday_in = DateTime("%B %d, %Y")
    bio_in = clean_string
```

The fact that `clean_string` can be defined once, then used in multiple processors
without mutating the original object is a huge benefit of the list-like interface.
