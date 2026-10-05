"""Localisation layer: every user-facing string goes through `t()` (Constitution: Technical
Constraints). Keys are English; the only catalogue for now is pt-BR."""

from __future__ import annotations

from manager_core.i18n.pt_BR import MESSAGES

_CATALOGUES = {"pt_BR": MESSAGES}
_locale = "pt_BR"


def t(key: str, **params: object) -> str:
    template = _CATALOGUES[_locale][key]  # a missing key is a bug: fail loudly
    return template.format(**params) if params else template


def has(key: str) -> bool:
    return key in _CATALOGUES[_locale]


def strings(prefix: str) -> dict[str, str]:
    """Every raw string whose key starts with `prefix` (for clients that draw their own labels,
    such as the Godot client's `hello`)."""
    return {k: v for k, v in _CATALOGUES[_locale].items() if k.startswith(prefix)}
