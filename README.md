
# Scrapy Processors

![License](https://img.shields.io/badge/license-MIT-blue.svg)
[![Python Versions](https://img.shields.io/badge/Python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue)](https://www.python.org/)
<!-- [![codecov](https://codecov.io/gh/nicholas-mischke/scrapy-processors/branch/master/graph/badge.svg)](https://codecov.io/gh/nicholas-mischke/scrapy-processors) -->

Scrapy Processors is a collection of Processor classes meant to work with
the [itemloaders](https://pypi.org/project/itemloaders/) package, commonly used with the [scrapy](https://pypi.org/project/Scrapy/) webscraping framework.

These processors are meant to extend / replace the provided processors in the [itemloaders](https://pypi.org/project/itemloaders/) package.

Additionally the provided Processor and ProcessorCollection classes can be extended to create custom processors.


## Installation

To install Scrapy Processors, simply use pip:

```bash
$ pip install scrapy-processors
```

## Built-in Processors
- [CharWhitespacePadding](README/built-in-process-value.md#charwhitespacepadding)
- [Coalesce](README/built-in-dunder-call.md#coalesce)
- [Date](README/built-in-process-value.md#date)
- [DateTime](README/built-in-process-value.md#datetime)
- [DateTimeExtrordinaire](README/built-in-process-value.md#datetimeextraordinaire)
- [Demojize](README/built-in-process-value.md#demojize)
- [Emails](README/built-in-process-value.md#emails)
- [ExtractDigits](README/built-in-process-value.md#extractdigits)
- [Flatten](README/built-in-dunder-call.md#flatten)
- [Join](README/built-in-dunder-call.md#join)
- [NormalizeNumericString](README/built-in-process-value.md#normalizenumericstring)
- [NormalizeWhitespace](README/built-in-process-value.md#normalizewhitespace)
- [PhoneNumbers](README/built-in-process-value.md#phonenumbers)
- [PriceParser](README/built-in-process-value.md#priceparser)
- [RemoveEmojis](README/built-in-process-value.md#removeemojis)
- [RemoveHTMLTags](README/built-in-process-value.md#removehtmltags)
- [SelectJmes](README/built-in-process-value.md#selectjmes)
- [Socials](README/built-in-process-value.md#socials)
- [StripQuotes](README/built-in-process-value.md#stripquotes)
- [TakeAll](README/built-in-dunder-call.md#takeall)
- [TakeAllTruthy](README/built-in-dunder-call.md#takealltruthy)
- [TakeFirst](README/built-in-dunder-call.md#takefirst)
- [TakeFirstTruthy](README/built-in-dunder-call.md#takefirsttruthy)
- [Time](README/built-in-process-value.md#time)
- [ToFloat](README/built-in-process-value.md#tofloat)
- [UnicodeEscape](README/built-in-process-value.md#unicodeescape)

## Built-in Processor Collections
- [Compose](README/built-in-collections.md#compose)
- [MapCompose](README/built-in-collections.md#mapcompose)

## Table of Contents

[What's a Processor?](README/whats-a-processor.md)

[What's Context?](README/whats-context.md)

[Subclassing Processor and ProcessorCollection](README/subclassing-processor-and-processorcollection.md)

[Built-in ProcessorCollection Subclasses](README/built-in-collections.md)

[Built-in value-by-value processors](README/built-in-process-value.md)

[Built-in iterable processors](README/built-in-dunder-call.md)

## Opening an Issue

If you encounter a problem with the project or have a feature request, you can open an issue to let us know.

To open an issue, please follow these steps:

1. Go to the [Issues](https://github.com/nicholas-mischke/scrapy-processors/issues) tab on the github repository page.
2. Click on the "New Issue" button.
3. Provide a descriptive title for the issue.
4. In the issue description, provide detailed information about the problem you are experiencing or the feature you are requesting.
5. If applicable, include steps to reproduce the problem or any relevant code examples.
6. Add appropriate labels to categorize the issue (e.g., bug, enhancement, documentation).
7. Click on the "Submit new issue" button to create the issue.

Once you have opened an issue, our team will review it and provide assistance or discuss the requested feature.

Note: Before opening a new issue, please search the existing issues to see if a similar issue has already been reported. This helps avoid duplicates and allows us to focus on resolving existing problems.

## Contributing

Thank you for considering contributing to this project! We welcome your contributions to help make this project better.

To contribute to this project, please follow these steps:

1. Fork the repository by clicking on the "Fork" button at the top of the repository page. This will create a copy of the repository in your GitHub account.
2. Clone the forked repository to your local machine using Git:

    ```
    $ git clone https://github.com/your-username/scrapy-processors.git
    ```

3. Create a new branch for your changes:

    ```
    $ git checkout -b feature
    ```

4. Make your desired changes to the codebase.
5. Commit your changes with descriptive commit messages:

    ```
    $ git commit -m "Add new feature"
    ```

6. Push your changes to your forked repository:

    ```
    $ git push origin feature
    ```

7. Open a pull request (PR) from your forked repository to the original repository's `master` branch.
8. Provide a clear and descriptive title for your PR and explain the changes you have made.
9. Wait for the project maintainers to review your PR. You may need to make additional changes based on their feedback.
10. Once your PR is approved, it will be merged into the main codebase. Congratulations on your contribution!

If you have any questions or need further assistance, feel free to open an issue or reach out to the project maintainers.

Happy contributing!

## License
This project is licensed under the MIT License. See the LICENSE file for more details.