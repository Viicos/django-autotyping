# django-autotyping

Automatically add type hints for Django powered applications.

[![Python versions](https://img.shields.io/pypi/pyversions/django-autotyping.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/django-autotyping.svg)](https://pypi.org/project/django-autotyping/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> [!WARNING]\
> Still WIP

# Installation

Through `pip`:

```sh
pip install django-autotyping
```

# Usage

`django-autotyping` is usable in two ways:
- As a Django development application.
- As a linter that will automatically apply changes to your code.

# Django application - dynamic stub files

# Linter - automatic codemods

`django-autotyping` can be used as a CLI program:

```sh
usage: Add type hints to your models for better auto-completion.

positional arguments:
  path                  Path to the directory containing the Django application. This directory should contain your `manage.py` file.

options:
  -h, --help            show this help message and exit
  --settings-module SETTINGS_MODULE
                        Value of the `DJANGO_SETTINGS_MODULE` environment variable (a dotted Python path).
  --diff                Show diff instead of applying changes to existing files.
  --disable [{DJA001} ...]
                        Rules to be disabled.
  --type-checking-block
                        Whether newly added imports should be in an `if TYPE_CHECKING` block (avoids circular imports).
  --assume-class-getitem
                        Whether generic classes in stubs files but not at runtime should be assumed to have a `__class_getitem__` method. This can be
                        achieved by using `django-stubs-ext` or manually.
```

# Rules

## Add type hints to forward relations (`DJA001`)

All subclasses of [`RelatedField`](https://github.com/django/django/blob/0ee2b8c326d47387bacb713a3ab369fa9a7a22ee/django/db/models/fields/related.py#L91) will be taken into account.

```python
from typing import TYPE_CHECKING

from django.db import models

# Model is imported in an `if TYPE_CHECKING` block if `--type-checking-block` is used.
if TYPE_CHECKING:
    # Related model is imported from the corresponding apps models module:
    from myproject.reporters.models import Reporter


class Article(models.Model):
    # If the field supports `__class_getitem__` at runtime, it is parametrized directly:
    reporter = models.ForeignKey["Reporter"](
        "reporters.Reporter",
        on_delete=models.CASCADE,
    )

    # Otherwise, an explicit annotation is used. No unnecessary import if model is in the same file.
    article_version: "models.OneToOneField[ArticleVersion]" = models.OneToOneField(
        "ArticleVersion",
        on_delete=models.CASCADE,
    )
```

> [!NOTE]\
> As of today, generated type hints will only play well with [`django-types`](https://github.com/sbdchd/django-types). [`django-stubs`](https://github.com/typeddjango/django-stubs) requires a type for both the `__set__` and `__get__` types.

`django-autotyping` is built with [LibCST](https://github.com/Instagram/LibCST/).
