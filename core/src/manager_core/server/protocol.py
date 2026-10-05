"""The local API's wire protocol (spec 007, contracts/local-api.md).

One JSON object per line over stdin/stdout: a subset of JSON-RPC 2.0. Requests are handled one at a
time, in order (determinism). stdout carries messages only; diagnostics go to stderr.
"""

from __future__ import annotations

import json
import sys
import traceback
from collections.abc import Callable, Iterable, Mapping
from typing import Any, TextIO

from manager_core.career.store import SaveError
from manager_core.i18n import t
from manager_core.server.encode import DecodeError, to_json

Params = dict[str, Any]


class RpcError(Exception):
    def __init__(self, code: str, message: str, data: Any = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.data = data


class Session:
    """What the server holds between requests (data-model.md). `notify` sends a notification
    for the request being handled; `stop` ends the loop after the current answer."""

    def __init__(self, out: TextIO) -> None:
        self.out = out
        self.request_id: int | None = None
        self.stop = False
        self.state: dict[str, Any] = {}

    def notify(self, method: str, params: Params) -> None:
        payload = {"request": self.request_id, **params}
        self._write({"jsonrpc": "2.0", "method": method, "params": to_json(payload)})

    def _write(self, message: Mapping[str, Any]) -> None:
        self.out.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.out.flush()


Handler = Callable[[Session, Params], Any]
ErrorMapper = Callable[[Exception], RpcError | None]


def _error_message(code: str, **params: object) -> str:
    return t(f"server.{code}", **params)


def _map_error(exc: Exception, extra: ErrorMapper | None) -> RpcError:
    if isinstance(exc, RpcError):
        return exc
    if isinstance(exc, DecodeError):
        return RpcError("P003", _error_message("P003", detail=str(exc)))
    if isinstance(exc, SaveError):
        return RpcError("SAVE", exc.message, {"save_code": exc.code})
    if extra is not None:
        mapped = extra(exc)
        if mapped is not None:
            return mapped
    traceback.print_exc(file=sys.stderr)
    return RpcError("P005", _error_message("P005", detail=f"{type(exc).__name__}: {exc}"))


def handle_line(session: Session, methods: Mapping[str, Handler], line: str,
                errors: ErrorMapper | None = None) -> None:
    """Handle one message line and write its answer (requests only; nothing else is accepted)."""
    request_id: Any = None
    try:
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RpcError("P001", _error_message("P001", detail=str(exc))) from exc
        if not isinstance(message, dict) or not isinstance(message.get("method"), str):
            raise RpcError("P001", _error_message("P001", detail="method"))
        request_id = message.get("id")
        params = message.get("params", {})
        if not isinstance(params, dict):
            raise RpcError("P003", _error_message("P003", detail="params"))
        handler = methods.get(message["method"])
        if handler is None:
            raise RpcError("P002", _error_message("P002", method=message["method"]))
        session.request_id = request_id
        result = handler(session, params)
        session._write({"jsonrpc": "2.0", "id": request_id, "result": to_json(result)})
    except Exception as exc:  # every failure becomes an answer; the server keeps running
        error = _map_error(exc, errors)
        body: dict[str, Any] = {"code": error.code, "message": error.message}
        if error.data is not None:
            body["data"] = to_json(error.data)
        session._write({"jsonrpc": "2.0", "id": request_id, "error": body})
    finally:
        session.request_id = None


def serve(session: Session, methods: Mapping[str, Handler], lines: Iterable[str],
          errors: ErrorMapper | None = None) -> None:
    for line in lines:
        if line.strip():
            handle_line(session, methods, line, errors)
        if session.stop:
            break


def param(params: Params, name: str, kind: type | tuple[type, ...], default: Any = ...) -> Any:
    """A named parameter of the expected type, or a P003 error."""
    if name not in params:
        if default is ...:
            raise RpcError("P003", _error_message("P003", detail=name))
        return default
    value = params[name]
    if kind is int and isinstance(value, float) and value.is_integer():
        value = int(value)  # clients whose JSON has one number type (Godot) send 10 as 10.0
    if not isinstance(value, kind) or (isinstance(value, bool) and kind is int):
        raise RpcError("P003", _error_message("P003", detail=name))
    return value
