## Built-in processors that override the __call__ method

### [TakeAll](#takeall)
---
the `TakeAll` processor is dentical to `itemloaders.processors.Identity` Processor. The name is more intuitive when using the processor as an output processor.

```python
processor = TakeAll()
processor(['apple', 'banana', 'cherry'])
# ['apple', 'banana', 'cherry']
processor('apple')
# 'apple' # Not ['apple'], but would be if it inherited from scrapy_processors.base.Processor
```
### Note:
This processor does not inherit from `scrapy_processors.Processor`, and is the only included processor not to do so. This is because values are wrapped in a list if it's a single value. See the section on metaclasses.

### [TakeAllTruthy](#takealltruthy)
---
The `TakeAllTruthy` Processor takes an iterable and returns all truthy values. If no values are truthy, return the default
value in `default_context`.

In Python, truthy values are those which are evaluated to True in a Boolean context. All values are considered "truthy" except for the following, which are "falsy":
- None
- False
- zero of any numeric type (0, 0.0, 0j, Decimal(0), Fraction(0, 1))
- empty sequences and collections ('', (), [], {}, set(), range(0))

#### Default Context:
- **falsey_values (Tuple[Any, ...]): = (None, False, 0, 0.0, 0j, Decimal(0), Fraction(0, 1)).**

    Values to consider falsey.
- **empty_iterables_are_falsey (bool): = True**

  If empty iterables are considered falsey.
- **exclude (Optional[Iterable[Any]]): ="Don't exclude any falsey values"**

  Types to exclude from the check. (cannot have a falsey value as a default, so the string is the default.)
- **default (Any): = None**

  The default list to return when no truthy values exist.


```python
processor = TakeAllTruthy()
processor([0, False, None, [], 'Hello', 5])
# ['Hello', 5]
```
### [TakeFirst](#takefirst)
---
The `TakeFirst` processor is nearly identical to the `itemloaders.processors.TakeFirst` processor. The difference is that it's now contextually aware, and allows for a default value.

#### Default Context:
- **exclude (Tuple[Any, ...]): = (None, "")**

  Values to exclude from returning, even if first.
- **default (Any): = None**

  The default value to return if no values are found.

```python
processor = TakeFirst()
processor(['apple', 'banana', 'cherry'])
# 'apple'
```
### [TakeFirstTruthy](#takefirsttruthy)
---
A `TakeFirst` processor that returns the first truthy value.

#### Default Context:
- **falsey_values (Tuple[Any, ...]): = (None, False, 0, 0.0, 0j, Decimal(0), Fraction(0, 1)).**

    Values to consider falsey.
- **empty_iterables_are_falsey (bool): = True**

  If empty iterables are considered falsey.
- **exclude (Optional[Iterable[Any]]): ="Don't exclude any falsey values"**

  Types to exclude from the check. (cannot have a falsey value as a default, so the string is the default.)
- **default (Any): = None**

  The default list to return when no truthy values exist.

```python
processor = TakeFirstTruthy()
processor([0, False, None, [], 'Hello', 5])
# 'Hello'
```
### [Coalesce](#coalesce)
---
The `Coalesce` processor returns the first non `NoneType` value in an iterable.

#### Default Context:
- **default (Any): = None**

  The value to return if all values are `None`. Defaults to `None`.

```python
processor = Coalesce(default='No values')
processor([None, None, None, 'Hello', None])
# 'Hello'
processor([None, None, None])
# 'No values'
```
### [Join](#join)
---
The `Join` processor returns a string of the list of values joined by a separator.
Elements of the iterable must be strings or have a `__str__` method defined.

#### Default Context:
- **separator (str): = " "**

  The separator to use when joining values. Defaults to a space (" ").

```python
processor = Join(separator=', ')
processor(['apple', 'banana', 'cherry'])
# 'apple, banana, cherry'
```
### [Flatten](#flatten)
---
the `Flatten` processor is a contexless processor that flattens an iterable of iterables into a single iterable.


```python
processor = Flatten()
processor([[1, 2], [3, 4], [5, 6]])
# [1, 2, 3, 4, 5, 6]
```