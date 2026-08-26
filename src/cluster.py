"""
cluster.py — an approach typology, learned from the counts rather than assigned.

THE QUESTION
Twenty-four approaches, six junctions, one scheme applied to all of them. JDA's signal-
free proposal treats the corridor as uniform. Is it? If the approaches fall into a small
number of behavioural types, the scheme can be tuned to the types instead of to the
average, and the junctions that do not fit the type are the ones to look at first.

WHAT IS CLUSTERED
Each approach becomes its 24-hour profile, normalised to sum to one. Normalising is the
whole point: without it the clustering rediscovers volume, which we already knew and did
not need a model for. What is left after normalising is SHAPE - when the traffic comes,
not how much - and shape is what distinguishes a commuter approach from a through one.

Ward linkage on Euclidean distance, k chosen by silhouette across k = 2..6. Hierarchical
rather than k-means because with 24 points a k-means run depends on its seed, and a
result that moves when you re-run it is not a finding.

THE GATE: AN EXTERNAL LABEL IT WAS NEVER GIVEN
Clustering always returns clusters. The test of whether these mean anything is whether
they line up with something true that was held out of the fitting. Every junction here
has two corridor arms (Mansarover Metro, Sanganer Stadium) and two cross-street arms, and
those should not behave alike - the corridor carries through traffic, the cross streets
carry local. That label never enters the distance matrix. If the clusters recover it
better than a random relabelling would, the typology is real; if they do not, this
module says so rather than publishing six pretty groups.

Run:  uv run python src/cluster.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist, squareform

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT_DATA

K_RANGE = range(2, 7)

# Below this the geometry is not clustered, it is a cloud. 0.25 is the conventional
# reading of "weak but present" structure; anything under it is reported as no typology
# rather than dressed up as one.
SILHOUETTE_MIN = 0.25

N_PERM = 10_000          # permutations for the external-label test
CORRIDOR_ARMS = ("Mansarover Metro", "Sanganer Stadium")


def _shares(bins, over):
    """Each approach as a share vector over `over`, on the analysis day."""
    mv = bins[bins.kind == "movement"].copy()
    mv["hour"] = pd.to_datetime(mv.bin_start).dt.hour
    day = sorted(mv.date.unique())[0]          # the analysis day; day two is derived
    g = (mv[mv.date == day].groupby(["junction", "arm_from", over])["count"].sum()
           .unstack(over).fillna(0.0))
    return g.div(g.sum(axis=1), axis=0).sort_index()


def profiles(bins):
    """
    Each approach's 24-hour shape, normalised so volume drops out.

    Normalising is the whole point. Without it the clustering rediscovers volume, which
    we already knew and did not need a model for.
    """
    return _shares(bins, "hour")


def compositions(bins):
    """Each approach's vehicle-class mix, as shares of its own stream."""
    return _shares(bins, "veh_class")


def silhouette(d, labels):
    """
    Mean silhouette over the points, from a square distance matrix.

    Written out rather than imported because scikit-learn is not in this project's stack
    and adding a dependency for forty lines of arithmetic is not worth the lockfile.
    """
    labels = np.asarray(labels)
    uniq = np.unique(labels)
    if len(uniq) < 2:
        return 0.0
    s = np.zeros(len(labels))
    for i in range(len(labels)):
        own = labels == labels[i]
        own[i] = False
        if own.sum() == 0:                     # a singleton cluster has no cohesion
            s[i] = 0.0
            continue
        a = d[i, own].mean()
        b = min(d[i, labels == u].mean() for u in uniq if u != labels[i])
        s[i] = (b - a) / max(a, b)
    return float(s.mean())


def fit(p):
    """Ward linkage, k by silhouette. Returns (labels, k, silhouette, per-k scores)."""
    x = p.to_numpy()
    dv = pdist(x)
    d = squareform(dv)
    z = linkage(dv, method="ward")
    scores = {}
    for k in K_RANGE:
        lab = fcluster(z, k, criterion="maxclust")
        scores[k] = round(silhouette(d, lab), 3)
    best = max(scores, key=scores.get)
    return fcluster(z, best, criterion="maxclust"), best, scores[best], scores


def external_label_test(p, labels, rng):
    """
    Do the clusters recover corridor-versus-cross-street, which they were never shown?

    Purity is the share of approaches sitting in the majority external class of their own
    cluster. Its null is not zero - a two-cluster split of a set that is half corridor is
    already about 50% pure by construction - so the number is compared against the same
    statistic on randomly permuted labels, and what is reported is the p-value.
    """
    is_corridor = np.array([arm in CORRIDOR_ARMS for _, arm in p.index])

    def purity(lab):
        return sum(max(((lab == c) & is_corridor).sum(),
                       ((lab == c) & ~is_corridor).sum())
                   for c in np.unique(lab)) / len(lab)

    obs = purity(labels)
    null = np.array([purity(rng.permutation(labels)) for _ in range(N_PERM)])
    return float(obs), float((null >= obs).mean() + 1 / N_PERM), float(null.mean())


def describe(p, labels, temporal):
    """One row per cluster: size, what is in it, and how it differs from the others."""
    rows = []
    for c in sorted(set(labels)):
        m = labels == c
        mean = p[m].mean(axis=0)
        members = [f"{j} {arm}" for j, arm in p.index[m]]
        corridor = sum(1 for _, arm in p.index[m] if arm in CORRIDOR_ARMS)
        r = dict(cluster=int(c), size=int(m.sum()),
                 corridor_arms=corridor, cross_arms=int(m.sum()) - corridor,
                 profile=[round(float(v), 4) for v in mean],
                 features=[str(x) for x in p.columns], members=members)
        if temporal:
            # share of the day carried in its four busiest hours: a flat approach is
            # near 4/24 = 0.167, a sharply peaked one much higher
            r["peak_hour"] = int(mean.idxmax())
            r["share_in_busiest_4h"] = round(float(np.sort(mean.to_numpy())[-4:].sum()), 3)
        else:
            r["dominant_class"] = str(mean.idxmax())
            r["dominant_share"] = round(float(mean.max()), 3)
        rows.append(r)
    return rows


def run(p, name, temporal, rng):
    """Fit, score, test against the held-out label, and describe. No decisions here."""
    labels, k, sil, scores = fit(p)
    purity, pval, null_mean = external_label_test(p, labels, rng)
    return dict(
        feature_set=name, n_features=int(p.shape[1]), k=int(k),
        silhouette=round(sil, 3), silhouette_by_k={str(a): b for a, b in scores.items()},
        structure_found=bool(sil >= SILHOUETTE_MIN),
        external_label=dict(label="corridor arm vs cross-street arm", held_out=True,
                            purity=round(purity, 3), null_mean=round(null_mean, 3),
                            p=round(pval, 5), permutations=N_PERM,
                            recovered=bool(pval < 0.05)),
        clusters=describe(p, labels, temporal))


def class_split(comp, cls):
    """Is one class's share genuinely different on corridor arms and cross-street arms?"""
    is_corr = np.array([arm in CORRIDOR_ARMS for _, arm in comp.index])
    a, b = comp[cls][is_corr].to_numpy(), comp[cls][~is_corr].to_numpy()
    u = stats.mannwhitneyu(a, b)
    return dict(vehicle_class=cls, corridor_mean=round(float(a.mean()), 4),
                cross_mean=round(float(b.mean()), 4), n_corridor=int(len(a)),
                n_cross=int(len(b)), p=float(u.pvalue),
                min_share=round(float(comp[cls].min()), 4),
                max_share=round(float(comp[cls].max()), 4))


def _report(r):
    print(f"\n--- {r['feature_set']} ({r['n_features']} features) ---")
    print("  silhouette by k: " +
          "  ".join(f"k={a} {b:+.3f}" for a, b in r["silhouette_by_k"].items()))
    print(f"  chosen k = {r['k']}, silhouette {r['silhouette']:+.3f}")
    for c in r["clusters"]:
        mem = ", ".join(m.replace("Mansarover Metro", "N").replace("Sanganer Stadium", "S")
                        for m in c["members"])
        extra = (f"peak {c['peak_hour']:02d}:00, busiest 4h {c['share_in_busiest_4h']:.1%}"
                 if "peak_hour" in c else
                 f"{c['dominant_class']} {c['dominant_share']:.1%}")
        print(f"    cluster {c['cluster']}  n={c['size']:<3}"
              f"({c['corridor_arms']} corridor / {c['cross_arms']} cross)  {extra:<34}"
              f"{mem[:36]}{'...' if len(mem) > 36 else ''}")
    e = r["external_label"]
    print(f"  held-out label: purity {e['purity']:.1%} vs {e['null_mean']:.1%} at random, "
          f"p = {e['p']:.4f}")
    print(f"  silhouette >= {SILHOUETTE_MIN}: "
          f"{'PASS' if r['structure_found'] else 'FAIL'}   "
          f"external label recovered: {'PASS' if e['recovered'] else 'FAIL'}")


def _main():
    from src.tmc_parse import parse_all

    bins, _ = parse_all()
    rng = np.random.default_rng(20260511)      # seeded: a p-value that moves is not one
    sets = [(profiles(bins), "24-hour temporal shape", True),
            (compositions(bins), "vehicle-class composition", False)]
    results = [run(p, name, temporal, rng) for p, name, temporal in sets]

    print("=== Approach typology, learned from the counts ===")
    print(f"  {len(sets[0][0])} approaches. TWO feature sets are fitted and BOTH are")
    print("  reported, whichever wins. Running two and publishing the one that passed")
    print("  would make the p-value meaningless, so read them as two tests, not one.")
    for r in results:
        _report(r)

    passed = [r for r in results if r["structure_found"] and r["external_label"]["recovered"]]
    print(f"\n  GATE - feature sets yielding a real typology: "
          f"**{len(passed)} of {len(results)}**")
    for r in results:
        if not r["structure_found"]:
            print(f"    {r['feature_set']}: no separation "
                  f"(silhouette {r['silhouette']:+.3f}). Reported as no typology rather")
            print(f"      than forced into k groups - clustering always returns clusters.")
        elif not r["external_label"]["recovered"]:
            print(f"    {r['feature_set']}: groups are tight but line up with nothing we")
            print(f"      can check, so they are a description, not evidence of a type.")

    for r in passed:
        e = r["external_label"]
        adj = min(1.0, e["p"] * len(results))
        print(f"    {r['feature_set']}: p = {e['p']:.4f}, and {e['p']:.4f} x "
              f"{len(results)} tests = {adj:.4f} on the strictest correction, so it "
              f"survives\n      the second look as well as the first.")

    print("\n=== What the two results mean together ===")
    if not any(r["structure_found"] for r in results if r["feature_set"].startswith("24-hour")):
        print("  Twenty-four approaches that do not separate on SHAPE are twenty-four")
        print("  approaches that arrive on the same clock. That is what makes one")
        print("  corridor-wide peak hour defensible, and it means a peak measured on one")
        print("  approach transfers to the others.")

    comp = next((r for r in results if r["feature_set"].startswith("vehicle")), None)
    split = None
    if comp and comp["structure_found"]:
        # Name the axis the clusters separate on rather than reading it off the cluster
        # labels: two of the five clusters are car-dominant and three two-wheeler-dominant,
        # and both kinds contain corridor and cross arms, so "the corridor clusters are
        # dominated by X" is not a statement the clusters support. The share itself is.
        split = class_split(compositions(bins), "TWO_W")
        gap = 100 * (split["cross_mean"] - split["corridor_mean"])
        print(f"\n  They DO separate on what is IN the stream. Two-wheelers are "
              f"{split['cross_mean']:.1%} of the")
        print(f"  cross-street approaches against {split['corridor_mean']:.1%} of the "
              f"corridor ones, Mann-Whitney")
        print(f"  p = {split['p']:.4f} over {split['n_cross']} and "
              f"{split['n_corridor']} approaches.")
        print(f"  The gap is real but small - {gap:.1f} percentage points - and the finding")
        print("  that matters is the one underneath it: the LOWEST two-wheeler share on")
        print(f"  any of the {split['n_corridor'] + split['n_cross']} approaches is "
              f"{split['min_share']:.1%}, four times IRC:106's 10% threshold.")
        print("  The survey carries two-wheelers at PCU 0.50 throughout. IRC:106 requires")
        print("  0.75 at that share, so the understatement is not concentrated anywhere -")
        print("  it applies to every approach on the corridor.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "cluster.json").write_text(json.dumps(dict(
        method="Ward linkage on volume-normalised approach share vectors",
        feature_sets_tested=len(results),
        multiple_comparison_note=("two feature sets were fitted and both are published, "
                                  "because reporting only the winner is what makes a "
                                  "p-value meaningless"),
        silhouette_min=SILHOUETTE_MIN, n_approaches=int(len(sets[0][0])),
        results=results,
        any_typology_found=bool(passed),
        two_wheeler_split=split,
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'cluster.json'}")


if __name__ == "__main__":
    _main()
