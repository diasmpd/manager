# Prototype (archived)

These are throwaway experiments from before the project adopted Spec Kit. They are kept for
reference only.

- `manager/engine.py`, `calibrate.py`, `run_match.py`, `tests/`: v0 minute-by-minute duel engine.
  It includes the first "booked players ease off" behaviour and its calibration numbers.
- `manager/models.py`, `manager/tactics.py`, `manager/generate.py`: the start of a v2 data model
  (FM attribute set, formations, team instructions), interrupted before its engine was written.
  They feed into spec 001/002.

Note: the v0 engine no longer imports cleanly, because `models.py` was overwritten by the v2 draft.
It does not need fixing. The product is rebuilt from specs.
