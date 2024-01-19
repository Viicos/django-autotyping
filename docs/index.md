# Django Autotyping

[![Python versions](https://img.shields.io/pypi/pyversions/django-autotyping.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/django-autotyping.svg)](https://pypi.org/project/django-autotyping/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

`django-autotyping` enhances your developing experience with Django by providing accurate type hints, without the need for
a custom IDE or mypy plugin:

- Generates custom [type stubs][stubs] based on the current state of your Django application, enhancing your development experience by providing auto-completions and accurate type checking.
- Automatically add explicit type hints to your source code when type stubs are not enough.

To understand the *why* and *how*, you can refer to the [context section][context].

`django-autotyping` is built with [LibCST](https://github.com/Instagram/LibCST/).

<figure markdown>
  ![Demo](assets/demo.svg)
  <figcaption>A live demo</figcaption>
</figure>

!!! warning "Still in development"
    This project is still work in progress. It is meant to work with [`django-stubs`](https://github.com/typeddjango/django-stubs), but some improvements and changes are probably going to be
    implemented in the stub definitions, and could potentially require some changes to the generated stubs.

# Installation

Through `pip`:

```sh
pip install django-autotyping
```

To make use of the dynamic stubs feature, you will also need to install [`django-stubs`](https://github.com/typeddjango/django-stubs):

```sh
pip install django-stubs
```

## Configuration

As any Django application, you will need to add `django_autotyping` to your [`INSTALLED_APPS`][INSTALLED_APPS]
(preferably in your development or local settings, if you already have them separated).

The application is configurable through the `AUTOTYPING` dict:

```python
AUTOTYPING = {
    "STUBS_GENERATION": {
        "STUBS_DIR": Path(BASE_DIR, "typings"),
    }
}
```

??? tip "Type checking configuration"
    To get typing and auto-completion support, you can make use of the
    [`AutotypingSettingsDict`][django_autotyping.typing.AutotypingSettingsDict] helper:

    ```python
    from django_autotyping.typing import AutotypingSettingsDict

    AUTOTYPING: AutotypingSettingsDict = {
        ...
    }
    ```

`django-autotyping` provides several linting rules, identified with the pattern `DJA00X` or `DJAS00X`. Rules can be disabled
using the `IGNORE` setting value.

For a complete list of available configuration values, refer to the usage section of [dynamic stubs][dynamic-stubs] and [explicit type hints][explicit-type-hints].
