from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field, replace

from django.urls import URLPattern, URLResolver


@dataclass(eq=True, frozen=True)
class PathArguments:
    """Describes the available arguments for a specific Django view."""

    arguments: frozenset[tuple[str, bool]] = field(default_factory=frozenset)

    def __len__(self) -> int:
        return len(self.arguments)

    def __bool__(self) -> bool:
        return bool(len(self))

    @property
    def sha1(self) -> str:
        stringified = "".join(f"{k}={v}" for k, v in sorted(self.arguments, key=lambda arg: arg[0]))
        return hashlib.sha1(stringified.encode("utf-8")).hexdigest()

    @property
    def typeddict_name(self) -> str:
        return f"_{self.sha1[:6].upper()}Kwargs"

    def is_mergeable(self, arguments: dict[str, bool]) -> bool:
        """Return whether the keys of the provided arguments are the same as the current instance."""
        return {arg[0] for arg in self.arguments} == set(arguments)

    def with_new_arguments(self, arguments: dict[str, bool]) -> PathArguments:
        new_arguments = frozenset((k, False if not arguments[k] else is_required) for k, is_required in self.arguments)
        return replace(self, arguments=new_arguments)


@dataclass(eq=True, frozen=True)
class PathInfo:
    """Describes the set of available arguments for a Django view.

    At its core, this class holds a set of the possible combinations of arguments for a view.
    If multiple views are registered with the same name, a call to `reverse` can match any of
    these views depending on the provided arguments and the order they appear in the URL patterns list.
    """

    arguments_set: frozenset[PathArguments] = field(default_factory=frozenset)

    @property
    def is_empty(self) -> bool:
        return all(not args for args in self.arguments_set)

    def with_new_arguments(self, arguments: dict[str, bool]) -> PathInfo:
        unfrozen_set = set(self.arguments_set)

        for args in self.arguments_set:
            if args.is_mergeable(arguments):
                new_args = args.with_new_arguments(arguments)
                unfrozen_set.remove(args)
                unfrozen_set.add(new_args)
                break
        else:
            # Provided arguments aren't mergeable, add a new entry
            unfrozen_set.add(PathArguments(frozenset(arguments.items())))
        return replace(self, arguments_set=frozenset(unfrozen_set))

    def get_kwargs_annotation(self) -> str:
        """Return the type annotation for the `kwargs` argument of `reverse`."""
        tds_str = [args.typeddict_name for args in self.arguments_set if args]
        if any(not args for args in self.arguments_set):
            tds_str.extend(["EmptyDict", "None"])

        return " | ".join(tds_str)

    def get_args_annotation(self, list_fallback: bool = True) -> str:
        """Return the type annotation for the `args` argument of `reverse`.

        If multiple URL patterns are available for a specific URL name (i.e. `arguments_set` contains
        multiple entries), the generated annotation will be the union of the possible tuple shapes.

        Args:
            list_fallback: Whether to include a `list[Any]` fallback type.
        """
        args_lengths = sorted([len(args) for args in self.arguments_set], reverse=True)
        tuples_str = [
            f"tuple[{', '.join('SupportsStr' for _ in range(length))}]" for length in args_lengths if length > 0
        ]
        if 0 in args_lengths:
            tuples_str.append("tuple[()]")
        if list_fallback:
            tuples_str.append("list[Any]")
        if 0 in args_lengths:
            tuples_str.append("None")

        return " | ".join(tuples_str)


def get_paths_infos(
    url_resolver: URLResolver,
    parent_namespaces: list[str] | None = None,
) -> defaultdict[str, PathInfo]:
    parent_namespaces = parent_namespaces or []
    paths_info: defaultdict[str, PathInfo] = defaultdict(PathInfo)

    for pattern in reversed(url_resolver.url_patterns):  # Parsing in reverse is important!
        if isinstance(pattern, URLPattern) and pattern.name:
            key = ":".join(parent_namespaces)
            if key:
                key += ":"
            key += pattern.name

            reverse_entries = url_resolver.reverse_dict.getlist(pattern.name)

            for possibility, _, defaults, _ in reverse_entries:
                for _, params in possibility:
                    # TODO should `defaults` really be taken into account?
                    # something weird is happening in `_reverse_with_prefix`:
                    # if any(kwargs.get(k, v) != v for k, v in defaults.items()): skip candidate
                    paths_info[key] = paths_info[key].with_new_arguments({k: (k not in defaults) for k in params})
        elif isinstance(pattern, URLResolver):
            new_parent_namespaces = parent_namespaces.copy()
            if pattern.namespace:
                new_parent_namespaces.append(pattern.namespace)

            paths_info = defaultdict(PathInfo, **paths_info, **get_paths_infos(pattern, new_parent_namespaces))
    return paths_info
