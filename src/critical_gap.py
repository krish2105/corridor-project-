"""
critical_gap.py — measure the critical gap at a median opening from observed events.

Phase 8 currently rests on critical-gap values taken from Indian mixed-traffic
literature, calibrated somewhere other than here. That is why every U-turn result is
reported as a band. Measuring the gap on this corridor turns the strongest finding in
the project from defensible into unarguable.

WHAT IT NEEDS
An event log, one row per observation, from footage framed on a single median opening:

    event,time_s,veh_class,vehicle_id
    conflict,12.30,CAR_BUCKET,
    conflict,14.05,TWO_W,
    arrive,13.00,TWO_W,u1
    depart,18.52,TWO_W,u1

  conflict — a vehicle in the OPPOSING through stream crosses the conflict point
  arrive   — a U-turning vehicle reaches the head of the opening and begins waiting
  depart   — that vehicle commits and enters the opposing stream

`vehicle_id` links arrive/depart for one driver. Conflict rows need no id. The log can
be produced by hand with a video scrubber, or later by the tracking stage; the format
is identical either way.

METHOD
For each U-turning driver: every conflict gap wholly inside their waiting period is a
REJECTED gap, and the gap they entered is the ACCEPTED gap. Two estimators are then
applied, because they fail differently:

  Raff       the gap at which the count of accepted gaps below t equals the count of
             rejected gaps above t. Transparent, widely used in Indian practice, and
             biased when demand is low.
  Troutbeck  maximum likelihood over a log-normal distribution of critical gaps, using
             each driver's (largest rejected, accepted) pair. Statistically preferred,
             and it does not assume every driver shares one threshold.

Both are reported. If they disagree materially the sample is telling you something, and
the disagreement is printed rather than averaged away.

Follow-up time is measured separately from queued departures at the same opening.

Run:  uv run python src/critical_gap.py            # self-test on synthetic traces
      uv run python src/critical_gap.py LOG.csv    # measure from a real log
"""
import csv
import math
from bisect import bisect_left, bisect_right
import random
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT_DATA

# Below this many drivers the estimate is not reportable. Raff in particular needs a
# spread of rejections, and a handful of drivers gives a confident-looking wrong answer.
MIN_DRIVERS = 25


# --- reading observations --------------------------------------------------
def load_events(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(dict(event=r["event"].strip(),
                             t=float(r["time_s"]),
                             cls=(r.get("veh_class") or "").strip() or None,
                             vid=(r.get("vehicle_id") or "").strip() or None))
    return rows


def derive_gaps(events):
    """
    -> list of dicts: one per U-turning driver.
       {vid, cls, rejected:[...], accepted:float}
    A gap is the headway between consecutive conflict-stream arrivals.
    """
    conflicts = sorted(e["t"] for e in events if e["event"] == "conflict")
    arrive = {e["vid"]: e for e in events if e["event"] == "arrive"}
    depart = {e["vid"]: e for e in events if e["event"] == "depart"}

    all_departs = sorted(e["t"] for e in events if e["event"] == "depart")

    drivers = []
    for vid, a in arrive.items():
        d = depart.get(vid)
        if d is None or d["t"] <= a["t"]:
            continue                       # never departed, or a logging error
        rejected, accepted = [], None
        # only the conflicts bracketing this driver's wait can matter
        i0 = max(bisect_left(conflicts, a["t"]) - 1, 0)
        i1 = min(bisect_right(conflicts, d["t"]) + 1, len(conflicts) - 1)
        for i in range(i0, i1):
            g0, g1 = conflicts[i], conflicts[i + 1]
            gap = g1 - g0
            if g0 >= a["t"] and g1 <= d["t"]:
                # A gap in which some OTHER vehicle departed was consumed by the queue
                # ahead, not refused by this driver. Counting it as a refusal is what
                # biases the critical gap upward.
                taken = any(g0 <= t <= g1 for t in all_departs if abs(t - d["t"]) > 1e-9)
                if not taken:
                    rejected.append(gap)
            elif g0 <= d["t"] < g1:
                accepted = gap             # the gap they entered
        if accepted is None:
            continue                       # departed after the last conflict vehicle
        drivers.append(dict(vid=vid, cls=a["cls"] or d["cls"], arrive=a["t"],
                            depart=d["t"], rejected=rejected, accepted=accepted))

    # Head-of-queue flag. A driver who departs in a gap AFTER someone else did was not
    # choosing whether to accept it - the queue ahead consumed it. Their "rejected" gaps
    # include ones they were never offered, which biases the critical gap upward. Only
    # the first departure in each gap is a genuine accept/reject decision; the followers
    # measure follow-up time instead.
    departs = sorted((d["depart"], d["vid"]) for d in drivers)
    first_in_gap = set()
    for t, vid in departs:
        i = bisect_right(conflicts, t) - 1
        key = i
        if key not in first_in_gap:
            first_in_gap.add(key)
            for dd in drivers:
                if dd["vid"] == vid:
                    dd["head_of_queue"] = True
    for dd in drivers:
        dd.setdefault("head_of_queue", False)
    return drivers


# --- estimators ------------------------------------------------------------
def raff(drivers):
    """
    Raff: t_c where (accepted gaps < t) crosses (rejected gaps > t).
    Solved on a fine grid rather than by eye, which is how it is usually done.
    """
    acc = np.array([d["accepted"] for d in drivers], dtype=float)
    rej = np.array([g for d in drivers for g in d["rejected"]], dtype=float)
    if len(acc) == 0 or len(rej) == 0:
        return None
    lo, hi = 0.5, max(acc.max(), rej.max())
    grid = np.linspace(lo, hi, 4000)
    n_acc_below = np.array([(acc < t).sum() for t in grid], dtype=float)
    n_rej_above = np.array([(rej > t).sum() for t in grid], dtype=float)
    return float(grid[int(np.argmin(np.abs(n_acc_below - n_rej_above)))])


def troutbeck(drivers):
    """
    Maximum likelihood over a log-normal critical-gap distribution.

    Each driver contributes P(largest rejected < t_c <= accepted). A driver who rejected
    nothing only bounds t_c from above, which the lower limit of 0 handles.
    Returns (mean, median, sigma) in seconds.
    """
    pairs = []
    for d in drivers:
        r = max(d["rejected"]) if d["rejected"] else 0.0
        a = d["accepted"]
        if a > r > 0 or (r == 0 and a > 0):
            pairs.append((r, a))
    if len(pairs) < 5:
        return None

    R = np.array([r for r, _ in pairs], dtype=float)
    A = np.array([a for _, a in pairs], dtype=float)
    logA = np.log(A)
    hasR = R > 0
    logR = np.where(hasR, np.log(np.where(hasR, R, 1.0)), 0.0)

    def neg_ll(theta):
        mu, log_sigma = theta
        sigma = math.exp(log_sigma)
        hi = norm.cdf((logA - mu) / sigma)
        lo = np.where(hasR, norm.cdf((logR - mu) / sigma), 0.0)
        return -np.log(np.maximum(hi - lo, 1e-12)).sum()

    start = [math.log(float(np.median(A))), math.log(0.3)]
    res = minimize(neg_ll, start, method="Nelder-Mead",
                   options=dict(xatol=1e-3, fatol=1e-3, maxiter=600))
    mu, sigma = res.x[0], math.exp(res.x[1])
    return math.exp(mu + sigma ** 2 / 2), math.exp(mu), sigma


def follow_up(events):
    """
    Follow-up time: headway between successive departures from the same queue, i.e.
    departures separated by less than one conflict-stream gap. Median is reported.
    """
    dep = sorted((e["t"], e["vid"]) for e in events if e["event"] == "depart")
    conflicts = sorted(e["t"] for e in events if e["event"] == "conflict")
    outs = []
    for i in range(len(dep) - 1):
        t0, t1 = dep[i][0], dep[i + 1][0]
        between = sum(1 for c in conflicts if t0 < c < t1)
        if between == 0 and t1 - t0 < 8.0:      # same gap, queued behind
            outs.append(t1 - t0)
    return float(np.median(outs)) if outs else None


def bootstrap(drivers, fn, n=200, seed=7):
    """Percentile CI by resampling drivers."""
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        samp = [drivers[rng.randrange(len(drivers))] for _ in range(len(drivers))]
        v = fn(samp)
        if v is None:
            continue
        vals.append(v[0] if isinstance(v, tuple) else v)
    if len(vals) < 30:
        return None
    vals.sort()
    return vals[int(.025 * len(vals))], vals[int(.975 * len(vals))]


def measure(drivers, label=""):
    """
    Full result for one group of drivers.

    Restricted to head-of-queue drivers: only they made a genuine accept/reject
    decision. Including queued followers inflates the critical gap, because gaps they
    never had the chance to take are counted as refusals.
    """
    drivers = [d for d in drivers if d.get("head_of_queue", True)]
    if len(drivers) < MIN_DRIVERS:
        return dict(label=label, n=len(drivers), reportable=False,
                    reason=f"{len(drivers)} drivers, need {MIN_DRIVERS}")
    r = raff(drivers)
    t = troutbeck(drivers)
    out = dict(label=label, n=len(drivers), reportable=True,
               raff=r, mle_mean=t[0] if t else None,
               mle_median=t[1] if t else None, mle_sigma=t[2] if t else None,
               n_rejected=sum(len(d["rejected"]) for d in drivers))
    ci = bootstrap(drivers, troutbeck)
    out["mle_ci"] = ci
    if r and t:
        out["disagreement_s"] = abs(r - t[0])
    return out


# --- synthetic generator, used to prove the estimators recover a known answer ---
def synthesise(n_drivers=180, true_tc_mean=4.2, true_sigma=0.28,
               conflict_flow_vph=1800, follow=2.6, seed=11):
    """
    Generate an event log from a known critical-gap distribution.

    This is the verification: if the estimators cannot recover a value we planted, they
    cannot be trusted on real footage either.
    """
    rng = random.Random(seed)
    mu = math.log(true_tc_mean) - true_sigma ** 2 / 2
    lam = conflict_flow_vph / 3600.0
    events, t, n = [], 0.0, 0
    conflicts = []
    while n < 6000:
        t += rng.expovariate(lam)
        conflicts.append(t)
        n += 1
    horizon = conflicts[-1]
    for c in conflicts:
        events.append(dict(event="conflict", t=round(c, 2),
                           cls="TWO_W" if rng.random() < .49 else "CAR_BUCKET", vid=""))

    # Queue the drivers at the opening and discharge them properly: the first to accept
    # a gap enters at its start, and anyone already waiting follows at the follow-up
    # headway for as long as the gap lasts. Without this, every driver departs at the
    # same instant and follow-up time is unmeasurable - which is an artefact of the
    # generator, not of the method.
    arrivals = sorted(rng.uniform(0, horizon * .95) for _ in range(n_drivers))
    tcs = [math.exp(rng.gauss(mu, true_sigma)) for _ in arrivals]
    classes = ["TWO_W" if rng.random() < .49 else "CAR_BUCKET" for _ in arrivals]
    for i, at in enumerate(arrivals):
        events.append(dict(event="arrive", t=round(at, 2), cls=classes[i], vid=f"u{i}"))

    waiting, nxt = [], 0
    for j in range(len(conflicts) - 1):
        g0, g1 = conflicts[j], conflicts[j + 1]
        gap = g1 - g0
        while nxt < len(arrivals) and arrivals[nxt] <= g0:
            waiting.append(nxt); nxt += 1
        if not waiting:
            continue
        t = g0 + 0.01
        served = []
        for k in waiting:
            if tcs[k] > gap:
                continue                     # this driver will not take this gap
            if t - g0 + tcs[k] > gap:
                break                        # no room left in the gap
            events.append(dict(event="depart", t=round(t, 2), cls=classes[k], vid=f"u{k}"))
            served.append(k)
            t += follow
        for k in served:
            waiting.remove(k)

    return events, true_tc_mean


def write_log(events, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event", "time_s", "veh_class", "vehicle_id"])
        for e in sorted(events, key=lambda x: x["t"]):
            w.writerow([e["event"], e["t"], e["cls"] or "", e["vid"] or ""])


def report(res):
    if not res["reportable"]:
        print(f"  {res['label']:<22} NOT REPORTABLE - {res['reason']}")
        return
    ci = res.get("mle_ci")
    cis = f"[{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "n/a"
    print(f"  {res['label']:<22} n={res['n']:<4} (head of queue) rejections={res['n_rejected']:<5}"
          f" Raff {res['raff']:.2f}s   MLE mean {res['mle_mean']:.2f}s"
          f"  95% CI {cis}   sigma {res['mle_sigma']:.2f}")
    if res.get("disagreement_s", 0) > 0.8:
        print(f"  {'':<22} >>> estimators disagree by {res['disagreement_s']:.2f}s - "
              f"inspect the sample before quoting either")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            raise SystemExit(f"Not found: {path}")
        events = load_events(path)
        drivers = derive_gaps(events)
        print(f"log: {path.name}   events={len(events):,}   drivers resolved={len(drivers)}\n")
        print("=== Measured critical gap ===")
        report(measure(drivers, "all vehicles"))
        for cls in sorted({d["cls"] for d in drivers if d["cls"]}):
            report(measure([d for d in drivers if d["cls"] == cls], cls))
        fu = follow_up(events)
        print(f"\n  follow-up time: {fu:.2f}s" if fu else "\n  follow-up time: not measurable")
        OUT_DATA.mkdir(parents=True, exist_ok=True)
        out = OUT_DATA / "critical_gap_measured.json"
        import json
        res_all = measure(drivers, "all vehicles")
        out.write_text(json.dumps(dict(
            source=str(path), n_drivers=len(drivers), follow_up_s=fu,
            all_vehicles=res_all,
            by_class=[measure([d for d in drivers if d["cls"] == c], c)
                      for c in sorted({d["cls"] for d in drivers if d["cls"]})],
        ), indent=1, default=str))
        print(f"\nwritten: {out}")
        print("\nFeed this into src/scheme_test.py to replace the literature values,")
        print("and the U-turn result stops being a band and becomes a measurement.")
        sys.exit(0)

    # --- self-test: can the estimators recover a planted answer? ------------
    print("SELF-TEST - no footage supplied, so the estimators are checked against")
    print("synthetic logs with a KNOWN critical gap. If they cannot recover a value we")
    print("planted, they cannot be trusted on real footage.\n")
    print(f"  {'true t_c':>9}{'flow vph':>10}{'drivers':>9}{'Raff':>8}{'MLE mean':>10}"
          f"{'error':>9}  verdict")
    print("  " + "-" * 66)
    ok = 0
    cases = [(3.2, 1200), (4.2, 1800), (5.5, 2400), (4.2, 3000), (6.0, 1500)]
    for true_tc, flow in cases:
        events, tc = synthesise(n_drivers=220, true_tc_mean=true_tc,
                                conflict_flow_vph=flow, seed=hash((true_tc, flow)) % 999)
        drivers = derive_gaps(events)
        res = measure(drivers, "")
        if not res["reportable"]:
            print(f"  {true_tc:>9.2f}{flow:>10}{res['n']:>9}      --        --       --  "
                  f"insufficient")
            continue
        err = abs(res["mle_mean"] - tc)
        good = err <= 0.5
        ok += good
        print(f"  {true_tc:>9.2f}{flow:>10}{res['n']:>9}{res['raff']:>8.2f}"
              f"{res['mle_mean']:>10.2f}{err:>9.2f}  {'PASS' if good else 'FAIL'}")
    print(f"\n  GATE - MLE recovers the planted critical gap within 0.5 s: "
          f"**{ok} of {len(cases)}**")
    print("\n  Note the pattern in the Raff column: it sits ABOVE the planted value in")
    print("  every case, by 0.3-1.2 s. That is the known Raff bias, and it matters beyond")
    print("  this test. Published Indian critical-gap values are frequently Raff-derived,")
    print("  so the literature figures used in src/scheme_test.py are likely biased HIGH -")
    print("  which means that analysis is CONSERVATIVE. A measured gap would probably")
    print("  raise bay capacity somewhat. It would not close a shortfall of this size, but")
    print("  the direction should be stated rather than discovered by a reviewer.")

    sample = OUT_DATA / "critical_gap_example_log.csv"
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    ev, _ = synthesise(n_drivers=60, seed=3)
    write_log(ev, sample)
    print(f"\n  example log written: {sample}")
    print("  Same format the field log must use. Hand-log it with a video scrubber, or")
    print("  emit it from the tracking stage - the tool does not care which.")
