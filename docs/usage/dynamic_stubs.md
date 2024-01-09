# Dynamic stubs

`django-autotyping` can generate customized type stubs depending on the current state of your Django project:

```sh
python manage.py generate_stubs --local-stubs-dir typings/ --ignore DJAS001
```

## Available rules

The following is a list of the available rules related to dynamic stubs:

- [`DJAS001`][django_autotyping.stubbing.codemods.forward_relation_overload_codemod.ForwardRelationOverloadCodemod]: add overloads to the `__init__` methods of related fields.
- [`DJAS002`][django_autotyping.stubbing.codemods.create_overload_codemod.CreateOverloadCodemod]: Add overloads to methods creating an instance of a model.
- [`DJAS010`][django_autotyping.stubbing.codemods.get_model_overload_codemod.GetModelOverloadCodemod]: Add overloads to the [`apps.get_model`][django.apps.apps.get_model] method.
- [`DJAS011`][django_autotyping.stubbing.codemods.reverse_overload_codemod.ReverseOverloadCodemod]: Add overloads to the [`reverse`][django.urls.reverse] function.


## Type checker configuration

Before making use of this feature, you must configure your type checker to discover your custom stubs:

- [`pyright`](https://github.com/microsoft/pyright/): will look for the `typings/` directory by default (see the [`stubPath` configuration option](https://microsoft.github.io/pyright/#/configuration?id=main-configuration-options)).
- [`mypy`](https://github.com/python/mypy/): configurable via the [`mypy_path`][mypy_path] value (or use the `MYPY_PATH` environment variable).

## Configuration

This section describes the available configuration options for stubs generation. These values must be set as a dictionary under
the `STUBS_GENERATION` key:

```python
AUTOTYPING = {
    "STUBS_GENERATION": {
        "LOCAL_STUBS_DIR": Path(...),
    }
}
```

::: django_autotyping.app_settings.StubsGenerationSettings
    options:
        show_source: false
        members_order: source
        inherited_members: true
        signature_crossrefs: true
        show_signature_annotations: true
