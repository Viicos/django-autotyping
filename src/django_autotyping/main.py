from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext

from .codemods import ForwardRelationTypingVisitor
from .django_utils import ModelInfo


def main(model_infos: list[ModelInfo]) -> None:
    model_filenames = set(model_info.filename for model_info in model_infos)

    # manager = FullRepoManager(".", filenames, {FullyQualifiedNameProvider})
    # manager.resolve_cache()

    for filename in model_filenames:
        code = Path(filename).read_text(encoding="utf-8")
        module = cst.parse_module(code)

        context = CodemodContext(
            filename=filename,
            scratch={},
        )
        filename_models = [model for model in model_infos if Path(model.filename) == Path(filename)]

        visitor = ForwardRelationTypingVisitor(
            context=context,
            model_infos=filename_models,
        )

        output_tree = visitor.transform_module(module)
        print(output_tree.code)
