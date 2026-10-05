# Research: Godot Desktop Client

Decisions for spec 007. The owner was away, and his standing rule is that he follows the
recommendation, so each decision below is a recommendation recorded for his review.

## R1. Transport between the client and the core

- **Decision**: the client starts the core as a **child process**, and the two talk through its
  standard input and output. Each message is one line of JSON (a JSON-RPC 2.0 subset).
  - In Godot 4.7, `OS.execute_with_pipe(path, args, blocking)` returns the child's stdio as a
    `FileAccess`, plus its `pid`. `OS.is_process_running` and `OS.kill` manage its lifetime.
  - The client reads replies on a background thread, so the window never waits on the pipe.
  - The core runs as `pythonw.exe -m manager_core.server`, the windowless Python, so no
    console window appears. This is to be verified in the first implementation task. If a
    console still shows, the fallback is a process-creation flag in a tiny launcher.
- **Why**:
  - Nothing listens on a port: no Windows firewall prompt, no port conflicts, and no other
    program can reach the core (FR-007).
  - The core lives and dies with the window (FR-006).
  - It needs only the standard library on the Python side (Constitution: vetted dependencies).
- **Alternatives considered**:
  - **HTTP or WebSocket on localhost**: a firewall prompt on first run on a corporate machine,
    ports to manage, and the core would have to be started separately. Rejected.
  - **Embedding Python in Godot (GDExtension)**: a native build and a heavy toolchain. Rejected.
  - **One process per request**: the career would reload each time (seconds). Rejected.

## R2. Contract shape

- **Decision**: named methods that map one-to-one to facade functions, grouped by prefix:
  `career.*`, `selection.*`, `tactic.*`, `view.*`, plus the session methods `hello` and
  `shutdown`.
  - The server keeps **one open career in memory**, as the terminal UI does. View methods act
    on it.
  - **Results** are plain JSON: dataclasses become objects, enums their values, and dates ISO
    strings.
  - **Errors** carry the core's code, a PT-BR message and details. Examples: refused swaps,
    tactic T-codes, save errors and not-found errors.
  - **Version.** The contract version is `MAJOR.MINOR`. `hello` returns it, and the client
    refuses to run on a major mismatch (FR-005). Adding a method or a field is a minor change;
    removing or renaming one is major.
- **Why**:
  - A one-to-one mapping keeps the client free of rules (Constitution III), and makes the
    contract testable method by method (SC-003).
  - JSON-RPC's request ids let a progress notification go out while a long request runs.
- **Alternatives considered**:
  - **Screen-shaped endpoints** (one call per screen): fewer calls, but rules creep into what a
    "screen" means, and the terminal UI could not share them. Rejected.
  - **A generic "call any facade function"**: no versioned surface at all. Rejected.

## R3. Long operations and progress

- **Decision**:
  - `career.continue` advances to the next stop. With `to_season_end`, it sends `progress`
    notifications (date, matches played) while it runs.
  - The client never blocks: requests are queued, answers arrive on its reader thread, and the
    UI shows a busy indicator.
  - The server handles one request at a time, in order (the core is not thread-safe, and
    determinism needs one order).
- **Why**: FR-008 and SC-004. A stop usually takes well under a second; a whole season takes a
  few seconds.

## R4. Text and localisation

- **Decision**: the client's own labels (menu, buttons, headings) come from the core's i18n
  table. `hello` returns every `ui.*` string, so PT-BR text has one source, shared with the
  terminal UI. Texts the core builds (news, feed lines, error messages) arrive already
  localised.
- **Why**: FR-009 with no duplicated string tables, and the constitution's localisation layer
  stays in one place.

## R5. Getting Godot and launching the game

- **Decision**:
  - `tools/setup_client.ps1` downloads **Godot 4.7.2-stable (win64, standard build)** from the
    official GitHub release into `tools/godot/`. That folder is gitignored, and nothing is
    installed system-wide.
  - The script checks the download against the release's published SHA-512 sum.
  - It then creates a **"Manager" desktop shortcut** that starts Godot with `--path client`.
    Double-clicking it opens the game window.
  - The client finds the core through `client/core.cfg`: the path to `.venv\Scripts\pythonw.exe`
    and the saves folder. The defaults are relative to the repo.
- **Why**:
  - FR-006: one double-click, no console.
  - The constitution fixes Godot 4.x, and 4.7.2 is the current stable (2026-08-18).
  - Exporting an executable needs export templates and adds a build step for no gain at M0.
- **Alternatives considered**:
  - **A `.bat` launcher**: it flashes a console. Rejected.
  - **A `.vbs` launcher**: VBScript is being removed from Windows 11. Rejected.
  - **An exported executable**: later, when the game is shared.

## R6. Client structure

- **Decision**: a Godot 4.7 project in `client/`:
  - `Core` (autoload): starts the process, sends requests, matches answers by id, and emits
    signals. Callers `await` a request.
  - `Main` scene: the top bar (date, club, Continue) and the left menu, with a content area that
    swaps screen scenes.
  - One scene per screen: careers (open and new), home, team selection, tactics, match day,
    squad, player, tables, calendar and news.
  - The default theme, lightly styled (spec Assumptions).

  GDScript is the only language: no C#, no GDExtension.
- **Why**: Godot's standard structure. Every screen only asks `Core` and draws the answer.

## R7. Testing

- **Core side (pytest)**:
  - a test per contract method, with valid input, invalid input and the error code;
  - framing: one line per message, unknown method, bad JSON;
  - the `hello` version;
  - **parity**: a season played through the server, with the proposed XI confirmed at every
    stop, equals the same season through the facade (SC-002).
- **Client side**:
  - a small headless runner (`godot --headless --path client -s res://tests/run_tests.gd`) with
    no add-on dependency;
  - checks that every screen scene loads and renders a canned answer;
  - and that the request queue, the error display and the version refusal work.

  A **smoke test** starts the real core through `Core`, then opens a career, continues once and
  closes.
- **CI**: the Windows job installs Godot with the same setup script (cached), and runs the
  headless client tests after the core and TUI suites.
- **Why**: Constitution IV. Most behaviour is tested where the rules are (the core). The client
  is tested for wiring and drawing.

## R8. Facade gaps found

The terminal UI reads a few things through helpers that return text (e.g. `match_stat_lines`).
The contract returns **data** instead, so the client can lay it out:
- `view.match` returns the stat lines as rows of (label, home, away).
- `view.home` gathers what the home screen shows: status, next match, position and latest news.

Both are thin additions to the facade, with tests. No rules move into them.
