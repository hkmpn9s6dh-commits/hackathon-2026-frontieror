"""Objective direction per problem, and the competition's instance score.

The scoring page gives one formula per direction (`/docs/main/scoring`):

    minimise: both positive -> reference / objective
    maximise: both positive -> objective / reference
    equal values score 1; a better one up to 2.

Reading the direction off the problem statement matters: `fischetti1998` is a
maximisation problem (collect prizes), so dividing the other way turns a 0.80 into
a 1.25 and invents a result that is not there. The direction below is quoted from
each `problem_description.txt`.
"""

from __future__ import annotations

DIRECTION = {
    "cordeau2006": "minimize",   # "minimize the total routing cost"
    "fischetti1998": "maximize",  # "maximize the total prize collected"
    "barnhart2000": "minimize",   # "minimize the total cost"
    "hoffman1993": "minimize",    # "minimizing the total cost"
    "bodur2017": "minimize",      # "minimize total expected cost"
    "nagy2015": "minimize",       # "minimize the total distance travelled"
}


def score(reference: float, value: float, direction: str) -> float:
    if reference is None or value is None:
        return 0.0
    if reference == 0:
        better = value < 0 if direction == "minimize" else value > 0
        return 2.0 if better else 0.0
    if (reference > 0) != (value > 0):
        better = value < reference if direction == "minimize" else value > reference
        return 2.0 if better else 0.0
    if direction == "minimize":
        ratio = reference / value if reference > 0 else value / reference
    else:
        ratio = value / reference if reference > 0 else reference / value
    return max(0.0, min(2.0, ratio))
