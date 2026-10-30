"""Explicit truth states and normalized exact scoring, version 1."""
from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Callable

class TruthState(StrEnum):
    VALUE = "value"
    ABSENT = "absent"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class TruthField:
    state: TruthState
    value: str | None = None

def score_truth_field(
    truth: TruthField,
    prediction: object,
    value_scorer: Callable[[object, object], dict | None],
) -> dict | None:
    """Apply explicit schema-v2 truth-state semantics around a value scorer."""
    if truth.state is TruthState.UNKNOWN:
        return None
    if truth.state in {TruthState.ABSENT, TruthState.NOT_APPLICABLE}:
        passed = prediction is None
        outcome = (
            f"correct_{truth.state.value}" if passed else "spurious"
        )
        return {
            "pass": passed,
            "outcome": outcome,
            "truth_state": truth.state.value,
            "truth": None,
            "pred": prediction,
        }
    result = value_scorer(truth.value, prediction)
    if result is None:
        raise ValueError("typed truth value was not scored")
    scored = dict(result)
    scored["truth_state"] = TruthState.VALUE.value
    return scored

def _norm_exact(value: object) -> str:
    if type(value) is not str:
        return ""
    return " ".join(value.strip().casefold().split())

def score_exact(truth, pred):
    passed = isinstance(pred, str) and _norm_exact(truth) == _norm_exact(pred)
    return {"pass": passed, "truth": truth, "pred": pred,
            "outcome": "exact" if passed else ("missing" if pred is None else "wrong_value")}
