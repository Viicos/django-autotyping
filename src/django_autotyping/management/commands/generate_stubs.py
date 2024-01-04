from typing import Any, TypedDict

from django.core.management.base import BaseCommand, CommandParser

from django_autotyping.codemodding.codemods import RulesT, rules
from django_autotyping.compat import Unpack


class CommandOptions(TypedDict):
    diff: bool
    """Show diff instead of applying changes to existing files."""

    disable: list[RulesT] | None
    """Rules to be disabled."""

    type_checking_block: bool
    """Whether newly added imports should be in an `if TYPE_CHECKING` block (avoids circular imports)."""

    assume_class_getitem: bool
    """Whether generic classes in stubs files but not at runtime should be assumed
    to have a `__class_getitem__` method. This can be achieved by using `django-stubs-ext` or manually.
    """


class GenerateStubsCommand(BaseCommand):
    help = "Generate the dynamic stubs based on the current project state."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--diff",
            action="store_true",
            help="Show diff instead of applying changes to existing files.",
        )
        parser.add_argument(
            "--disable",
            choices=[rule[0] for rule in rules],
            nargs="*",
            help="Rules to be disabled.",
        )
        parser.add_argument(
            "--type-checking-block",
            action="store_true",
            help="Whether newly added imports should be in an `if TYPE_CHECKING` block (avoids circular imports).",
        )
        parser.add_argument(
            "--assume-class-getitem",
            action="store_true",
            help="Whether generic classes in stubs files but not at runtime should be assumed "
            "to have a `__class_getitem__` method. This can be achieved by using `django-stubs-ext` or manually.",
        )

    def handle(self, *args: Any, **options: Unpack[CommandOptions]) -> str | None:
        pass
