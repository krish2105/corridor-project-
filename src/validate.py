"""
validate.py — manual ground truth against automated counts.

The section a reviewer reads first, and the reason the rest can be trusted. Automated
counts without this are an assertion; with it they are a measurement with a stated error.

Acceptance thresholds are set in advance, per the methodology, and a failure is reported
rather than worked around:

    total vehicle MAPE            < 5% target, < 10% minimum
    per-class MAPE, 2W/car/auto   < 10% target, < 15% minimum
    per-class MAPE, bus/truck/MAV < 10% target, < 20% minimum (low counts inflate
                                    percentage error, so the looser bound is not laxity)
    movement assignment accuracy  > 95% target, > 90% minimum

MAPE is computed on paired 15-minute intervals, never on daily totals. Totals hide
compensating errors: an over-count in one interval cancels an under-count in another and
the day looks perfect while every interval is wrong.

Run:  uv run python src/validate.py     # self-test on synthetic pairs
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GATES = {
    "total":      dict(target=0.05, minimum=0.10),
    "major":      dict(target=0.10, minimum=0.15),   # 2W, car bucket, auto
    "minor":      dict(target=0.10, minimum=0.20),   # bus, truck, MAV - low counts
    "assignment": dict(target=0.95, minimum=0.90),   # higher is better
}
MAJOR = {"TWO_W", "CAR_BUCKET", "AUTO_TRK_BUS"}


def mape(manual, auto):
    """
    Mean absolute percentage error over paired intervals.

    Intervals where the manual count is zero are excluded: percentage error is undefined
    there, and including them as 100% error whenever the detector sees anything makes the
    statistic meaningless on rare classes.
    """
    m = np.asarray(manual, dtype=float)
    a = np.asarray(auto, dtype=float)
    live = m > 0
    if not live.any():
        return None, 0
    return float(np.mean(np.abs(a[live] - m[live]) / m[live])), int(live.sum())


def grade(value, gate, higher_is_better=False):
    if value is None:
        return "no data"
    g = GATES[gate]
    if higher_is_better:
        return "PASS" if value >= g["target"] else ("MARGINAL" if value >= g["minimum"] else "FAIL")
    return "PASS" if value <= g["target"] else ("MARGINAL" if value <= g["minimum"] else "FAIL")


def validate(pairs, assignment_accuracy=None):
    """
    pairs: {veh_class: [(manual, auto), ...]} one tuple per 15-minute interval.
    Returns a report dict. Nothing is rounded away; the caller decides presentation.
    """
    per_class, tot_m, tot_a = {}, [], []
    for cls, obs in pairs.items():
        m = [p[0] for p in obs]
        a = [p[1] for p in obs]
        val, n = mape(m, a)
        band = "major" if cls in MAJOR else "minor"
        per_class[cls] = dict(mape=val, intervals=n, band=band,
                              verdict=grade(val, band),
                              manual_total=int(sum(m)), auto_total=int(sum(a)))
        tot_m.append(m)
        tot_a.append(a)

    n_int = max(len(x) for x in tot_m)
    tm = np.zeros(n_int)
    ta = np.zeros(n_int)
    for m, a in zip(tot_m, tot_a):
        tm[:len(m)] += m
        ta[:len(a)] += a
    total_mape, n = mape(tm, ta)

    out = dict(total=dict(mape=total_mape, intervals=n, verdict=grade(total_mape, "total"),
                          manual_total=int(tm.sum()), auto_total=int(ta.sum())),
               per_class=per_class)
    if assignment_accuracy is not None:
        out["assignment"] = dict(accuracy=assignment_accuracy,
                                 verdict=grade(assignment_accuracy, "assignment", True))
    fails = [k for k, v in per_class.items() if v["verdict"] == "FAIL"]
    if out["total"]["verdict"] == "FAIL":
        fails.append("TOTAL")
    if assignment_accuracy is not None and out["assignment"]["verdict"] == "FAIL":
        fails.append("ASSIGNMENT")
    marg = [k for k, v in per_class.items() if v["verdict"] == "MARGINAL"]
    if out["total"]["verdict"] == "MARGINAL":
        marg.append("TOTAL")
    if assignment_accuracy is not None and out["assignment"]["verdict"] == "MARGINAL":
        marg.append("ASSIGNMENT")
    # Accepted means above the MINIMUM. Meeting target is a separate, higher bar, and
    # conflating them lets a barely-passing dataset be reported as a clean one.
    out["accepted"] = len(fails) == 0
    out["meets_target"] = len(fails) == 0 and len(marg) == 0
    out["failed_gates"] = fails
    out["marginal_gates"] = marg
    return out


def report(res):
    t = res["total"]
    print(f"  {'metric':<22}{'manual':>10}{'auto':>10}{'MAPE':>9}{'intervals':>11}  verdict")
    print("  " + "-" * 72)
    print(f"  {'TOTAL':<22}{t['manual_total']:>10,}{t['auto_total']:>10,}"
          f"{t['mape']:>8.1%}{t['intervals']:>11}  {t['verdict']}")
    for cls, v in sorted(res["per_class"].items(), key=lambda kv: -kv[1]["manual_total"]):
        mp = f"{v['mape']:.1%}" if v["mape"] is not None else "--"
        print(f"  {cls:<22}{v['manual_total']:>10,}{v['auto_total']:>10,}"
              f"{mp:>9}{v['intervals']:>11}  {v['verdict']}")
    if "assignment" in res:
        a = res["assignment"]
        print(f"\n  movement assignment accuracy: {a['accuracy']:.1%}  {a['verdict']}")
    print()
    if not res["accepted"]:
        print(f"  NOT ACCEPTED - below the minimum on: {', '.join(res['failed_gates'])}")
        print("  Fix the pipeline before these counts are used for anything.")
    elif not res["meets_target"]:
        print(f"  ACCEPTED, but only marginally on: {', '.join(res['marginal_gates'])}")
        print("  Above the minimum, below target. Usable, and the shortfall must be stated")
        print("  in the report rather than rounded to 'validated'.")
    else:
        print("  ACCEPTED - every gate at target.")


def _synth(bias=0.0, noise=0.06, n_intervals=8, seed=1):
    """Paired manual/auto counts with a known systematic bias and random error."""
    rng = np.random.default_rng(seed)
    base = {"TWO_W": 420, "CAR_BUCKET": 380, "AUTO_TRK_BUS": 24,
            "AGRI_LCV": 9, "TRL_MAV": 5}
    pairs = {}
    for cls, mean in base.items():
        obs = []
        for _ in range(n_intervals):
            m = max(0, int(rng.poisson(mean)))
            a = max(0, int(round(m * (1 + bias) * (1 + rng.normal(0, noise)))))
            obs.append((m, a))
        pairs[cls] = obs
    return pairs


if __name__ == "__main__":
    print("SELF-TEST - no counts exist yet, so the gates are checked against synthetic")
    print("manual/auto pairs with a KNOWN bias. The statistic must catch what we planted.\n")
    print(f"  {'planted bias':>13}{'noise':>8}{'total MAPE':>12}{'verdict':>10}   expected")
    print("  " + "-" * 60)
    ok = 0
    cases = [(0.00, 0.03, "PASS"), (0.03, 0.03, "PASS"),
             (0.08, 0.03, "MARGINAL"), (0.18, 0.04, "FAIL"), (-0.14, 0.04, "FAIL")]
    for bias, noise, expect in cases:
        res = validate(_synth(bias=bias, noise=noise, seed=int(abs(bias) * 100) + 3))
        got = res["total"]["verdict"]
        good = got == expect
        ok += good
        print(f"  {bias:>12.0%}{noise:>8.0%}{res['total']['mape']:>11.1%}{got:>10}"
              f"   {expect}  {'ok' if good else 'MISMATCH'}")
    print(f"\n  GATE - verdict matches the planted bias: **{ok} of {len(cases)}**")

    print("\n  Worked example, 8% high bias:\n")
    report(validate(_synth(bias=0.08, noise=0.03, seed=11), assignment_accuracy=0.93))
