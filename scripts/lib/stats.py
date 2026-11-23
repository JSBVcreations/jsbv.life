"""Shared statistics for the builders: the Python twin of assets/stats.js.

Same names and rules as the JS module, and scripts/tests/test_stats.py checks both give the same numbers:
- A day with no data (None) is missing, never zero. Rates divide by days WITH data.
- A week counts with 5 of its 7 days, a month with 20 days (MIN_WEEK, MIN_MONTH).
- Clock times average on the circle.
Standard library only.
"""
import math
import random

MIN_WEEK, MIN_MONTH = 5, 20


def _ok(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def clean(xs):
    return [x for x in xs if _ok(x)]


def mean(xs):
    v = clean(xs)
    return sum(v) / len(v) if v else None


def sd(xs):
    v = clean(xs)
    if len(v) < 2:
        return None
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def quantile(xs, q):
    """Linear interpolation between order statistics (type 7, as R and NumPy default)."""
    v = sorted(clean(xs))
    if not v:
        return None
    h = (len(v) - 1) * q
    lo, hi = math.floor(h), math.ceil(h)
    return v[lo] + (h - lo) * (v[hi] - v[lo])


def median(xs):
    return quantile(xs, 0.5)


def rate(xs, min_days=1):
    v = clean(xs)
    return sum(v) / len(v) if len(v) >= min_days else None


def rolling(xs, days, centred=False, min_days=None, stat='mean'):
    if min_days is None:
        min_days = days // 2 + 1
    back = (days - 1) // 2 if centred else days - 1
    fwd = days - 1 - back if centred else 0
    f = median if stat == 'median' else mean
    out = []
    for i in range(len(xs)):
        w = xs[max(0, i - back):min(len(xs), i + fwd + 1)]
        out.append(f(w) if len(clean(w)) >= min_days else None)
    return out


def deviation(xs, days=28, min_days=14):
    out = [None] * len(xs)
    for i, x in enumerate(xs):
        if not _ok(x):
            continue
        w = xs[max(0, i - days):i]
        if len(clean(w)) < min_days:
            continue
        out[i] = x - median(w)
    return out


def percentile(x, pool):
    """Share of pool below x, ties counted as half (mid-rank), 0-100."""
    v = clean(pool)
    if not v or not _ok(x):
        return None
    below = sum(1 for y in v if y < x)
    tie = sum(1 for y in v if y == x)
    return 100 * (below + 0.5 * tie) / len(v)


def _ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        e = i
        while e + 1 < len(o) and v[o[e + 1]] == v[o[i]]:
            e += 1
        for t in range(i, e + 1):
            r[o[t]] = (i + e) / 2 + 1
        i = e + 1
    return r


def _pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None


def lag1(xs):
    a, b = [], []
    for i in range(1, len(xs)):
        if _ok(xs[i]) and _ok(xs[i - 1]):
            a.append(xs[i - 1])
            b.append(xs[i])
    r = _pearson(a, b) if len(a) > 3 else None
    return r or 0


def norm_cdf(z):
    t = 1 / (1 + 0.3275911 * abs(z) / math.sqrt(2))
    y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * math.exp(-(z * z) / 2)
    return (1 + y) / 2 if z >= 0 else (1 - y) / 2


def corr(x, y, method='spearman', min_n=20):
    """Correlation with a 95% interval and two-sided p allowing for autocorrelation (effective n)."""
    px, py = [], []
    for a, b in zip(x, y):
        if _ok(a) and _ok(b):
            px.append(a)
            py.append(b)
    n = len(px)
    if n < min_n:
        return None
    r = _pearson(_ranks(px), _ranks(py)) if method == 'spearman' else _pearson(px, py)
    if r is None:
        return None
    k = max(-0.95, min(0.95, lag1(x) * lag1(y)))
    n_eff = max(4, min(n, n * (1 - k) / (1 + k)))
    z = math.atanh(max(-0.999999, min(0.999999, r)))
    se = 1 / math.sqrt(n_eff - 3)
    p = 2 * (1 - norm_cdf(abs(z) / se))
    return {'r': r, 'n': n, 'nEff': n_eff, 'lo': math.tanh(z - 1.96 * se), 'hi': math.tanh(z + 1.96 * se), 'p': p}


def bh(ps):
    """Benjamini-Hochberg q-values (None stays None)."""
    idx = sorted([(p, i) for i, p in enumerate(ps) if _ok(p)])
    m = len(idx)
    q = [None] * len(ps)
    run = 1.0
    for k in range(m - 1, -1, -1):
        run = min(run, idx[k][0] * m / (k + 1))
        q[idx[k][1]] = run
    return q


def clock_mean(hours):
    v = clean(hours)
    if not v:
        return None
    s = sum(math.sin((h % 24) / 24 * 2 * math.pi) for h in v) / len(v)
    c = sum(math.cos((h % 24) / 24 * 2 * math.pi) for h in v) / len(v)
    R = math.hypot(s, c)
    hour = math.atan2(s, c) / (2 * math.pi) * 24
    if hour < 0:
        hour += 24
    sd_min = math.sqrt(-2 * math.log(min(1, R))) / (2 * math.pi) * 24 * 60 if R > 0 else None
    return {'hour': hour, 'sdMin': sd_min}


def bootstrap_mean_range(xs, lo=0.1, hi=0.9, iters=2000, seed=7):
    """Range of the mean of xs under resampling days with replacement: (lo, hi) quantiles."""
    v = clean(xs)
    if len(v) < 2:
        return None
    rnd = random.Random(seed)
    means = [sum(rnd.choice(v) for _ in v) / len(v) for _ in range(iters)]
    return quantile(means, lo), quantile(means, hi)


def shifts(xs, min_seg=8, max_shifts=6):
    """Level shifts by binary segmentation on the mean with a BIC-style penalty (same as stats.js)."""
    idx = [i for i, x in enumerate(xs) if _ok(x)]
    v = [xs[i] for i in idx]
    n = len(v)
    if n < 2 * min_seg:
        return []
    s1, s2 = [0.0], [0.0]
    for x in v:
        s1.append(s1[-1] + x)
        s2.append(s2[-1] + x * x)

    def sse(a, b):
        k = b - a
        m = (s1[b] - s1[a]) / k
        return s2[b] - s2[a] - k * m * m

    pen = 3 * math.log(n) * max(sse(0, n) / n, 1e-9)
    cuts = []

    def split(a, b):
        if len(cuts) >= max_shifts or b - a < 2 * min_seg:
            return
        best, gain = None, 0
        for c in range(a + min_seg, b - min_seg + 1):
            g = sse(a, b) - sse(a, c) - sse(c, b)
            if g > gain:
                gain, best = g, c
        if best is None or gain < pen:
            return
        cuts.append(best)
        split(a, best)
        split(best, b)

    split(0, n)
    cuts.sort()
    bounds = [0] + cuts + [n]
    return [{'at': idx[c], 'before': (s1[c] - s1[bounds[k]]) / (c - bounds[k]),
             'after': (s1[bounds[k + 2]] - s1[c]) / (bounds[k + 2] - c)} for k, c in enumerate(cuts)]
