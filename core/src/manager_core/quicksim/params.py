"""Quick-sim model parameters as data (research R9).

All constants of the model live in `reference/quicksim/model.toml`, so a calibration change is a
reviewable data diff. Every calibration report records `model_version` and `params_hash`.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import tomllib
from dataclasses import dataclass, fields
from importlib import resources
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from manager_core.i18n import t


@dataclass(frozen=True, slots=True)
class Rates:
    """Per side per minute, unless stated otherwise."""

    shot: float
    foul: float
    corner_per_shot: float  # corners per shot taken (pressure proxy)
    corner_base: float
    penalty: float
    own_goal_share: float  # share of goals turned into own goals
    yellow_per_foul: float
    direct_red_per_foul: float


@dataclass(frozen=True, slots=True)
class Strength:
    attack: float  # shot-rate slope per 5 rating points of attack − opposing defence
    control: float  # shot-rate slope per 5 points of control difference
    keeper: float  # goal-probability slope per 5 points of goalkeeping above 10
    xg_median: float
    xg_sigma: float
    xg_attack: float  # xG median slope per 5 points of attack − opposing defence


@dataclass(frozen=True, slots=True)
class Home:
    shot: float  # multiplier on the home side's shot rate
    possession: float


@dataclass(frozen=True, slots=True)
class Time:
    trend_start: float
    trend_end: float


@dataclass(frozen=True, slots=True)
class State:
    chase: float
    exposed: float
    protect: float
    man_up: float


@dataclass(frozen=True, slots=True)
class Caution:
    enabled: bool
    foul: float
    card: float
    cost: float


@dataclass(frozen=True, slots=True)
class Stoppage:
    first: tuple[int, int]
    second: tuple[int, int]


@dataclass(frozen=True, slots=True)
class Subs:
    halftime_chance: float
    windows: tuple[tuple[int, int], ...]
    max: int
    window_chance: float  # chance a side uses each in-play window
    per_window: tuple[int, int]


@dataclass(frozen=True, slots=True)
class LineWeights:
    goalkeeper: float
    defender: float
    midfielder: float
    attacking_mid: float
    forward: float


@dataclass(frozen=True, slots=True)
class Scorers:
    line_weights: LineWeights
    header_share: float
    header_defender_weight: float
    assist_share: float


@dataclass(frozen=True, slots=True)
class ShootoutParams:
    base: float
    taker: float
    composure: float
    keeper: float
    low: float
    high: float


@dataclass(frozen=True, slots=True)
class ModelParams:
    model_version: str
    rates: Rates
    strength: Strength
    home: Home
    time: Time
    state: State
    caution: Caution
    stoppage: Stoppage
    subs: Subs
    scorers: Scorers
    shootout: ShootoutParams

    @property
    def params_hash(self) -> str:
        canonical = json.dumps(dataclasses.asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def with_values(self, **changes: float | bool) -> ModelParams:
        """A copy with dotted-path changes, e.g. `with_values(**{"rates.shot": 0.14})`."""
        result: Any = self
        for dotted, value in changes.items():
            result = _replace_path(result, dotted.split("."), value)
        return result  # type: ignore[no-any-return]


def _replace_path(obj: Any, path: list[str], value: object) -> Any:
    if len(path) == 1:
        return dataclasses.replace(obj, **{path[0]: value})
    return dataclasses.replace(obj, **{path[0]: _replace_path(getattr(obj, path[0]), path[1:],
                                                               value)})


class ModelParamsError(ValueError):
    def __init__(self, problems: list[tuple[str, str]]) -> None:
        self.problems = problems  # (code, key path)
        super().__init__("; ".join(t(f"quicksim.{code}", path=path) for code, path in problems))


# Fields that are probabilities or shares must lie in (0, 1).
_UNIT_INTERVAL = {"rates.shot", "rates.foul", "rates.corner_per_shot", "rates.corner_base",
                  "rates.penalty", "rates.own_goal_share", "rates.yellow_per_foul",
                  "rates.direct_red_per_foul", "subs.halftime_chance", "subs.window_chance",
                  "scorers.header_share", "scorers.assist_share", "caution.foul",
                  "caution.card", "caution.cost", "shootout.base", "shootout.low",
                  "shootout.high", "strength.xg_median"}


def _build[T](cls: type[T], raw: object, path: str,
              problems: list[tuple[str, str]]) -> T | None:
    if not isinstance(raw, dict):
        problems.append(("Q001", path or "<root>"))
        return None
    hints = get_type_hints(cls)
    values: dict[str, object] = {}
    for f in fields(cls):  # type: ignore[arg-type]
        key = f"{path}.{f.name}" if path else f.name
        if f.name not in raw:
            problems.append(("Q001", key))
            continue
        value = _convert(hints[f.name], raw[f.name], key, problems)
        if value is not None:
            values[f.name] = value
    if len(values) != len(fields(cls)):  # type: ignore[arg-type]
        return None
    return cls(**values)


def _convert(kind: Any, raw: object, path: str, problems: list[tuple[str, str]]) -> object:
    if dataclasses.is_dataclass(kind):
        return _build(kind, raw, path, problems)  # type: ignore[arg-type]
    if kind is bool:
        if isinstance(raw, bool):
            return raw
    elif kind is int:
        if isinstance(raw, int) and not isinstance(raw, bool):
            return raw
    elif kind is float:
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            value = float(raw)
            if path in _UNIT_INTERVAL and not 0 < value < 1:
                problems.append(("Q001", path))
                return None
            return value
    elif kind is str:
        if isinstance(raw, str):
            return raw
    elif get_origin(kind) is tuple and isinstance(raw, list):
        args = get_args(kind)
        if len(args) == 2 and args[1] is Ellipsis:
            items = [_convert(args[0], r, f"{path}[{i}]", problems) for i, r in enumerate(raw)]
            return tuple(items) if None not in items else None
        if len(raw) == len(args) and all(isinstance(r, int) for r in raw):
            pair = tuple(raw)
            if len(pair) == 2 and pair[0] > pair[1]:  # ranges must be ordered
                problems.append(("Q001", path))
                return None
            return pair
    problems.append(("Q001", path))
    return None


def _parse(text: str) -> ModelParams:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ModelParamsError([("Q001", f"<toml: {exc}>")]) from exc
    problems: list[tuple[str, str]] = []
    params = _build(ModelParams, doc, "", problems)
    if problems or params is None:
        raise ModelParamsError(problems or [("Q001", "<root>")])
    if params.shootout.low >= params.shootout.high:
        raise ModelParamsError([("Q001", "shootout.low")])
    return params


def load_params() -> ModelParams:
    entry = resources.files("manager_core.reference").joinpath("quicksim").joinpath("model.toml")
    return _parse(entry.read_text("utf-8"))


def load_params_file(path: Path) -> ModelParams:
    return _parse(path.read_text("utf-8"))


def dump_params(params: ModelParams) -> str:
    """TOML text for a parameter set (used by the tuning tool)."""
    lines = [f'model_version = "{params.model_version}"', ""]

    def fmt(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            return repr(round(value, 6))
        if isinstance(value, tuple):
            return "[" + ", ".join(fmt(v) for v in value) + "]"
        if isinstance(value, str):
            return f'"{value}"'
        return str(value)

    def table(name: str, obj: Any) -> None:
        lines.append(f"[{name}]")
        nested = []
        for f in fields(obj):
            value = getattr(obj, f.name)
            if dataclasses.is_dataclass(value):
                nested.append((f"{name}.{f.name}", value))
            else:
                lines.append(f"{f.name} = {fmt(value)}")
        lines.append("")
        for sub_name, sub in nested:
            table(sub_name, sub)

    for f in fields(params):
        value = getattr(params, f.name)
        if dataclasses.is_dataclass(value):
            table(f.name, value)
    return "\n".join(lines)
