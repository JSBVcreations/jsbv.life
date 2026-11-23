#!/usr/bin/env python3
"""assets/stats.js and scripts/lib/stats.py must give the same numbers on the same inputs.

    python3 scripts/tests/test_stats.py        (needs node on the PATH)
"""
import json, math, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from lib import stats as S  # noqa: E402

# a fixed, awkward test series: gaps, ties, a level shift, autocorrelation
X = [None if i % 11 == 3 else round(50 + 10 * math.sin(i / 5) + (12 if i > 60 else 0) + (i % 7) * 0.5, 2) for i in range(120)]
Y = [None if i % 13 == 5 else round(30 + 6 * math.sin(i / 5 + 0.4) + (i % 4), 2) for i in range(120)]
H = [23.5, 0.5, 23.75, 1.25, 22.9, 24.6, 0.1]

py = {
    'mean': S.mean(X), 'sd': S.sd(X), 'q25': S.quantile(X, 0.25), 'median': S.median(X), 'rate': S.rate(X[:7], 5),
    'roll7': S.rolling(X, 7), 'roll7c': S.rolling(X, 7, centred=True, min_days=4), 'dev': S.deviation(X, 28, 14),
    'pct': S.percentile(55, X), 'lag1': S.lag1(X), 'corr': S.corr(X, Y), 'corrp': S.corr(X, Y, method='pearson'),
    'bh': S.bh([0.01, 0.04, None, 0.03, 0.2, 0.001]), 'clock': S.clock_mean(H), 'shifts': S.shifts(X),
}
js = subprocess.run(['node', '--input-type=module', '-e', f"""
import * as S from '{ROOT}/assets/stats.js';
const X = {json.dumps(X)}, Y = {json.dumps(Y)}, H = {json.dumps(H)};
console.log(JSON.stringify({{
  mean: S.mean(X), sd: S.sd(X), q25: S.quantile(X, 0.25), median: S.median(X), rate: S.rate(X.slice(0, 7), 5),
  roll7: S.rolling(X, 7), roll7c: S.rolling(X, 7, {{ centred: true, minDays: 4 }}), dev: S.deviation(X, 28, 14),
  pct: S.percentile(55, X), lag1: S.lag1(X), corr: S.corr(X, Y), corrp: S.corr(X, Y, {{ method: 'pearson' }}),
  bh: S.bh([0.01, 0.04, null, 0.03, 0.2, 0.001]), clock: S.clockMean(H), shifts: S.shifts(X),
}}));
"""], capture_output=True, text=True, check=True)
js = json.loads(js.stdout)
js['clock'] = {'hour': js['clock']['hour'], 'sdMin': js['clock']['sdMin']}


def same(a, b, path):
    if isinstance(a, dict):
        assert set(a) == set(b), (path, set(a) ^ set(b))
        for k in a:
            same(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list):
        assert len(a) == len(b), (path, len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            same(x, y, f'{path}[{i}]')
    elif a is None or b is None:
        assert a is None and b is None, (path, a, b)
    else:
        assert abs(a - b) <= 1e-6 * max(1, abs(a)), (path, a, b)


bad = 0
for k in py:
    try:
        same(py[k], js[k], k)
        print(f'ok   {k}')
    except AssertionError as e:
        bad += 1
        print(f'FAIL {k}: {e}')
# a few known answers
assert S.clock_mean([23.5, 0.5])['hour'] in (0.0, 24.0) or abs(S.clock_mean([23.5, 0.5])['hour'] % 24) < 1e-9
assert S.percentile(2, [1, 2, 3]) == 50
assert S.bh([0.01, 0.02])[0] == 0.02
print('all match' if not bad else f'{bad} differ')
sys.exit(1 if bad else 0)
