# Explicit type hints

There are some cases where generating custom type stubs is not enough. In such cases, it might be required
to add some explicit type annotations to your code.

Fortunately, `django-autotyping` can automatically add these type hints in some places.

```sh
python manage.py add_type_hints --project-dir src/ --diff --ignore DJA001
```

!!! warning "Still work in progress"
    This functionality is still work in progress.

## Available rules

- [`DJA001`][django_autotyping.codemodding.codemods.forward_relation_typing_codemod.ForwardRelationTypingCodemod]: Add type annotations to forward relations.

## Configuration

This section describes the available configuration options for stubs generation. These values must be set as a dictionary under
the `CODE_GENERATION` key:

```python
AUTOTYPING = {
    "STUBS_GENERATION": {
        "PROJECT_DIR": Path(...),
    }
}
```

::: django_autotyping.app_settings.CodeGenerationSettings
    options:
        show_source: false
        members_order: source
        inherited_members: true
        signature_crossrefs: true
        show_signature_annotations: true
