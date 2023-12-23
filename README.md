# django-autotyping

Automatically add type hints for Django powered applications.

`django-autotyping` generates custom [type stubs](https://typing.readthedocs.io/en/latest/source/stubs.html) based on your current Django application, enhancing your development experience
by providing auto-completions and accurate type checking.

To understand the purpose of why and how, you can refer to [this article](https://viicos.github.io/posts/an-alternative-to-the-django-mypy-plugin/).

`django-autotyping` is built with [LibCST](https://github.com/Instagram/LibCST/).

[![Python versions](https://img.shields.io/pypi/pyversions/django-autotyping.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/django-autotyping.svg)](https://pypi.org/project/django-autotyping/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> [!WARNING]\
> This project is still work in progress. It is meant to work with [`django-stubs`](https://github.com/typeddjango/django-stubs), but some improvements and changes are probably going to be
> implemented in the stub definitions, and could potentially require some changes to the generated stubs.

# Installation

Through `pip`:

```sh
pip install django-autotyping
```

# Usage

`django-autotyping` can achieve the following:
- Generate dynamic stubs depending on your application. For this use case, it is recommended
to use it as a Django development application (see [configuration](#configuration)).
- When dynamic stubs are not enough, explicit type hints can be automatically added to your source code.

# Configuration

As any Django application, you will need to add `django_autotyping` to your `INSTALLED_APPS` (preferably in your development or local settings, if you already have them separated).

The application is configurable with the `AUTOTYPING` dict:

```python
AUTOTYPING = {
    "STUBS_DIR": Path(BASE_DIR, "typings"),
}
```

The only required configuration value is `STUBS_DIR`, a path pointing to your configured local stub directory.

Once installed, the stubs will be generated after each migration (by connecting to the [`post_migrate`](https://docs.djangoproject.com/en/dev/ref/signals/#post-migrate) signal).

## `STUBS_DIR`

**Required.**

A [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) object pointing to your
configured local stubs directory, as specified by the [PEP 561](https://peps.python.org/pep-0561/#type-checker-module-resolution-order). Depending on the type checker used, configuration differs:
- [`pyright`](https://github.com/microsoft/pyright/): will look for the `typings/` directory by default (see [configuration](https://microsoft.github.io/pyright/#/configuration?id=main-configuration-options)).
- [`mypy`](https://github.com/python/mypy/): configurable via the [`mypy_path`](https://mypy.readthedocs.io/en/stable/config_file.html#confval-mypy_path) value (or use the `MYPY_PATH` environment variable).

## `DISABLED_RULES`

_Default value: empty list._

A list of rule identifiers to be disabled.

## `ALLOW_PLAIN_MODEL_REFERENCES`

_Default value: `True`._

Whether string references in the form of `{model_name}` should be generated in overloads.

If set to `True`, both `{model_name}` and `{model_name}.{app_label}` are allowed
(unless the model name has a duplicate in a different app).

_Affected rules: `DJAS001`._

## `ALLOW_NONE_SET_TYPE`

_Default value: `False`._

Whether to allow having the `__set__` type variable set to `None`.

While Django allows setting most model instance fields to any value (before saving),
it is generally a bad practice to do so. However, it might be beneficial to allow `None`
to be set temporarly.

This also works for foreign fields, where unlike standard fields, the Django descriptor used
only allows model instances and `None` to be set.

_Affected rules: `DJAS001`._

## `MODEL_FIELDS_OPTIONAL`

_Default value: `True`._

Whether all model fields should be considered optional when creating model instances.

This affects the following signatures:
- `Manager.create/acreate`
- `__init__` methods of models

A lot can happen behind the scenes when instantiating models. Even if a field doesn't have
a default value provided, the database could have triggers implemented that would provide one.
This is why, by default, this configuration attribute defaults to `True`. If set to `False`,
`django-autotyping` will try its best to determine required fields, namely by checking if:
- the field can be `null`
- the field has a default or a database default value set
- the field is a subclass of `DateField` and has `auto_now` or `auto_now_add` set to `True`.

_Affected rules: `DJAS002`._

# Available rules

## Add type hints to related fields (`DJAS001`)

A codemod that will add overloads to the `__init__` methods of related fields.

This will provide auto-completion (VSCode users, see this [issue](https://github.com/microsoft/pylance-release/issues/4428)) when using `ForeignKey`, `OneToOneField` and `ManyToManyField` with string references to a model, and accurate type checking when accessing the field attribute from a model instance.

<details>

<summary>Technical details</summary>

Stub files affected:
- `django-stubs/db/models/fields/related.pyi`

The following overloads will be created:

```python
class ForeignKey(ForeignObject[_ST, _GT]):
    # For each model, will add two overloads:
    # - 1st: `null: Literal[True]`, which will parametrize `ForeignKey` get types as `Optional`.
    # - 2nd: `null: Literal[False] = ...` (the default).
    # `to` is annotated as a `Literal`, with two values: {app_label}.{model_name} and {model_name}.
    # If two models from different apps have the same name, only the first form will be available.
    @overload
    def __init__(
        self: ForeignKey[MyModel | None, MyModel | None],
        to: Literal["MyModel", "myapp.MyModel"],
        ...
    ) -> None: ...
```
</details>

## Add type hints to methods that create an instance of a model (`DJAS002`)

A codemod that will add overloads to the `create`/`acreate` methods of managers and querysets, along with overloads for the `__init__` method of models.

The generated signature can be affected by the [`MODEL_FIELDS_OPTIONAL`](#model_fields_optional) setting.

<details>

<summary>Technical details</summary>

Stub files affected:
- `django-stubs/db/models/manager.pyi`
- `django-stubs/db/models/query.pyi`

This codemod makes use of the [PEP 692](https://peps.python.org/pep-0692/). If your type checker/LSP supports it, documentation is provided for each field if `help_text` was set.

</details>

## Add type hints to the query methods of managers and querysets (`DJAS003`)

> [!WARNING]\
> This rule is still in progress, and waiting on some Python typing features to land.

## Add type hints to `Apps.get_model` (`DJAS010`)

A codemod that will add overloads to the `Apps.get_model` method, supporting both use cases:

```python
reveal_type(apps.get_model("app_name.ModelName"))  # Revealed type is type[ModelName]
reveal_type(apps.get_model("app_name", "ModelName"))  # Revealed type is type[ModelName]
```

<details>

<summary>Technical details</summary>

Stub files affected:
- `django-stubs/apps/registry.pyi`

</details>

# Linter - automatic codemods

`django-autotyping` can also be used as a CLI program. Running the CLI will apply explicit annotations to your code.

Note that this feature is decoupled from the dynamic stubs generation, as it applies modifications
to your source code, and it might not be desirable to have these modifications automatically applied. For this reason, it is only usable as a CLI program, and doesn't require the application
to be added to your `INSTALLED_APPS`.

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

## Rules

### Add type hints to forward relations (`DJA001`)

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
> Instead, it is recommended to use the corresponding dynamic stub rule (`DJAS001`). This rule might be updated in the future to drop support for `django-types`.

### Add type hints for reverse relationships (`DJA002`)

> [!WARNING]\
> This rule is still in progress.
