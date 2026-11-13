"""Offline frame-time analysis; no hooks, capture providers or game handles."""
import csv
import math
import statistics
import hashlib
from pathlib import Path

def analyze(values):
    frames = [float(v) for v in values]
    if len(frames) < 1000 or any(not math.isfinite(v) or v <= 0 for v in frames):
        raise ValueError('Supply at least 1000 finite positive frame times in milliseconds.')
    descending = sorted(frames, reverse=True)
    def low(fraction):
        return 1000 / statistics.mean(descending[:max(1, math.ceil(len(frames) * fraction))])
    return dict(frames=len(frames), duration_s=sum(frames)/1000,
                average_fps=1000/statistics.mean(frames), low_1=low(.01), low_01=low(.001),
                p99_ms=sorted(frames)[math.ceil(.99 * len(frames))-1],
                mean_ms=statistics.mean(frames), stdev_ms=statistics.stdev(frames),
                histogram=[sum(lo <= v < hi for v in frames) for lo, hi in
                           [(0,4),(4,8),(8,12),(12,16.67),(16.67,25),(25,50),(50,float('inf'))]])

def load_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        candidates = ['frametime_ms', 'MsBetweenPresents', 'FrameTime']
        field = next((c for c in candidates if c in (reader.fieldnames or [])), None)
        if not field:
            raise ValueError('CSV needs frametime_ms, MsBetweenPresents or FrameTime (milliseconds). Export one game/process/run only.')
        rows = list(reader)
        for key in ('ProcessID', 'Application', 'SwapChainAddress'):
            if len({row.get(key) for row in rows if row.get(key)}) > 1:
                raise ValueError(f'Multiple {key} values: filter to one stream before importing.')
        result=analyze([row[field] for row in rows])
        result['source_sha256']=hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return result

def compare(before, after):
    if len(before) < 3 or len(after) < 3:
        return 'At least three matched runs per condition required to estimate run-to-run variation.'
    b = [x['average_fps'] for x in before]
    a = [x['average_fps'] for x in after]
    change = statistics.mean(a) - statistics.mean(b)
    # Conservative descriptive heuristic, explicitly not a significance test.
    spread = 2 * max(statistics.stdev(a), statistics.stdev(b))
    return (f'Mean FPS change {change:+.2f} ({100*change/statistics.mean(b):+.2f}%). '
            f'Twice maximum within-condition SD: {spread:.2f} FPS. '
            + ('Change exceeds this descriptive variation band. ' if abs(change) > spread else 'Change is within this descriptive variation band. ')
            + 'Not a statistical significance or causality claim; match scenes, temperatures and capture settings.')


def advanced_compare(before, after, iterations=2000):
    """Resample independent RUNS, not autocorrelated individual frames."""
    import random
    if len(before)<3 or len(after)<3: raise ValueError('At least three independent matched runs per condition required')
    contexts={r.get('context','').strip() for r in before+after}
    if len(contexts)!=1 or not next(iter(contexts)):
        raise ValueError('Set the same nonempty experiment context for every run; do not mix scenes, hardware or graphics configurations.')
    if not 100<=iterations<=10000: raise ValueError('Bootstrap iterations out of bounds')
    rng=random.Random(1731)
    metrics={}
    for key in ('average_fps','low_1','low_01','p99_ms'):
        b=[float(r[key]) for r in before]; a=[float(r[key]) for r in after]
        if any(not math.isfinite(x) or x<=0 for x in b+a): raise ValueError('Invalid run metric')
        delta=statistics.mean(a)-statistics.mean(b)
        distribution=sorted(statistics.mean(rng.choices(a,k=len(a)))-statistics.mean(rng.choices(b,k=len(b))) for _ in range(iterations))
        low=distribution[int(.025*iterations)]; high=distribution[min(iterations-1,int(.975*iterations))]
        metrics[key]={'before_mean':statistics.mean(b),'after_mean':statistics.mean(a),
                      'delta':delta,'percent':100*delta/statistics.mean(b),'bootstrap_95_percentile_interval':[low,high],
                      'direction':'lower is better' if key=='p99_ms' else 'higher is better',
                      'interval_excludes_zero':low>0 or high<0,
                      'before_sd':statistics.stdev(b),'after_sd':statistics.stdev(a)}
    durations=[r['duration_s'] for r in before+after]
    warnings=[]
    if max(durations)>1.2*min(durations): warnings.append('Run durations differ by >20%; compare the same route and duration.')
    if min(durations)<60: warnings.append('At least one capture is <60 seconds; tail metrics are especially unstable.')
    return {'context':next(iter(contexts)),'runs_before':len(before),'runs_after':len(after),'metrics':metrics,
            'warnings':warnings,'method':'Deterministic independent run-level percentile bootstrap (2000 by default). Exploratory intervals with small sample sizes; not proof of causality or anti-cheat/input-latency testing.'}
