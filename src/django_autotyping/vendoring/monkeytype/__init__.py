"""This is a vendorized version of MonkeyType. Source: https://github.com/Instagram/MonkeyType

Original license:

BSD License

For MonkeyType software

Copyright (c) 2017-present, Facebook, Inc. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

 * Neither the name Facebook nor the names of its contributors may be used to
   endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from __future__ import annotations

from libcst import Module
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import (
    GatherImportsVisitor,
    ImportItem,
)

from .type_checking_imports_transformer import MoveImportsToTypeCheckingBlockVisitor

__all__ = ("MoveImportsToTypeCheckingBlockVisitor", "get_newly_imported_items")


def get_newly_imported_items(stub_module: Module, source_module: Module) -> list[ImportItem]:
    context = CodemodContext()
    gatherer = GatherImportsVisitor(context)
    stub_module.visit(gatherer)
    stub_imports = list(gatherer.symbol_mapping.values())

    context = CodemodContext()
    gatherer = GatherImportsVisitor(context)
    source_module.visit(gatherer)
    source_imports = list(gatherer.symbol_mapping.values())

    return list(set(stub_imports).difference(set(source_imports)))
