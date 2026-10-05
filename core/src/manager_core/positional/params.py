"""The positional engine's parameters (spec 008): every constant is data in
`reference/positional/model.toml`, fitted by the positional tuner."""

from __future__ import annotations

import hashlib
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from importlib import resources


@dataclass(frozen=True)
class PositionalParams:
    model_version: str
    groups: Mapping[str, Mapping[str, float]]
    text: str = field(repr=False, default="")

    def __getitem__(self, group: str) -> Mapping[str, float]:
        return self.groups[group]

    def with_values(self, **changes: float) -> PositionalParams:
        """A copy with dotted-path changes, e.g. `with_values(**{"xg.distance": -0.1})`."""
        groups = {g: dict(v) for g, v in self.groups.items()}
        for dotted, value in changes.items():
            group, name = dotted.split(".", 1)
            if name not in groups[group]:
                raise KeyError(dotted)
            groups[group][name] = float(value)
        return PositionalParams(self.model_version, groups)

    @property
    def params_hash(self) -> str:
        body = repr(sorted((g, sorted(v.items())) for g, v in self.groups.items()))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()


def parse(text: str) -> PositionalParams:
    doc = tomllib.loads(text)
    version = str(doc.pop("model_version"))
    groups = {g: {k: float(v) for k, v in values.items()} for g, values in doc.items()}
    return PositionalParams(version, groups, text)


@cache
def load_params() -> PositionalParams:
    entry = resources.files("manager_core.reference").joinpath("positional").joinpath("model.toml")
    return parse(entry.read_text("utf-8"))
